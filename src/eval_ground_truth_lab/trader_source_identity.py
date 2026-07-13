from __future__ import annotations

import base64
import hashlib
import json
import re
from collections.abc import Mapping
from dataclasses import asdict, dataclass
from pathlib import PurePosixPath
from typing import Any

from eval_ground_truth_lab.execution_binding import EXECUTION_BINDING_SHA256

LOADED_EXECUTION_BINDING_SHA256 = EXECUTION_BINDING_SHA256

TRADER_SOURCE_IDENTITY_PROOF_SCHEMA_VERSION = "eval-lab-trader-source-git-proof-v1"

_DIGEST_PATTERN = re.compile(r"[0-9a-f]{64}\Z")
_GIT_OBJECT_PATTERN = re.compile(r"[0-9a-f]{40}\Z")


class TraderSourceIdentityProofError(ValueError):
    """Raised when the packaged Trader Git-object proof is invalid."""


@dataclass(frozen=True)
class VerifiedTraderSourceIdentity:
    source_bundle_sha256: str
    source_git_blob_sha1: str
    source_git_commit: str
    source_git_tree: str
    source_path: str
    proof_sha256: str

    def to_mapping(self) -> dict[str, str]:
        return asdict(self)


def verify_trader_source_identity_proof(
    *,
    proof_bytes: bytes,
    evidence_bytes: bytes,
) -> VerifiedTraderSourceIdentity:
    """Verify an offline commit-to-blob Git object chain for packaged evidence."""

    proof = _parse_json_object(proof_bytes)
    _require_exact_fields(
        proof,
        {
            "blob_oid",
            "commit",
            "schema_version",
            "source_bundle_sha256",
            "source_path",
            "trees",
        },
        "source identity proof",
    )
    if proof.get("schema_version") != TRADER_SOURCE_IDENTITY_PROOF_SCHEMA_VERSION:
        raise TraderSourceIdentityProofError("Unsupported Trader source identity proof schema")

    source_bundle_sha256 = _required_digest(
        proof.get("source_bundle_sha256"), "source_bundle_sha256"
    )
    source_path = _safe_source_path(proof.get("source_path"))
    blob_oid = _required_git_oid(proof.get("blob_oid"), "blob_oid")
    if _git_object_oid("blob", evidence_bytes) != blob_oid:
        raise TraderSourceIdentityProofError(
            "Packaged Trader evidence does not match the proof's terminal blob"
        )

    commit = _mapping(proof.get("commit"), "commit")
    _require_exact_fields(commit, {"content_base64", "oid"}, "commit")
    commit_oid = _required_git_oid(commit.get("oid"), "commit.oid")
    commit_content = _canonical_base64_bytes(commit.get("content_base64"), "commit.content_base64")
    if _git_object_oid("commit", commit_content) != commit_oid:
        raise TraderSourceIdentityProofError("Trader proof commit object hash is invalid")
    root_tree_oid = _commit_tree_oid(commit_content)

    raw_trees = proof.get("trees")
    if not isinstance(raw_trees, list) or not raw_trees:
        raise TraderSourceIdentityProofError("trees must be a non-empty list")
    trees: dict[str, bytes] = {}
    for index, raw_tree in enumerate(raw_trees):
        tree = _mapping(raw_tree, f"trees[{index}]")
        _require_exact_fields(tree, {"content_base64", "oid"}, f"trees[{index}]")
        tree_oid = _required_git_oid(tree.get("oid"), f"trees[{index}].oid")
        if tree_oid in trees:
            raise TraderSourceIdentityProofError("Trader proof contains a duplicate tree object")
        tree_content = _canonical_base64_bytes(
            tree.get("content_base64"), f"trees[{index}].content_base64"
        )
        if _git_object_oid("tree", tree_content) != tree_oid:
            raise TraderSourceIdentityProofError("Trader proof tree object hash is invalid")
        trees[tree_oid] = tree_content

    current_tree_oid = root_tree_oid
    visited_tree_oids: set[str] = set()
    path_parts = PurePosixPath(source_path).parts
    for index, part in enumerate(path_parts):
        tree_content = trees.get(current_tree_oid)
        if tree_content is None:
            raise TraderSourceIdentityProofError("Trader proof omits a path tree object")
        visited_tree_oids.add(current_tree_oid)
        entries = _parse_tree(tree_content)
        entry = entries.get(part.encode())
        if entry is None:
            raise TraderSourceIdentityProofError("Trader proof source path is absent from its tree")
        mode, entry_oid = entry
        if index < len(path_parts) - 1:
            if mode != b"40000":
                raise TraderSourceIdentityProofError(
                    "Trader proof source path traverses a non-tree object"
                )
            current_tree_oid = entry_oid
        else:
            if mode != b"100644" or entry_oid != blob_oid:
                raise TraderSourceIdentityProofError(
                    "Trader proof source path does not terminate at the evidence blob"
                )

    if visited_tree_oids != set(trees):
        raise TraderSourceIdentityProofError("Trader proof contains unreferenced tree objects")

    return VerifiedTraderSourceIdentity(
        source_bundle_sha256=source_bundle_sha256,
        source_git_blob_sha1=blob_oid,
        source_git_commit=commit_oid,
        source_git_tree=root_tree_oid,
        source_path=source_path,
        proof_sha256=hashlib.sha256(proof_bytes).hexdigest(),
    )


