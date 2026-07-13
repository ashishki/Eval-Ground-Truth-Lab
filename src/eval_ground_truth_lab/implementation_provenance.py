from __future__ import annotations

import hashlib
import json
import os
import stat
import subprocess
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

IMPLEMENTATION_PROVENANCE_SCHEMA_VERSION = "eval-lab-implementation-provenance-v1"


class ImplementationProvenanceError(RuntimeError):
    """Raised when local implementation identity cannot be measured safely."""


@dataclass(frozen=True)
class _PackageFileSnapshot:
    path: str
    sha256: str
    size_bytes: int
    git_blob_sha1: str
    git_mode: str


def build_implementation_provenance(
    *,
    component_paths: Mapping[str, str | Path],
    package_root: str | Path,
) -> dict[str, Any]:
    """Bind named decision components and the complete installed package payload."""

    root = Path(package_root).resolve()
    components = {
        name: _sha256_file(_require_regular_file(Path(path), label=name))
        for name, path in sorted(component_paths.items())
    }
    package_payload, package_files = _package_payload_identity(root)
    return {
        "components_sha256": components,
        "package_payload": package_payload,
        "schema_version": IMPLEMENTATION_PROVENANCE_SCHEMA_VERSION,
        "source": _source_identity(
            root,
            package_files=package_files,
            package_payload_sha256=package_payload["sha256"],
        ),
    }


def _package_payload_identity(
    root: Path,
) -> tuple[dict[str, Any], tuple[_PackageFileSnapshot, ...]]:
    if root.is_symlink() or not root.is_dir():
        raise ImplementationProvenanceError(f"Package root is not a directory: {root}")
    files: list[_PackageFileSnapshot] = []
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root)
        if "__pycache__" in relative.parts or path.suffix in {".pyc", ".pyo"}:
            continue
        if path.is_symlink():
            raise ImplementationProvenanceError(
                f"Package payload cannot contain symlinks: {relative.as_posix()}"
            )
        if path.is_file():
            with path.open("rb") as source:
                measured_bytes = source.read()
                measured_stat = os.fstat(source.fileno())
            if not stat.S_ISREG(measured_stat.st_mode):
                raise ImplementationProvenanceError(
                    f"Package payload entry is not a regular file: {relative.as_posix()}"
                )
            executable_bits = stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH
            files.append(
                _PackageFileSnapshot(
                    path=relative.as_posix(),
                    sha256=hashlib.sha256(measured_bytes).hexdigest(),
                    size_bytes=len(measured_bytes),
                    git_blob_sha1=_git_blob_sha1(measured_bytes),
                    git_mode=("100755" if measured_stat.st_mode & executable_bits else "100644"),
                )
            )
    if not files:
        raise ImplementationProvenanceError("Package payload contains no regular files")
    entries = [
        {
            "mode": file.git_mode,
            "path": file.path,
            "sha256": file.sha256,
            "size_bytes": file.size_bytes,
        }
        for file in files
    ]
    payload = json.dumps(
        entries,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode()
    return (
        {
            "file_count": len(entries),
            "sha256": hashlib.sha256(payload).hexdigest(),
        },
        tuple(files),
    )


def _source_identity(
    package_root: Path,
    *,
    package_files: tuple[_PackageFileSnapshot, ...],
    package_payload_sha256: str,
) -> dict[str, Any]:
    repository_root = _try_git(package_root, "rev-parse", "--show-toplevel")
    if repository_root is None:
        return _installed_package_identity(package_payload_sha256)
    root = Path(repository_root)
    try:
        package_root.relative_to(root)
    except ValueError as exc:
        raise ImplementationProvenanceError(
            "Git repository root does not contain the measured package"
        ) from exc
    commit = _try_git(root, "rev-parse", "--verify", "HEAD^{commit}")
    if commit is None:
        return _installed_package_identity(package_payload_sha256)
    tree = _try_git(root, "rev-parse", "--verify", f"{commit}^{{tree}}")
    if tree is None:
        return _installed_package_identity(package_payload_sha256)
    if not _package_payload_is_tracked_at_head(
        repository_root=root,
        package_root=package_root,
        package_files=package_files,
        commit=commit,
    ):
        return _installed_package_identity(package_payload_sha256)
    return {
        "commit": commit,
        "kind": "git_worktree",
        "measured_package_matches_head": True,
        "tree": tree,
    }


def _package_payload_is_tracked_at_head(
    *,
    repository_root: Path,
    package_root: Path,
    package_files: tuple[_PackageFileSnapshot, ...],
    commit: str,
) -> bool:
    package_prefix = package_root.relative_to(repository_root)
    repository_paths = {
        (
            package_file.path
            if package_prefix == Path(".")
            else (package_prefix / package_file.path).as_posix()
        ): package_file
        for package_file in package_files
    }
    head_entries = _git_tree_entries_under_path(
        repository_root,
        commit=commit,
        repository_path=package_prefix.as_posix(),
    )
    if head_entries is None or set(head_entries) != set(repository_paths):
        return False
    for repository_path, package_file in repository_paths.items():
        entry = head_entries[repository_path]
        git_mode, object_type, object_id = entry
        if object_type != "blob":
            return False
        if object_id != package_file.git_blob_sha1:
            return False
        if git_mode != package_file.git_mode:
            return False
    return True


def _git_tree_entries_under_path(
    repository_root: Path,
    *,
    commit: str,
    repository_path: str,
) -> dict[str, tuple[str, str, str]] | None:
    try:
        completed = subprocess.run(
            (
                "git",
                "-C",
                str(repository_root),
                "ls-tree",
                "-r",
                "-z",
                "--full-tree",
                commit,
                "--",
                repository_path,
            ),
            check=False,
            capture_output=True,
            env={**os.environ, "GIT_LITERAL_PATHSPECS": "1"},
            timeout=10,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if completed.returncode != 0 or (completed.stdout and not completed.stdout.endswith(b"\0")):
        return None
    records = completed.stdout[:-1].split(b"\0") if completed.stdout else []
    entries: dict[str, tuple[str, str, str]] = {}
    for record in records:
        if b"\t" not in record:
            return None
        header, encoded_path = record.split(b"\t", 1)
        fields = header.split(b" ")
        path = os.fsdecode(encoded_path)
        if len(fields) != 3 or path in entries:
            return None
        try:
            entries[path] = (
                fields[0].decode("ascii"),
                fields[1].decode("ascii"),
                fields[2].decode("ascii"),
            )
        except UnicodeDecodeError:
            return None
    return entries


def _git_blob_sha1(payload: bytes) -> str:
    header = f"blob {len(payload)}\0".encode()
    return hashlib.sha1(header + payload, usedforsecurity=False).hexdigest()


def _installed_package_identity(package_payload_sha256: str) -> dict[str, str]:
    return {
        "installed_artifact_sha256": package_payload_sha256,
        "kind": "installed_package",
    }


def _try_git(cwd: Path, *args: str) -> str | None:
    try:
        completed = subprocess.run(
            ("git", "-C", str(cwd), *args),
            check=False,
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if completed.returncode != 0:
        return None
    return completed.stdout.strip()


def _require_regular_file(path: Path, *, label: str) -> Path:
    if path.is_symlink():
        raise ImplementationProvenanceError(
            f"Implementation component {label!r} is not a regular file"
        )
    resolved = path.resolve()
    if not resolved.is_file():
        raise ImplementationProvenanceError(
            f"Implementation component {label!r} is not a regular file"
        )
    return resolved


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
