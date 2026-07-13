from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

from eval_ground_truth_lab import implementation_provenance as provenance_module
from eval_ground_truth_lab.implementation_provenance import (
    ImplementationProvenanceError,
    build_implementation_provenance,
)


def test_installed_payload_digest_is_stable_across_mtime_changes(tmp_path: Path) -> None:
    package = tmp_path / "installed-package"
    package.mkdir()
    component = package / "runner.py"
    component.write_text("VALUE = 1\n", encoding="utf-8")
    resource = package / "fixture.json"
    resource.write_text('{"synthetic":true}\n', encoding="utf-8")

    first = build_implementation_provenance(
        component_paths={"runner": component},
        package_root=package,
    )
    os.utime(component, (1_000_000_000, 1_000_000_000))
    os.utime(resource, (1_100_000_000, 1_100_000_000))
    second = build_implementation_provenance(
        component_paths={"runner": component},
        package_root=package,
    )

    assert first == second
    assert first["source"] == {
        "installed_artifact_sha256": first["package_payload"]["sha256"],
        "kind": "installed_package",
    }
    assert first["package_payload"]["file_count"] == 2


def test_payload_digest_changes_when_an_unlisted_package_module_changes(tmp_path: Path) -> None:
    package = tmp_path / "installed-package"
    package.mkdir()
    component = package / "runner.py"
    component.write_text("VALUE = 1\n", encoding="utf-8")
    unlisted = package / "manifest_writer.py"
    unlisted.write_text("VALUE = 1\n", encoding="utf-8")
    before = build_implementation_provenance(
        component_paths={"runner": component},
        package_root=package,
    )

    unlisted.write_text("VALUE = 2\n", encoding="utf-8")
    after = build_implementation_provenance(
        component_paths={"runner": component},
        package_root=package,
    )

    assert before["components_sha256"] == after["components_sha256"]
    assert before["package_payload"]["sha256"] != after["package_payload"]["sha256"]


def test_named_component_must_be_inside_package_root(tmp_path: Path) -> None:
    package = tmp_path / "installed-package"
    package.mkdir()
    (package / "runner.py").write_text("VALUE = 1\n", encoding="utf-8")
    outside = tmp_path / "outside.py"
    outside.write_text("VALUE = 2\n", encoding="utf-8")

    with pytest.raises(ImplementationProvenanceError, match="outside the package root"):
        build_implementation_provenance(
            component_paths={"runner": outside},
            package_root=package,
        )


