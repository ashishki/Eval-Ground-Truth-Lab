from __future__ import annotations

import json

import pytest

from eval_ground_truth_lab.datasets import DatasetValidationError, load_dataset


def test_valid_jsonl_dataset_metadata(tmp_path) -> None:
    dataset_path = tmp_path / "support_tickets.jsonl"
    dataset_path.write_text(
        "\n".join(
            [
                json.dumps(
                    {
                        "id": "case-001",
                        "input": {"ticket": "Cannot reset password"},
                        "expected": {"category": "account_access"},
                    }
                ),
                json.dumps(
                    {
                        "id": "case-002",
                        "input": {"ticket": "Refund request"},
                        "expected": {"category": "billing"},
                    }
                ),
            ]
        ),
        encoding="utf-8",
    )

    dataset = load_dataset(dataset_path)

    assert dataset.metadata.dataset_id == "support_tickets"
    assert dataset.metadata.schema_version == "1.0"
    assert dataset.metadata.case_count == 2
    assert len(dataset.metadata.dataset_hash) == 64
    assert dataset.metadata.source_path == dataset_path


def test_valid_yaml_dataset_metadata(tmp_path) -> None:
    dataset_path = tmp_path / "support_tickets.yaml"
    dataset_path.write_text(
        """
dataset_id: support-ticket-evals
schema_version: "1.1"
cases:
  - id: case-001
    input:
      ticket: Cannot reset password
    expected:
      category: account_access
""".strip(),
        encoding="utf-8",
    )

    dataset = load_dataset(dataset_path)

    assert dataset.metadata.dataset_id == "support-ticket-evals"
    assert dataset.metadata.schema_version == "1.1"
    assert dataset.metadata.case_count == 1
    assert dataset.cases[0].id == "case-001"


def test_missing_required_field_names_case_and_field(tmp_path) -> None:
    dataset_path = tmp_path / "missing_expected.jsonl"
    dataset_path.write_text(
        json.dumps({"id": "case-003", "input": {"ticket": "Need escalation"}}),
        encoding="utf-8",
    )

    with pytest.raises(DatasetValidationError) as exc_info:
        load_dataset(dataset_path)

    assert exc_info.value.case_id == "case-003"
    assert exc_info.value.field == "expected"
    assert "case-003" in str(exc_info.value)
    assert "expected" in str(exc_info.value)


def test_case_content_changes_dataset_hash(tmp_path) -> None:
    first_path = tmp_path / "first.jsonl"
    second_path = tmp_path / "second.jsonl"
    first_path.write_text(
        json.dumps(
            {
                "id": "case-004",
                "input": {"ticket": "Approve wire transfer?"},
                "expected": {"action": "deny"},
            }
        ),
        encoding="utf-8",
    )
    second_path.write_text(
        json.dumps(
            {
                "id": "case-004",
                "input": {"ticket": "Approve wire transfer?"},
                "expected": {"action": "approve"},
            }
        ),
        encoding="utf-8",
    )

    first = load_dataset(first_path)
    second = load_dataset(second_path)

    assert first.metadata.dataset_hash != second.metadata.dataset_hash


def test_metadata_key_order_does_not_change_dataset_hash(tmp_path) -> None:
    first_path = tmp_path / "first.jsonl"
    second_path = tmp_path / "second.jsonl"
    first_path.write_text(
        json.dumps(
            {
                "id": "case-005",
                "input": {"ticket": "Cancel subscription"},
                "expected": {"category": "billing"},
                "metadata": {"risk": "low", "source": "synthetic"},
            }
        ),
        encoding="utf-8",
    )
    second_path.write_text(
        json.dumps(
            {
                "metadata": {"source": "synthetic", "risk": "low"},
                "expected": {"category": "billing"},
                "input": {"ticket": "Cancel subscription"},
                "id": "case-005",
            }
        ),
        encoding="utf-8",
    )

    first = load_dataset(first_path)
    second = load_dataset(second_path)

    assert first.metadata.dataset_hash == second.metadata.dataset_hash
