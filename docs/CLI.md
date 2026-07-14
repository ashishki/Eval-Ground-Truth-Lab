# CLI

Eval Ground Truth Lab is CLI-first. Commands write local artifacts and use
deterministic validators by default.

## Commands

```bash
python -m eval_ground_truth_lab.cli --help
python -m eval_ground_truth_lab.cli seeded-smoke --help
python -m eval_ground_truth_lab.cli dataset-inspect --help
python -m eval_ground_truth_lab.cli run-gdev-agent --help
python -m eval_ground_truth_lab.cli run-gdev-agent-challenge --help
python -m eval_ground_truth_lab.cli run-trader-risk-audit-replay --help
python -m eval_ground_truth_lab.cli verify-evidence --help
python -m eval_ground_truth_lab.cli compare --help
python -m eval_ground_truth_lab.cli cost-rollup --help
python -m eval_ground_truth_lab.cli budget-check --help
```

## Dataset Inspect

```bash
python -m eval_ground_truth_lab.cli dataset-inspect \
  --dataset datasets/gdev_agent/triage_v1.jsonl
```

Prints dataset ID, schema version, case count, and dataset hash.

## Run gdev-agent

```bash
python -m eval_ground_truth_lab.cli run-gdev-agent \
  --dataset datasets/gdev_agent/triage_v1.jsonl \
  --base-url http://localhost:8000 \
  --run-id gdev-baseline-v1 \
  --candidate-version gdev-agent-demo \
  --component-revision <full-gdev-git-sha> \
  --report reports/gdev-agent/baseline_report.md
```

The command writes a run artifact under `runs/` by default and writes a markdown
report at the requested path. It uses `GDEV_AGENT_*` environment variables for
tenant and webhook configuration unless a caller injects an adapter in code.
Terminal runs also have a `.sha256` seal; this detects accidental/tampering
changes but is not a filesystem immutability guarantee.
`--component-revision` must be a full 40- or 64-character revision (or an
explicit `fixture:` identity in tests). Together with the run ID, candidate
version, and dataset hash, it produces the deterministic namespace applied to
live HTTP `request_id` and `message_id` values.

## Run gdev-agent Challenge

```bash
eval-ground-truth-lab run-gdev-agent-challenge \
  --base-url http://localhost:8000 \
  --run-id <new-unique-run-id> \
  --run-dir /tmp/eval-lab-gdev-challenge-runs \
  --candidate-version gdev-agent-demo \
  --component-revision <full-gdev-git-sha> \
  --component-worktree-state clean \
  --environment-label local-compose-demo \
  --evidence-dir /tmp/gdev-challenge-evidence
```

The command evaluates 90 candidate-facing cases and injects ten declared
provider faults in the harness. It writes machine-readable JSON first, renders
Markdown only from that JSON object, copies the terminal run/seal, and writes a
content-addressed manifest last. Every declared challenge threshold affects the
gate; failed gates exit `1` without deleting the evidence.
Challenge JSON and manifest metadata both record the request namespace,
namespace inputs, and whether a real gdev HTTP adapter or a custom passthrough
adapter handled the cases.
Keep `--run-dir` outside `--evidence-dir`: the command copies the sealed terminal
run into the evidence directory's own `run/` subdirectory during finalization.

## Replay Trader Risk Audit sanitized evidence

```bash
eval-ground-truth-lab run-trader-risk-audit-replay \
  --run-id trader-synthetic-quickstart-v1 \
  --run-dir /tmp/eval-lab-trader-runs \
  --evidence-dir /tmp/eval-lab-trader-evidence
```

The default dataset, evidence export, provenance, and offline Git-object proof
are package resources for the fully synthetic quickstart fixture, so an
installed wheel works outside a repository checkout. The command reads every
input once and uses those exact bytes for validation, hashing, replay, and
packaging. It requires exactly one v1 case, checks the complete sealed result
without unknown nested fields, and writes an eight-artifact content-addressed
evidence pack. Exact case/input and synthetic metadata allowlists, recursive
duplicate-key rejection, and strict
expected-payload shapes run before any output directory is created. Only the
byte-identical packaged dataset receives fixture/privacy claims; schema-valid
overrides are marked caller-supplied and not privacy-reviewed. A validator
mismatch exits `1` and retains the pack; malformed, tampered, empty, or
multi-case input fails closed without a PASS pack.

Evidence/provenance overrides receive no packaged source or privacy claims,
even if the caller recomputes every internal hash and retains canonical ids.
Packaged source trust additionally requires the proof to bind the exact commit,
root tree, repository path, and evidence blob. Direct adapter output preserves
the input values only as `declared_privacy_classification` and `declared_source`
and reports unassessed effective trust. Replay writes a separate
`effective_trust` decision before RunStore sealing. A matching caller expectation
can therefore PASS compatibility validators while the result, manifest, report,
candidate identity, and sealed run remain explicitly unreviewed.