def _parse_json_object(payload: bytes) -> Mapping[str, Any]:
    def reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise TraderSourceIdentityProofError(
                    f"Duplicate key in Trader source identity proof: {key!r}"
                )
            result[key] = value
        return result

    try:
        value = json.loads(payload, object_pairs_hook=reject_duplicate_keys)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise TraderSourceIdentityProofError(
            "Trader source identity proof is not valid JSON"
        ) from exc
    return _mapping(value, "source identity proof")


def _commit_tree_oid(content: bytes) -> str:
    header, separator, _ = content.partition(b"\n\n")
    if not separator:
        raise TraderSourceIdentityProofError("Trader proof commit object has no message boundary")
    tree_headers = [line[5:] for line in header.splitlines() if line.startswith(b"tree ")]
    if len(tree_headers) != 1:
        raise TraderSourceIdentityProofError("Trader proof commit must bind exactly one root tree")
    try:
        value = tree_headers[0].decode("ascii")
    except UnicodeDecodeError as exc:
        raise TraderSourceIdentityProofError("Trader proof commit tree oid is not ASCII") from exc
    return _required_git_oid(value, "commit.tree")


def _parse_tree(content: bytes) -> dict[bytes, tuple[bytes, str]]:
    entries: dict[bytes, tuple[bytes, str]] = {}
    offset = 0
    while offset < len(content):
        space = content.find(b" ", offset)
        nul = content.find(b"\0", space + 1)
        if space <= offset or nul <= space + 1 or nul + 21 > len(content):
            raise TraderSourceIdentityProofError("Trader proof contains a malformed tree object")
        mode = content[offset:space]
        name = content[space + 1 : nul]
        if b"/" in name or name in {b".", b".."} or name in entries:
            raise TraderSourceIdentityProofError("Trader proof contains an unsafe tree entry")
        entries[name] = (mode, content[nul + 1 : nul + 21].hex())
        offset = nul + 21
    return entries


def _canonical_base64_bytes(value: Any, field: str) -> bytes:
    if not isinstance(value, str) or not value:
        raise TraderSourceIdentityProofError(f"{field} must be a non-empty base64 string")
    try:
        decoded = base64.b64decode(value, validate=True)
    except (ValueError, base64.binascii.Error) as exc:
        raise TraderSourceIdentityProofError(f"{field} is not valid base64") from exc
    if base64.b64encode(decoded).decode("ascii") != value:
        raise TraderSourceIdentityProofError(f"{field} is not canonical base64")
    return decoded


def _git_object_oid(kind: str, content: bytes) -> str:
    header = f"{kind} {len(content)}\0".encode()
    return hashlib.sha1(header + content, usedforsecurity=False).hexdigest()


def _safe_source_path(value: Any) -> str:
    if not isinstance(value, str) or not value:
        raise TraderSourceIdentityProofError("source_path must be a non-empty string")
    path = PurePosixPath(value)
    if (
        path.is_absolute()
        or value != path.as_posix()
        or any(part in {"", ".", ".."} for part in path.parts)
    ):
        raise TraderSourceIdentityProofError("source_path must be a normalized relative path")
    return value


def _required_git_oid(value: Any, field: str) -> str:
    if not isinstance(value, str) or not _GIT_OBJECT_PATTERN.fullmatch(value):
        raise TraderSourceIdentityProofError(f"{field} must be a lowercase Git SHA-1")
    return value


def _required_digest(value: Any, field: str) -> str:
    if not isinstance(value, str) or not _DIGEST_PATTERN.fullmatch(value):
        raise TraderSourceIdentityProofError(f"{field} must be a lowercase SHA-256")
    return value


def _mapping(value: Any, field: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise TraderSourceIdentityProofError(f"{field} must be an object")
    return value


def _require_exact_fields(value: Mapping[str, Any], expected: set[str], field: str) -> None:
    if set(value) != expected:
        raise TraderSourceIdentityProofError(f"{field} fields do not match the proof schema")
