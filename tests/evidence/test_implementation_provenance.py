from __future__ import annotations

import os
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
