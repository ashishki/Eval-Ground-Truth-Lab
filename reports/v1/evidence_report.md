# V1 Evidence Report

## Dataset Evidence

- V1 manifest: `datasets/v1/manifest.json`
- V1 cases: `datasets/v1/cases.jsonl`
- Case count: `100`
- Dataset hash: `bfffb49cdc8fb2420ff9a499d795d84eadfc1e526a08bbe0a10a154acc2a54f7`

## Seeded Regression Evidence

- Seeded regression manifest: `datasets/v1/seeded_regressions.json`
- Smoke dataset: `datasets/smoke/seeded_regressions.jsonl`
- Smoke threshold config: `datasets/smoke/thresholds.json`
- CI workflow evidence: `.github/workflows/ci.yml`
- Smoke gate test: `tests/eval/test_seeded_smoke_gate.py::test_seeded_unsafe_regression_fails_ci_gate`
- Smoke report test: `tests/eval/test_seeded_smoke_report.py::test_seeded_report_links_required_evidence`

| Required CI failure | Evidence link | Expected gate |
|---------------------|---------------|---------------|
| unsafe regression / unsafe auto-approval | `tests/eval/test_seeded_smoke_gate.py::test_seeded_unsafe_regression_fails_ci_gate` | `unsafe_auto_approval_rate` |
| invalid structured output | `tests/eval/test_seeded_smoke_report.py::test_seeded_report_links_required_evidence` | `invalid_output_rate` |
| excessive cost increase | `tests/eval/test_seeded_smoke_report.py::test_seeded_report_links_required_evidence` | `cost_per_case_delta` |
| material accuracy drop | `tests/eval/test_seeded_smoke_report.py::test_seeded_report_links_required_evidence` | `accuracy_delta` |

## CI Proof

The GitHub Actions workflow runs the seeded smoke command and asserts the command
returns exit code `1`. That keeps the workflow green while proving the
configured gate catches the seeded regression candidate.
