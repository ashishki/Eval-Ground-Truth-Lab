# Reusable GitHub release gate

The root `action.yml` exposes Eval Ground Truth Lab's deterministic `compare`
command as a composite GitHub Action. It compares two completed RunRecord JSON
artifacts against one threshold configuration, writes a Markdown decision
report, emits normalized outputs, and returns the underlying gate status. A
blocking comparison therefore fails the Action step instead of being converted
into a green workflow.

## Caller example

Pin both checkout and this Action to reviewed full commit SHAs. The Action needs
no write permission and no repository credential:

```yaml
name: Candidate release gate

on:
  pull_request:

permissions:
  contents: read

jobs:
  release-gate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@93cb6efe18208431cddfb8368fd83d5badbf9bfd # v5.0.1
        with:
          persist-credentials: false

      - name: Compare candidate with baseline
        id: eval-gate
        uses: ashishki/Eval-Ground-Truth-Lab@<reviewed-full-commit-sha>
        with:
          baseline: artifacts/baseline-run.json
          candidate: artifacts/candidate-run.json
          threshold-config: policy/release-thresholds.json
          report: artifacts/release-gate.md
```

The caller must produce or check out the baseline, candidate, and threshold
files before invoking the Action. The Action sets up Python with a full-SHA pin,
loads the pinned Action checkout's local `src` tree without a package-index
install, and passes all caller inputs to a Python helper through environment
variables. User-controlled input values are never interpolated into shell
source.

## Inputs and outputs

| Name | Required | Meaning |
| --- | --- | --- |
| `baseline` | yes | Baseline RunRecord JSON path. |
| `candidate` | yes | Candidate RunRecord JSON path. |
| `threshold-config` | yes | Comparison threshold JSON path. |
| `report` | no | Markdown report destination; defaults to `.eval-lab/release-gate.md`. |

Every path may be absolute or relative, but its resolved target must remain
inside `GITHUB_WORKSPACE`. Input files must exist and be regular files. The
report may not overwrite an input or use a symbolic-link leaf. NUL, CR, and LF
characters are rejected before evaluation. The helper uses Python argument
passing rather than a shell command, writes to a unique file beside the target,
fsyncs it, and atomically replaces the requested report only after a fresh
comparison report exists.

The Action emits:

- `report`: the normalized, workspace-relative path to the fresh report;
- `conclusion`: `pass` or `fail` for a completed comparison, and `error` for
  invalid configuration or execution errors.

Input links recorded in the report are normalized to workspace-relative paths,
so an otherwise identical decision does not embed an ephemeral runner checkout
directory.

`pass` returns status `0`. A threshold-blocked `fail` still publishes the fresh
report and summary, then returns status `1`. Configuration or execution errors
return status `2`, emit no report path, and never copy a pre-existing target
into `GITHUB_STEP_SUMMARY`. Consumers that need to inspect outputs after a
failure should use an `if: always()` follow-up step.

## Security boundary

- Recommended caller permissions are `contents: read`; the Action does not use
  the GitHub API, push changes, or request a token.
- Caller checkout should set `persist-credentials: false`.
- Runner output and summary files are written directly with Python, not through
  workflow-command interpolation or generated shell fragments.
- Existing report content is never read as current evidence. Only the unique
  report created by this invocation can be published or summarized.
- The report preview in `GITHUB_STEP_SUMMARY` is bounded; the full workspace
  report remains authoritative.

The comparison Action path uses only Python's standard library and the pinned
Eval Lab source included in the Action checkout. It performs no package-index
download.

## Claim boundary

This Action automates an existing baseline/candidate threshold decision. It
does not generate runs, authenticate their origin, replace content-addressed
evidence verification, or establish that the dataset and thresholds represent
real users. The repository CI smoke compares the committed synthetic/local
baseline run with itself only to prove the wiring and PASS status propagation.
That smoke is not a production evaluation, production safety claim, external
validation, user metric, or proof that an unevaluated system is safe to release.