def test_component_package_and_head_identity_share_one_immutable_snapshot(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _, package, component = _tracked_package_repository(tmp_path)
    baseline = build_implementation_provenance(
        component_paths={"runner": component},
        package_root=package,
    )
    original_capture = provenance_module._capture_package_snapshot
    capture_calls = 0

    def capture_then_mutate(root: Path):  # noqa: ANN202
        nonlocal capture_calls
        capture_calls += 1
        snapshot = original_capture(root)
        component.write_text("VALUE = 2\n", encoding="utf-8")
        component.chmod(component.stat().st_mode | 0o111)
        (package / "late.py").write_text("LATE = True\n", encoding="utf-8")
        return snapshot

    monkeypatch.setattr(provenance_module, "_capture_package_snapshot", capture_then_mutate)
    raced = build_implementation_provenance(
        component_paths={"runner": component},
        package_root=package,
    )

    assert capture_calls == 1
    assert raced == baseline
    assert raced["source"]["kind"] == "git_worktree"


def test_ignored_installed_package_inside_unrelated_repo_is_not_a_git_worktree(
    tmp_path: Path,
) -> None:
    repository = tmp_path / "unrelated-repository"
    repository.mkdir()
    _git(repository, "init", "--initial-branch=main")
    _git(repository, "config", "user.name", "Eval Lab Test")
    _git(repository, "config", "user.email", "eval-lab-test@example.invalid")
    (repository / ".gitignore").write_text("installed/\n", encoding="utf-8")
    (repository / "README.md").write_text("# unrelated repository\n", encoding="utf-8")
    _git(repository, "add", ".gitignore", "README.md")
    _git(repository, "commit", "-m", "test: create unrelated repository")

    package = repository / "installed/eval_ground_truth_lab"
    package.mkdir(parents=True)
    component = package / "runner.py"
    component.write_text("VALUE = 1\n", encoding="utf-8")
    (package / "fixture.json").write_text('{"synthetic":true}\n', encoding="utf-8")

    provenance = build_implementation_provenance(
        component_paths={"runner": component},
        package_root=package,
    )

    assert provenance["source"] == {
        "installed_artifact_sha256": provenance["package_payload"]["sha256"],
        "kind": "installed_package",
    }


def test_git_identity_claim_is_limited_to_measured_package_bytes_and_modes(
    tmp_path: Path,
) -> None:
    repository, package, component = _tracked_package_repository(tmp_path)
    commit = _git(repository, "rev-parse", "HEAD")
    tree = _git(repository, "rev-parse", "HEAD^{tree}")
    (repository / "README.md").write_text("dirty unrelated file\n", encoding="utf-8")

    provenance = build_implementation_provenance(
        component_paths={"runner": component},
        package_root=package,
    )

    assert provenance["source"] == {
        "commit": commit,
        "kind": "git_worktree",
        "measured_package_matches_head": True,
        "tree": tree,
    }
    assert "worktree_clean" not in provenance["source"]


@pytest.mark.parametrize("index_flag", ["--assume-unchanged", "--skip-worktree"])
@pytest.mark.parametrize("mutation", ["bytes", "executable_mode"])
def test_hidden_measured_package_mutation_cannot_claim_git_head_identity(
    tmp_path: Path,
    index_flag: str,
    mutation: str,
) -> None:
    repository, package, component = _tracked_package_repository(tmp_path)
    before = build_implementation_provenance(
        component_paths={"runner": component},
        package_root=package,
    )
    _git(repository, "update-index", index_flag, "package/runner.py")
    if mutation == "bytes":
        component.write_text("VALUE = 2\n", encoding="utf-8")
    else:
        component.chmod(component.stat().st_mode | 0o111)

    assert _git(repository, "status", "--porcelain=v1", "--untracked-files=all") == ""
    provenance = build_implementation_provenance(
        component_paths={"runner": component},
        package_root=package,
    )

    assert provenance["source"] == {
        "installed_artifact_sha256": provenance["package_payload"]["sha256"],
        "kind": "installed_package",
    }
    assert provenance["package_payload"]["sha256"] != before["package_payload"]["sha256"]


def test_skip_worktree_cannot_hide_deleted_tracked_package_file(tmp_path: Path) -> None:
    repository, package, component = _tracked_package_repository(tmp_path)
    remaining = package / "fixture.json"
    _git(repository, "update-index", "--skip-worktree", "package/runner.py")
    component.unlink()

    assert _git(repository, "status", "--porcelain=v1", "--untracked-files=all") == ""
    provenance = build_implementation_provenance(
        component_paths={"fixture": remaining},
        package_root=package,
    )

    assert provenance["source"] == {
        "installed_artifact_sha256": provenance["package_payload"]["sha256"],
        "kind": "installed_package",
    }


def _tracked_package_repository(tmp_path: Path) -> tuple[Path, Path, Path]:
    repository = tmp_path / "repository"
    repository.mkdir()
    _git(repository, "init", "--initial-branch=main")
    _git(repository, "config", "user.name", "Eval Lab Test")
    _git(repository, "config", "user.email", "eval-lab-test@example.invalid")
    package = repository / "package"
    package.mkdir()
    component = package / "runner.py"
    component.write_text("VALUE = 1\n", encoding="utf-8")
    (package / "fixture.json").write_text('{"synthetic":true}\n', encoding="utf-8")
    (repository / "README.md").write_text("# repository\n", encoding="utf-8")
    _git(repository, "add", "README.md", "package")
    _git(repository, "commit", "-m", "test: create tracked package")
    return repository, package, component


def _git(repository: Path, *args: str) -> str:
    completed = subprocess.run(
        ("git", "-C", str(repository), *args),
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout.strip()
