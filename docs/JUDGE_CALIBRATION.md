# Judge Calibration

The optional OpenAI judge provider is disabled by default. It can only run when
an operator supplies a provider API key and a positive per-run judge budget.

The provider uses structured JSON output with this non-authoritative shape:

```json
{
  "score": 0.55,
  "explanation": "Ambiguous enough for human review.",
  "quality_outcome": "ambiguous"
}
```

Deterministic validators remain authoritative. Judge output can create human
review items for ambiguous cases, but it cannot override deterministic blocking
failures such as unsafe auto-approval or invalid structured output.

## Local Contract

- Provider config reads `OPENAI_API_KEY` or `LLM_JUDGE_API_KEY`; absence disables
  the provider.
- `JudgeRunner` checks budget before calling the provider.
- Telemetry records tokens, estimated cost, latency, retry count, model, and
  quality outcome.
- Tests use fake transport only and make no live provider calls.

## Calibration Fixtures

- Dataset: `datasets/judge_calibration/ambiguous_cases.jsonl`
- Report: `reports/judge_calibration/report.md`
- Contract tests: `tests/judging/test_provider_contract.py`
