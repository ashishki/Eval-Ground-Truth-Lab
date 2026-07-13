# Archived gdev-content deterministic cases

## Status

This is a provenance-preserving archive of the six corrected deterministic-stub
cases that could be replayed from the superseded `gdev-content` repository. It
is not a flagship benchmark, a gdev-agent adapter dataset, a blind holdout, or
evidence about live model quality.

## Provenance

| Field | Value |
|---|---|
| Source repository | `https://github.com/ashishki/gdev-content` |
| Repository head reviewed | `628da247148b31f7885f3e859d96e939a2ef6454` |
| Last source commit changing the cases | `44dd93760de2cccf0667f393d7c231bdfbbcabc0` |
| Source path | `eval/cases.jsonl` |
| Source Git blob | `e8fda6e2e9134bc66c7fc0dfc30d0bd44f5a84c4` |
| Source raw SHA-256 | `b7f6e682af5157034da13682c11cd88fa82b4a3a9c34b593a6bba69dd664a34f` |
| Source authoring basis | Synthetic cases authored in the repository owned by the same publisher; migrated here under Apache-2.0 |
| Real-user or production data | None claimed or observed |

Each case preserves the source input, mode, language selector, source ID, and
expected pipeline boolean. IDs were prefixed with `legacy-gdev-content-`, and
the source fields were normalized into Eval Lab's `input` / `expected` /
`metadata` schema. No source label was strengthened.

## Replay performed before migration

The source harness was executed at repository head `628da247...` with
`PYTHONDONTWRITEBYTECODE=1` and results written outside the repository:

```bash
python eval/run_eval.py \
  --provider stub \
  --cases eval/cases.jsonl \
  --out-dir /tmp/gdev-content-audit-results
```

The isolated dependency set was `pydantic==2.13.4`,
`pydantic-core==2.46.4`, `Jinja2==3.1.6`, and `MarkupSafe==3.0.3`. All six
expected pipeline booleans matched. Five positive fixtures completed and the
declared invalid-JSON fixture failed after two generator attempts, yielding
`expectation_match_rate=1.0` and `success_rate=0.8333`. The latter is descriptive
of five expected successes out of six, not a quality target. Local latency
values were deliberately not migrated as performance evidence.

## Exclusions and limitations

- The source's 20 `TC-*.json` LLM cases were not migrated. The source review
  documented that they had previously been disconnected from the harness, and
  no credential-free replay can establish their semantic labels. Copying them
  would risk importing contradictory expectations into the flagship benchmark.
- The deterministic stub emits fixed outputs and does not demonstrate prompt,
  provider, model, language, safety, tone, cost, or production behavior.
- `C-004` expects the pipeline to complete, not that every possible generated
  answer is safe. Its text is retained only as a structural fixture.
- The source repository did not have a reproducible dependency lock or CI gate.
  Exact replay dependencies are therefore recorded above.
- These cases are archive material and are not part of the canonical v0.2.0
  gdev challenge or its threshold decision.

The current manifest and tests verify case count, IDs, provenance fields, raw
content hash, source checksum metadata, and the one declared negative result.
