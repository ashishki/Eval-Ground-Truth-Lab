from __future__ import annotations

import json
import subprocess

from eval_ground_truth_lab.adapters import CliCandidateAdapter


def test_cli_adapter_records_process_result() -> None:
    calls = []

    def fake_runner(command, **kwargs):
        calls.append((command, kwargs))
        return subprocess.CompletedProcess(
            args=command,
            returncode=2,
            stdout=json.dumps({"category": "billing"}),
            stderr="candidate warning",
        )

    adapter = CliCandidateAdapter(("python", "-m", "candidate"), runner=fake_runner)
    result = adapter.invoke({"id": "case-001", "input": {"ticket": "Refund"}})

    assert calls[0][0] == ["python", "-m", "candidate"]
    assert json.loads(calls[0][1]["input"]) == {
        "case": {"id": "case-001", "input": {"ticket": "Refund"}}
    }
    assert "shell" not in calls[0][1]
    assert result.output == {"category": "billing"}
    assert result.stdout == json.dumps({"category": "billing"})
    assert result.stderr == "candidate warning"
    assert result.exit_code == 2
    assert result.latency_ms >= 0.0
    assert result.trace_id
    assert result.operation_name == "candidate.cli"
