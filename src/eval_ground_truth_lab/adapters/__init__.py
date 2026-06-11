from eval_ground_truth_lab.adapters.base import AdapterResult, UnsafeAdapterInputError
from eval_ground_truth_lab.adapters.cli import CliCandidateAdapter
from eval_ground_truth_lab.adapters.http import HttpCandidateAdapter, HttpResponse
from eval_ground_truth_lab.adapters.synthetic import SyntheticDemoAdapter

__all__ = [
    "AdapterResult",
    "CliCandidateAdapter",
    "HttpCandidateAdapter",
    "HttpResponse",
    "SyntheticDemoAdapter",
    "UnsafeAdapterInputError",
]
