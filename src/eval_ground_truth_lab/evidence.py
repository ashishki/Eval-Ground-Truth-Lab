from __future__ import annotations

import hashlib
import json
import os
import tempfile
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any

from eval_ground_truth_lab.execution_binding import EXECUTION_BINDING_SHA256

LOADED_EXECUTION_BINDING_SHA256 = EXECUTION_BINDING_SHA256

EVIDENCE_SCHEMA_VERSION = "eval-lab-evidence-v1"


class EvidenceError(RuntimeError):
    """Base error for evidence pack operations."""


class EvidenceVerificationError(EvidenceError):
    """Raised when an evidence pack is incomplete or has changed."""


@dataclass(frozen=True)
class EvidenceVerificationResult:
    manifest_path: Path
    content_address: str
    artifact_count: int

    def to_mapping(self) -> dict[str, Any]:
        return {
            "artifact_count": self.artifact_count,
            "content_address": self.content_address,
            "manifest_path": str(self.manifest_path),
            "verified": True,
        }


def write_evidence_manifest(
    root: str | Path,
    artifact_paths: Sequence[str | Path],
    *,
    metadata: Mapping[str, Any],
) -> Path:
    """Write a content-addressed manifest after every artifact is final."""

    pack_root = Path(root)
    pack_root.mkdir(parents=True, exist_ok=True)
    artifacts: list[dict[str, Any]] = []
    seen: set[str] = set()
    for candidate in artifact_paths:
        relative = _safe_relative_path(candidate)
        relative_text = relative.as_posix()
        if relative_text in seen:
            raise EvidenceError(f"Artifact is declared more than once: {relative_text}")
        seen.add(relative_text)
        artifact = pack_root / relative
        if artifact.is_symlink() or not artifact.is_file():
            raise EvidenceError(f"Declared artifact is not a regular file: {relative_text}")
        artifacts.append(
            {
                "path": relative_text,
                "sha256": _sha256_file(artifact),
                "size_bytes": artifact.stat().st_size,
            }
        )

    payload = {
        "artifacts": sorted(artifacts, key=lambda item: item["path"]),
        "metadata": dict(metadata),
        "schema_version": EVIDENCE_SCHEMA_VERSION,
    }
    digest = hashlib.sha256(_canonical_json_bytes(payload)).hexdigest()
    manifest = {
        **payload,
        "content_address": f"sha256:{digest}",
    }
    manifest_path = pack_root / f"sha256-{digest}.manifest.json"
    if manifest_path.exists():
        raise EvidenceError(f"Evidence manifest already exists: {manifest_path}")
    atomic_write_json(manifest_path, manifest)
    return manifest_path


