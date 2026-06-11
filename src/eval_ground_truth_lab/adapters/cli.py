from __future__ import annotations

import json
import subprocess
from collections.abc import Callable, Mapping, Sequence
from time import perf_counter
from typing import Any

from eval_ground_truth_lab.adapters.base import AdapterResult, UnsafeAdapterInputError
from eval_ground_truth_lab.tracing import start_trace

FORBIDDEN_CLI_FIELDS = frozenset({"command", "cmd", "shell", "args", "argv", "executable"})


class CliCandidateAdapter:
    def __init__(
        self,
        command_template: Sequence[str],
        *,
        timeout_seconds: float = 30.0,
        runner: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
    ) -> None:
        if not command_template:
            raise ValueError("command_template must contain at least one argument")
        self.command_template = tuple(command_template)
        self.timeout_seconds = timeout_seconds
        self._runner = runner

    def invoke(self, case: Mapping[str, Any]) -> AdapterResult:
        _reject_forbidden_fields(case, FORBIDDEN_CLI_FIELDS)
        trace = start_trace("candidate.cli")
        started = perf_counter()
        completed = self._runner(
            list(self.command_template),
            input=json.dumps({"case": dict(case)}, sort_keys=True),
            text=True,
            capture_output=True,
            timeout=self.timeout_seconds,
            check=False,
        )
        latency_ms = (perf_counter() - started) * 1000
        return AdapterResult(
            output=_parse_stdout(completed.stdout),
            stdout=completed.stdout,
            stderr=completed.stderr,
            exit_code=completed.returncode,
            latency_ms=latency_ms,
            trace_id=trace.trace_id,
            operation_name=trace.operation_name,
        )


def _reject_forbidden_fields(case: Mapping[str, Any], forbidden_fields: frozenset[str]) -> None:
    present = sorted(field for field in forbidden_fields if field in case)
    if present:
        raise UnsafeAdapterInputError(
            f"Eval case cannot define adapter execution fields: {', '.join(present)}"
        )


def _parse_stdout(stdout: str) -> Any:
    stripped = stdout.strip()
    if not stripped:
        return None
    try:
        return json.loads(stripped)
    except json.JSONDecodeError:
        return stripped
