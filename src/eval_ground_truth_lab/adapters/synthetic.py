from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
from typing import Any

from eval_ground_truth_lab.adapters.base import AdapterResult


class SyntheticDemoAdapter:
    def __init__(self, fixtures: Mapping[str, Any]) -> None:
        self._fixtures = dict(fixtures)

    def invoke(self, case: Mapping[str, Any]) -> AdapterResult:
        case_id = str(case["id"])
        if case_id not in self._fixtures:
            raise KeyError(f"No synthetic fixture configured for case {case_id}")
        return AdapterResult(output=deepcopy(self._fixtures[case_id]))
