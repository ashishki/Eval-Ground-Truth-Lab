# META_ANALYSIS - Cycle 19

Date: 2026-06-12
Type: targeted

## Project State

Phase 6 is in progress. T22 Optional Real Judge Provider is implemented
locally. Next: T23 - File-Backed Human Review Queue.

Baseline: 84 pass, 0 skip.

## Open Findings

| ID | Sev | Description | Files | Status |
|----|-----|-------------|-------|--------|
| none | n/a | No open findings in `docs/CODEX_PROMPT.md`; Cycle 18 review had no P0/P1/P2 findings. | n/a | n/a |

## PROMPT_1 Scope (architecture)

- Provider boundary: new `OpenAIJudgeProvider` uses injectable transport and is
  exported from `eval_ground_truth_lab.judging.providers`.
- Disabled default: provider config returns `None` without `OPENAI_API_KEY` or
  `LLM_JUDGE_API_KEY`; `JudgeRunner` still requires provider key and positive
  budget before any call.
- Structured output: provider requests strict JSON schema output with `score`,
  `explanation`, and `quality_outcome`; tests validate payload and response
  shape.
- Budget and telemetry: existing `JudgeRunner` budget precheck runs before
  provider call; telemetry records tokens, estimated cost, latency, retry count,
  model, and quality outcome.
- Human review and authority: ambiguous judge output can create a
  `HumanReviewQueue` item, and deterministic failures remain blocking through
  `final_case_decision`.
- Calibration artifacts: `docs/JUDGE_CALIBRATION.md`,
  `datasets/judge_calibration/ambiguous_cases.jsonl`, and
  `reports/judge_calibration/report.md` document synthetic, no-live-call
  evidence.
- Acceptance tests: `tests/judging/test_provider_contract.py` covers T22.
- Audit continuity: Cycle 18 review artifacts archived under
  `docs/audit/archive/`.

## PROMPT_2 Scope (code/docs priority order)

1. `src/eval_ground_truth_lab/judging/providers/openai_provider.py` (new)
2. `src/eval_ground_truth_lab/judging/providers/__init__.py` (new)
3. `src/eval_ground_truth_lab/judging/__init__.py` (changed)
4. `tests/judging/test_provider_contract.py` (new)
5. `docs/JUDGE_CALIBRATION.md` (new)
6. `datasets/judge_calibration/ambiguous_cases.jsonl` (new)
7. `reports/judge_calibration/report.md` (new)
8. `.gitignore` (changed)
9. `README.md` (changed)
10. `docs/README.md` (changed)
11. `docs/CODEX_PROMPT.md` (changed)
12. `docs/EVIDENCE_INDEX.md` (changed)
13. `docs/IMPLEMENTATION_JOURNAL.md` (changed)
14. `docs/audit/` review artifacts (changed/new)

## Cycle Type

Targeted - Phase 6 task review for T22 optional real judge provider.

## Notes for PROMPT_3

Focus on provider disabled-by-default behavior, no live calls in tests, budget
precheck before provider transport, structured output validation, telemetry
fields, human review routing, and deterministic-failure authority.
