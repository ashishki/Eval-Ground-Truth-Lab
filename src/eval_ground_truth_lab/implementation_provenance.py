from __future__ import annotations

import hashlib
import json
import os
import re
import stat
import subprocess
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from eval_ground_truth_lab.execution_binding import EXECUTION_BINDING_SHA256

IMPLEMENTATION_PROVENANCE_SCHEMA_VERSION = "eval-lab-implementation-provenance-v2"
EXECUTION_BINDING_SCHEMA_VERSION = "eval-lab-loaded-execution-binding-v1"
EXECUTION_BINDING_RELATIVE_PATH = "execution_binding.py"
LOADED_EXECUTION_BINDING_SHA256 = EXECUTION_BINDING_SHA256

_EXECUTION_BINDING_PATTERN = re.compile(rb'(?m)^EXECUTION_BINDING_SHA256 = "([0-9a-f]{64})"$')
_EXECUTION_BINDING_PLACEHOLDER = b"0" * 64


class ImplementationProvenanceError(RuntimeError):
    """Raised when local implementation identity cannot be measured safely."""


@dataclass(frozen=True)
class _PackageFileSnapshot:
    path: str
    payload: bytes
    git_mode: str

    @property
    def sha256(self) -> str:
        return hashlib.sha256(self.payload).hexdigest()

    @property
    def size_bytes(self) -> int:
        return len(self.payload)

    @property
    def git_blob_sha1(self) -> str:
        return _git_blob_sha1(self.payload)


@dataclass(frozen=True)
class _PackageSnapshot:
    files: tuple[_PackageFileSnapshot, ...]


def build_implementation_provenance(
    *,
    component_paths: Mapping[str, str | Path],
    package_root: str | Path,
    require_execution_binding: bool = False,
) -> dict[str, Any]:
    """Bind named decision components and the complete installed package payload."""

    unresolved_root = Path(package_root)
    if unresolved_root.is_symlink():
        raise ImplementationProvenanceError(f"Package root is not a directory: {unresolved_root}")
    root = unresolved_root.resolve()
    component_relative_paths = _component_relative_paths(
        component_paths=component_paths,
        package_root=root,
    )
    snapshot = _capture_package_snapshot(root)
    components = _component_hashes(
        component_relative_paths=component_relative_paths,
        snapshot=snapshot,
    )
    package_payload = _package_payload_identity(snapshot)
    result = {
        "components_sha256": components,
        "package_payload": package_payload,
        "schema_version": IMPLEMENTATION_PROVENANCE_SCHEMA_VERSION,
        "source": _source_identity(
            root,
            package_files=snapshot.files,
            package_payload_sha256=package_payload["sha256"],
        ),
    }
    if require_execution_binding:
        result["execution_binding"] = _execution_binding_identity(snapshot)
    return result


def derive_execution_binding_sha256(*, package_root: str | Path) -> str:
    """Derive the generated execution binding from one immutable package snapshot."""

    unresolved_root = Path(package_root)
    if unresolved_root.is_symlink():
        raise ImplementationProvenanceError(f"Package root is not a directory: {unresolved_root}")
    root = unresolved_root.resolve()
    return _derive_execution_binding_sha256(_capture_package_snapshot(root))


def _component_relative_paths(
    *,
    component_paths: Mapping[str, str | Path],
    package_root: Path,
) -> dict[str, str]:
    relative_paths: dict[str, str] = {}
    for name, path in sorted(component_paths.items()):
        resolved = Path(path).resolve()
        try:
            relative = resolved.relative_to(package_root)
        except ValueError as exc:
            raise ImplementationProvenanceError(
                f"Implementation component {name!r} is outside the package root"
            ) from exc
        relative_paths[name] = relative.as_posix()
    return relative_paths


def _capture_package_snapshot(root: Path) -> _PackageSnapshot:
    """Read one recursive package state into immutable path/mode/byte records."""

    if root.is_symlink() or not root.is_dir():
        raise ImplementationProvenanceError(f"Package root is not a directory: {root}")
    files: list[_PackageFileSnapshot] = []
    captured_stats: dict[str, os.stat_result] = {}
    for path, relative, path_stat in _package_regular_files(root):
        flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
        try:
            descriptor = os.open(path, flags)
        except OSError as exc:
            raise ImplementationProvenanceError(
                f"Package payload entry could not be opened safely: {relative}"
            ) from exc
        with os.fdopen(descriptor, "rb") as source:
            measured_stat = os.fstat(source.fileno())
            if not stat.S_ISREG(measured_stat.st_mode) or not _same_file(path_stat, measured_stat):
                raise ImplementationProvenanceError(
                    f"Package payload entry changed during capture: {relative}"
                )
            measured_bytes = source.read()
            final_stat = os.fstat(source.fileno())
        if not _stable_stat(measured_stat, final_stat):
            raise ImplementationProvenanceError(
                f"Package payload entry changed during capture: {relative}"
            )
        executable_bits = stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH
        files.append(
            _PackageFileSnapshot(
                path=relative,
                payload=measured_bytes,
                git_mode=("100755" if measured_stat.st_mode & executable_bits else "100644"),
            )
        )
        captured_stats[relative] = final_stat
    if not files:
        raise ImplementationProvenanceError("Package payload contains no regular files")
    final_files = _package_regular_files(root)
    final_stats = {relative: path_stat for _, relative, path_stat in final_files}
    if set(final_stats) != set(captured_stats) or any(
        not _stable_stat(captured_stats[path], final_stats[path]) for path in captured_stats
    ):
        raise ImplementationProvenanceError("Package payload changed during recursive capture")
    return _PackageSnapshot(files=tuple(files))