def verify_evidence_manifest(manifest_path: str | Path) -> EvidenceVerificationResult:
    path = Path(manifest_path)
    if path.is_symlink() or not path.is_file():
        raise EvidenceVerificationError(f"Manifest is not a regular file: {path}")
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        raise EvidenceVerificationError(f"Cannot read evidence manifest: {path}") from exc
    if not isinstance(raw, dict):
        raise EvidenceVerificationError("Evidence manifest must be a JSON object")
    required = {"artifacts", "content_address", "metadata", "schema_version"}
    if set(raw) != required or raw.get("schema_version") != EVIDENCE_SCHEMA_VERSION:
        raise EvidenceVerificationError("Evidence manifest schema is invalid")

    payload = {key: raw[key] for key in ("artifacts", "metadata", "schema_version")}
    digest = hashlib.sha256(_canonical_json_bytes(payload)).hexdigest()
    content_address = f"sha256:{digest}"
    if raw.get("content_address") != content_address:
        raise EvidenceVerificationError("Manifest content address does not match its payload")
    if path.name != f"sha256-{digest}.manifest.json":
        raise EvidenceVerificationError("Manifest filename does not match its content address")

    artifacts = raw.get("artifacts")
    if not isinstance(artifacts, list) or not artifacts:
        raise EvidenceVerificationError("Evidence manifest must declare at least one artifact")

    root = path.parent
    declared: set[str] = set()
    for item in artifacts:
        if not isinstance(item, dict) or set(item) != {"path", "sha256", "size_bytes"}:
            raise EvidenceVerificationError("Evidence artifact entry is invalid")
        relative = _safe_relative_path_for_verification(item.get("path"))
        relative_text = relative.as_posix()
        if relative_text in declared:
            raise EvidenceVerificationError(f"Duplicate artifact declaration: {relative_text}")
        declared.add(relative_text)
        artifact = root / relative
        if artifact.is_symlink() or not artifact.is_file():
            raise EvidenceVerificationError(f"Declared artifact is missing: {relative_text}")
        if artifact.stat().st_size != item.get("size_bytes"):
            raise EvidenceVerificationError(f"Artifact size changed: {relative_text}")
        if _sha256_file(artifact) != item.get("sha256"):
            raise EvidenceVerificationError(f"Artifact digest changed: {relative_text}")

    actual_files: set[str] = set()
    for candidate in root.rglob("*"):
        if candidate.is_symlink():
            raise EvidenceVerificationError(
                f"Evidence packs cannot contain symlinks: {candidate.relative_to(root)}"
            )
        if candidate.is_file():
            actual_files.add(candidate.relative_to(root).as_posix())
    allowed = declared | {path.relative_to(root).as_posix()}
    additions = sorted(actual_files - allowed)
    if additions:
        raise EvidenceVerificationError(
            "Evidence pack contains undeclared files: " + ", ".join(additions)
        )
    missing = sorted(allowed - actual_files)
    if missing:
        raise EvidenceVerificationError(
            "Evidence pack is missing declared files: " + ", ".join(missing)
        )

    return EvidenceVerificationResult(
        manifest_path=path,
        content_address=content_address,
        artifact_count=len(artifacts),
    )


def atomic_write_json(path: str | Path, value: Mapping[str, Any]) -> None:
    atomic_write_bytes(
        path,
        (json.dumps(value, indent=2, sort_keys=True) + "\n").encode("utf-8"),
    )


def atomic_write_text(path: str | Path, value: str) -> None:
    atomic_write_bytes(path, value.encode("utf-8"))


def atomic_write_bytes(path: str | Path, value: bytes) -> None:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        dir=destination.parent,
        prefix=f".{destination.name}.",
        suffix=".tmp",
    )
    temporary_path = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as output:
            output.write(value)
            output.flush()
            os.fsync(output.fileno())
        os.replace(temporary_path, destination)
        _fsync_directory(destination.parent)
    finally:
        temporary_path.unlink(missing_ok=True)


def sha256_file(path: str | Path) -> str:
    return _sha256_file(Path(path))


def _safe_relative_path(value: str | Path) -> PurePosixPath:
    return _validate_relative_text(Path(value).as_posix())


def _safe_relative_path_for_verification(value: Any) -> PurePosixPath:
    if not isinstance(value, str):
        raise EvidenceVerificationError("Artifact path must be a string")
    try:
        return _validate_relative_text(value)
    except EvidenceError as exc:
        raise EvidenceVerificationError(str(exc)) from exc


def _validate_relative_text(value: str) -> PurePosixPath:
    relative = PurePosixPath(value)
    if not value or relative.is_absolute() or ".." in relative.parts or "." in relative.parts:
        raise EvidenceError(f"Artifact path must be a safe relative path: {value!r}")
    if "\\" in value:
        raise EvidenceError(f"Artifact path must use POSIX separators: {value!r}")
    return relative


def _canonical_json_bytes(value: Mapping[str, Any]) -> bytes:
    try:
        return json.dumps(
            value,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise EvidenceError("Evidence metadata must be canonical JSON data") from exc


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _fsync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
