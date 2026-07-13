from __future__ import annotations

import os
import subprocess
from pathlib import Path

from eval_ground_truth_lab.implementation_provenance import build_implementation_provenance


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


def _git(repository: Path, *args: str) -> None:
    subprocess.run(
        ("git", "-C", str(repository), *args),
        check=True,
        capture_output=True,
        text=True,
    )