def _package_regular_files(root: Path) -> list[tuple[Path, str, os.stat_result]]:
    files: list[tuple[Path, str, os.stat_result]] = []
    for path in sorted(root.rglob("*"), key=lambda item: item.relative_to(root).as_posix()):
        relative_path = path.relative_to(root)
        if "__pycache__" in relative_path.parts or path.suffix in {".pyc", ".pyo"}:
            continue
        relative = relative_path.as_posix()
        try:
            path_stat = path.lstat()
        except OSError as exc:
            raise ImplementationProvenanceError(
                f"Package payload entry changed during capture: {relative}"
            ) from exc
        if stat.S_ISLNK(path_stat.st_mode):
            raise ImplementationProvenanceError(
                f"Package payload cannot contain symlinks: {relative}"
            )
        if stat.S_ISDIR(path_stat.st_mode):
            continue
        if not stat.S_ISREG(path_stat.st_mode):
            raise ImplementationProvenanceError(
                f"Package payload entry is not a regular file: {relative}"
            )
        files.append((path, relative, path_stat))
    return files


def _same_file(first: os.stat_result, second: os.stat_result) -> bool:
    return (first.st_dev, first.st_ino) == (second.st_dev, second.st_ino)


def _stable_stat(first: os.stat_result, second: os.stat_result) -> bool:
    return (
        first.st_dev,
        first.st_ino,
        first.st_mode,
        first.st_size,
        first.st_mtime_ns,
        first.st_ctime_ns,
    ) == (
        second.st_dev,
        second.st_ino,
        second.st_mode,
        second.st_size,
        second.st_mtime_ns,
        second.st_ctime_ns,
    )


def _component_hashes(
    *,
    component_relative_paths: Mapping[str, str],
    snapshot: _PackageSnapshot,
) -> dict[str, str]:
    snapshot_by_path = {file.path: file for file in snapshot.files}
    components: dict[str, str] = {}
    for name, relative in component_relative_paths.items():
        component = snapshot_by_path.get(relative)
        if component is None:
            raise ImplementationProvenanceError(
                f"Implementation component {name!r} is not a regular file in the package snapshot"
            )
        components[name] = component.sha256
    return components


def _package_payload_identity(snapshot: _PackageSnapshot) -> dict[str, Any]:
    entries = [
        {
            "mode": file.git_mode,
            "path": file.path,
            "sha256": file.sha256,
            "size_bytes": file.size_bytes,
        }
        for file in snapshot.files
    ]
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


def _execution_binding_identity(snapshot: _PackageSnapshot) -> dict[str, str]:
    snapshot_by_path = {file.path: file for file in snapshot.files}
    binding_file = snapshot_by_path.get(EXECUTION_BINDING_RELATIVE_PATH)
    if binding_file is None:
        raise ImplementationProvenanceError(
            f"Package execution binding is missing: {EXECUTION_BINDING_RELATIVE_PATH}"
        )
    matches = list(_EXECUTION_BINDING_PATTERN.finditer(binding_file.payload))
    if len(matches) != 1:
        raise ImplementationProvenanceError(
            "Package execution binding must contain exactly one canonical SHA-256 marker"
        )
    embedded = matches[0].group(1).decode("ascii")
    derived = _derive_execution_binding_sha256(snapshot)
    if embedded != derived:
        raise ImplementationProvenanceError(
            "Package execution binding does not match the immutable package snapshot"
        )
    return {
        "schema_version": EXECUTION_BINDING_SCHEMA_VERSION,
        "sha256": derived,
    }


def _derive_execution_binding_sha256(snapshot: _PackageSnapshot) -> str:
    entries: list[dict[str, Any]] = []
    binding_seen = False
    for file in snapshot.files:
        payload = file.payload
        if file.path == EXECUTION_BINDING_RELATIVE_PATH:
            matches = list(_EXECUTION_BINDING_PATTERN.finditer(payload))
            if len(matches) != 1:
                raise ImplementationProvenanceError(
                    "Package execution binding must contain exactly one canonical SHA-256 marker"
                )
            payload = (
                payload[: matches[0].start(1)]
                + _EXECUTION_BINDING_PLACEHOLDER
                + payload[matches[0].end(1) :]
            )
            binding_seen = True
        entries.append(
            {
                "mode": file.git_mode,
                "path": file.path,
                "sha256": hashlib.sha256(payload).hexdigest(),
                "size_bytes": len(payload),
            }
        )
    if not binding_seen:
        raise ImplementationProvenanceError(
            f"Package execution binding is missing: {EXECUTION_BINDING_RELATIVE_PATH}"
        )
    payload = json.dumps(
        {
            "files": entries,
            "schema_version": EXECUTION_BINDING_SCHEMA_VERSION,
        },
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode()
    return hashlib.sha256(payload).hexdigest()


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
