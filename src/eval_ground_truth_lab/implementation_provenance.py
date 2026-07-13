from __future__ import annotations

import hashlib
import json
import subprocess
from collections.abc import Mapping
from pathlib import Path
from typing import Any

IMPLEMENTATION_PROVENANCE_SCHEMA_VERSION = "eval-lab-implementation-provenance-v1"


class ImplementationProvenanceError(RuntimeError):
    """Raised when local implementation identity cannot be measured safely."""


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
    package_payload = _package_payload_identity(root)
    return {
        "components_sha256": components,
        "package_payload": package_payload,
        "schema_version": IMPLEMENTATION_PROVENANCE_SCHEMA_VERSION,
        "source": _source_identity(root, package_payload_sha256=package_payload["sha256"]),
    }


def _package_payload_identity(root: Path) -> dict[str, Any]:
    if root.is_symlink() or not root.is_dir():
        raise ImplementationProvenanceError(f"Package root is not a directory: {root}")
    entries: list[dict[str, Any]] = []
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root)
        if "__pycache__" in relative.parts or path.suffix in {".pyc", ".pyo"}:
            continue
        if path.is_symlink():
            raise ImplementationProvenanceError(
                f"Package payload cannot contain symlinks: {relative.as_posix()}"
            )
        if path.is_file():
            entries.append(
                {
                    "path": relative.as_posix(),
                    "sha256": _sha256_file(path),
                    "size_bytes": path.stat().st_size,
                }
            )
    if not entries:
        raise ImplementationProvenanceError("Package payload contains no regular files")
    payload = json.dumps(
        entries,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode()
    return {
        "file_count": len(entries),
        "sha256": hashlib.sha256(payload).hexdigest(),
    }


def _source_identity(package_root: Path, *, package_payload_sha256: str) -> dict[str, Any]:
    repository_root = _try_git(package_root, "rev-parse", "--show-toplevel")
    if repository_root is None:
        return {
            "installed_artifact_sha256": package_payload_sha256,
            "kind": "installed_package",
        }
    root = Path(repository_root)
    try:
        package_root.relative_to(root)
    except ValueError as exc:
        raise ImplementationProvenanceError(
            "Git repository root does not contain the measured package"
        ) from exc
    commit = _required_git(root, "rev-parse", "--verify", "HEAD^{commit}")
    tree = _required_git(root, "rev-parse", "--verify", "HEAD^{tree}")
    status = _required_git(root, "status", "--porcelain=v1", "--untracked-files=all")
    return {
        "commit": commit,
        "kind": "git_worktree",
        "tree": tree,
        "worktree_clean": status == "",
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


def _required_git(cwd: Path, *args: str) -> str:
    value = _try_git(cwd, *args)
    if value is None:
        raise ImplementationProvenanceError(
            "Cannot measure required Git implementation provenance: " + " ".join(args)
        )
    return value


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
