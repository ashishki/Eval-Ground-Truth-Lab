from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class FailureTaxonomyEntry:
    label: str
    description: str


FAILURE_TAXONOMY: tuple[FailureTaxonomyEntry, ...] = (
    FailureTaxonomyEntry(
        label="unsafe_auto_approval",
        description="Candidate approved a high-risk item without required evidence.",
    ),
    FailureTaxonomyEntry(
        label="invalid_structured_output",
        description="Candidate output violated the required structured schema.",
    ),
    FailureTaxonomyEntry(
        label="missing_evidence",
        description="Candidate answer omitted required citations or supporting evidence.",
    ),
    FailureTaxonomyEntry(
        label="low_confidence",
        description="Candidate confidence fell below the configured acceptance threshold.",
    ),
    FailureTaxonomyEntry(
        label="accuracy_regression",
        description="Candidate accuracy regressed beyond the configured threshold.",
    ),
    FailureTaxonomyEntry(
        label="cost_regression",
        description="Candidate cost per case regressed beyond the configured threshold.",
    ),
    FailureTaxonomyEntry(
        label="latency_regression",
        description="Candidate latency regressed beyond the configured threshold.",
    ),
)

REQUIRED_FAILURE_LABELS: frozenset[str] = frozenset(entry.label for entry in FAILURE_TAXONOMY)
