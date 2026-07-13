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
| `baseline` | yes | Completed, non-empty baseline RunRecord JSON path. |
| `candidate` | yes | Completed, non-empty candidate RunRecord JSON path. |
| `threshold-config` | yes | Comparison threshold JSON path. |
| `report` | no | Markdown report destination; defaults to `.eval-lab/release-gate.md`. |

Every path may be absolute or relative, but its resolved target must remain
inside `GITHUB_WORKSPACE`. Input files must exist and be regular files. The
report may not overwrite an input or use a symbolic-link leaf. NUL, CR, and LF
characters are rejected before evaluation. The helper uses Python argument
passing rather than a shell command. Two-phase validation first resolves the
report without touching it, then independently checks every input and rejects
path or hard-link aliases. Once the report is known to be safe and distinct
from all resolvable inputs, any previous target is removed even when another
input is invalid. A valid invocation writes to a unique file beside the target,
fsyncs it, and atomically places the requested report only after a fresh
comparison report exists. A writable workspace and report parent are caller
preconditions. The resolved workspace-relative paths are revalidated after
symlink resolution and reject line breaks, NUL, backticks, and table delimiters
before any path can appear in Markdown evidence.

### Decision-input contract

Both run artifacts must be canonical JSON objects with every decision-bearing
RunRecord field present. Each must have exact status `completed`, a non-empty
`completed_at`, and at least one case result. Case IDs must be non-empty and
unique within each run, and the baseline and candidate case-ID sets must match
exactly. The validator version, threshold-config version, and run type must also
match; the comparison engine continues to require the same dataset hash. Every
case must contain a non-empty set of results with unique, non-empty
`validator_id` values, boolean `passed`, and non-empty string `category`; the
validator-ID set for each corresponding case must match exactly across the two
runs. Optional receipt `message` must be a string and an optional nested
`case_id` must match its outer case. `category` is `none` exactly for passing
receipts. A corresponding validator may change from a passing `none` receipt to
a supported failure category; that regression is evaluated as a comparison
FAIL rather than an Action configuration error. Missing, truncated, or
malformed validator receipts remain configuration errors.

Run IDs must use the canonical RunStore-safe 1-128 character syntax. All
metadata and receipt strings that can appear in the Markdown report reject line
breaks, NUL, backticks, and table delimiters; receipt messages also reject raw
HTML delimiters. The report artifact itself is therefore fail-closed against
heading, code-span, table-cell, and raw-HTML injection.

Aggregate cost and latency values and every case-level cost/latency value must
be JSON numbers rather than booleans or numeric strings, finite, and
non-negative. Aggregate total/per-case cost and p50/p95 latency must recompute
exactly from the complete case results. This prevents omitted cases,
validator-result truncation, or caller-authored aggregate values from turning
an incomplete candidate into a PASS.

The Action accepts only complete per-case validator receipts. Failure-only or
sparse seeded CLI artifacts (including artifacts where both runs have an empty
`validator_results` list) are rejected until the core CLI emits complete
receipts for every evaluated case; they cannot produce an Action PASS.

Threshold JSON is strict and duplicate keys are rejected. The native schema
requires exactly these five decision fields and a non-empty string `version`:

- `max_accuracy_drop`;
- `max_invalid_output_rate_increase`;
- `max_unsafe_auto_approval_rate_increase`;
- `max_latency_p95_delta_ms`;
- `max_cost_per_case_delta_usd`.

The threshold `version` must equal `threshold_config_version` in both run
artifacts. A missing or mismatched version is an Action configuration error, so
a caller cannot apply an unbound relaxed policy to runs that name another
policy version.

The documented legacy gdev comparison schema remains supported with all five
of its comparison fields and `version` required. Missing and unknown fields, booleans,
numeric strings, negative values, non-standard `NaN`/`Infinity`, and
floating-point overflow such as `1e309` are rejected. Accuracy, rate, and drop values must be
within `[0, 1]`; cost and latency allowances must be finite and non-negative.
Valid native and legacy configurations retain the CLI's comparison semantics.

The Action emits:

- `report`: the normalized, workspace-relative path to the fresh report;
- `conclusion`: `pass` or `fail` for a completed comparison, and `error` for
  invalid configuration or execution errors.

Input links recorded in the report are normalized to workspace-relative paths,
so an otherwise identical decision does not embed an ephemeral runner checkout
directory.

`pass` returns status `0`. A threshold-blocked `fail` still publishes the fresh
report and summary, then returns status `1`. Configuration or execution errors
return status `2`, emit no report path, remove the configured target, and never
copy a pre-existing target into `GITHUB_STEP_SUMMARY`. This makes a fixed-path
`if: always()` artifact uploader unable to mistake an earlier PASS report for
the current decision. An unsafe or unresolved report path is rejected without
touching its target. If filesystem permissions deny cleanup, the Action reports
an error and keeps its `report` output empty, but cannot guarantee deletion.

Never upload the configured fixed path on an Action error. Artifact steps must
use the non-empty `steps.<id>.outputs.report` value only when `conclusion` is
exactly `pass` or `fail`; `conclusion=error` is never publishable evidence.

## Security boundary

- Recommended caller permissions are `contents: read`; the Action does not use
  the GitHub API, push changes, or request a token.
- Caller checkout should set `persist-credentials: false`.
- Runner output and summary files are written directly with Python, not through
  workflow-command interpolation or generated shell fragments.
- Existing report content is removed after path validation and never read as
  current evidence. Only the unique report created by this invocation can be
  published or summarized. In a writable workspace, an Action error leaves the
  configured target absent; cleanup denial remains an error with blank output.
- The report preview in `GITHUB_STEP_SUMMARY` is bounded; the full workspace
  report remains authoritative.

The comparison Action path uses only Python's standard library and the pinned
Eval Lab source included in the Action checkout. It performs no package-index
download.

## Claim boundary

This Action automates an existing baseline/candidate threshold decision. It
does not generate runs, authenticate their origin, replace content-addressed
evidence verification, or establish that the dataset and thresholds represent
real users. Receipt categories are artifact inputs: structural validation does
not prove that a producer assigned an authentic category. Artifact and category
origin authenticity remain outside this Action's boundary. The repository CI
smoke compares the committed synthetic/local baseline run with itself only to
prove the wiring and PASS status propagation. That smoke is not a production
evaluation, production safety claim, external validation, user metric, or proof
that an unevaluated system is safe to release.