The packaged terminal JSON and seal come directly from the immutable RunStore
completion snapshot. Result and manifest bind their hashes plus run id,
candidate, dataset, validator, and completed status. Implementation provenance
also binds the parser, RunStore, manifest writer, remaining decision modules,
complete package payload, and either an exact HEAD match for the recursive
measured-package path set, bytes, and executable modes or an installed-artifact
digest. It makes no whole-worktree cleanliness claim.

This is a contract compatibility replay, not a live Trader execution, financial
policy benchmark, external-user case study, or production evidence. See
`docs/TRADER_RISK_AUDIT_ADAPTER.md` for the product and claim boundary.

## Verify Evidence

```bash
eval-ground-truth-lab verify-evidence \
  --manifest /tmp/gdev-challenge-evidence/sha256-*.manifest.json
```

Verification fails for a changed or deleted artifact, manifest/content-address
mismatch, symlink, or an undeclared added file.

## Compare

```bash
python -m eval_ground_truth_lab.cli compare \
  --baseline runs/gdev-baseline-v1.json \
  --candidate runs/gdev-candidate-v2.json \
  --threshold-config datasets/gdev_agent/thresholds.json \
  --report reports/gdev-agent/comparison_report.md
```

The command exits `1` when comparison thresholds have a blocking failure.
It exits `0` only for a valid non-blocking comparison, `1` only for a valid
blocking decision, and `2` for invalid input or report-generation failure.
Invalid input is reported on stderr as an Eval comparison error; it is never
presented as an ordinary threshold failure.

Both run artifacts must be completed and non-empty, contain the same unique
case IDs, and carry the same non-empty validator-ID set for each case. Run type,
validator version, run threshold-policy version, and the threshold file's
declared version must agree. Validator outcomes and categories may change: that
is decision evidence, not a schema mismatch. A candidate `passed: true` to
`passed: false` validator transition is blocking regardless of category;
baseline-known failures are not new regressions and candidate recoveries are
allowed.

Run and policy JSON rejects duplicate keys recursively. Decision metrics must be
finite and non-negative, match the complete case-result aggregates, and stay at
or below `2^53 - 1`. Integer values must be exactly representable in that
domain; decimal values must use a lossless shortest-round-trip spelling before
conversion. Rate/drop thresholds are additionally limited to `[0, 1]`.
Native delta thresholds and the documented legacy gdev threshold schema remain
supported, but missing, mixed, or unknown threshold fields fail closed.

Gate status uses exact arithmetic after validation: count-derived accuracy and
failure rates are rational fractions; cost per case is the exact rational mean
of canonical case costs; latency p95 is the exact selected canonical case value;
and policy decimals retain their exact value, including the complement of the
legacy accuracy minimum. Reports show the exact delta and exact gate expression,
so high-magnitude subtraction and a finite decimal approximation of `1/3`
cannot round a blocking regression into PASS. Float delta attributes remain
presentation-compatible views, not the source of gate authority.

`output` may be any JSON value. `output.correct` remains optional when output is
an object: when absent, or when output is non-object, it retains the established
comparison meaning of "not counted as correct"; when present, it must be a
boolean. Validator receipts, rather than an invented accuracy value, remain
authoritative for validator-only outcomes.

When `run_compare_command` has verified that `--report` is a regular-file
target that does not alias an input, it removes any stale target before reading
the comparison inputs. Success and valid blocking failure publish through a
same-directory fsync/atomic-replace write. Any later input or execution error
leaves no report at that target. A report symlink or input alias is rejected
without modifying the linked/input file. Failures before the helper is invoked
are outside this cleanup guarantee.

## Cost Rollup

```bash
python -m eval_ground_truth_lab.cli cost-rollup \
  --telemetry docs/ai_cost_telemetry.jsonl \
  --out reports/cost/latest.json
```

The command reads provider-agnostic JSONL telemetry and writes a deterministic
rollup with total cost, total tokens, cost by model/workflow/case, p95 latency,
retry count, judge call count, and quality outcome distribution.

## Budget Check

```bash
python -m eval_ground_truth_lab.cli budget-check \
  --rollup reports/cost/latest.json \
  --policy docs/cost_policy.json
```

The command exits `1` when the rollup exceeds `per_run_budget_usd`,
`monthly_project_budget_usd`, `cost_per_case_ceiling`, or
`judge_call_count_ceiling`. CI should use fixture telemetry by default. Live
judge cost gates require telemetry rollup artifacts and an approved budget
policy before they are enforced.
