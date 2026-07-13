# v0.2.0 gdev-agent challenge evidence

Status: **verified canonical local run; gate FAIL**

Executed: 2026-07-13

Content address:
`sha256:656face21f27b496d4d3e8bb0b588824f5737d122c1275c710f3e5b15ff94b4b`

This package is the first committed 100-case challenge execution against a
fixed, clean `gdev-agent` revision. It is canonical evidence of what happened,
not a claim that the reference workload met the release thresholds.

## Fixed inputs

| Input | Value |
|---|---|
| Eval Lab source revision used to execute | `6defd741d6a33026163218ca5c28fb02f1ffd327` |
| Eval Lab harness version | `0.2.0` |
| gdev-agent revision | `0e4c5f0fd50382bbf12ffd35cfca4632384fb0cc` |
| gdev-agent image digest | `sha256:7dc9fef2ec6fe25745405546ec69f6a6f64c1bfa9f052dc54abfd65498a6f6da` |
| gdev-agent worktree | clean, detached at the revision above |
| Environment | local Docker Compose, deterministic demo mode, freshly recreated Redis/PostgreSQL containers |
| Dataset semantic hash | `151e5eec83373b92cf263aa1f32edb26ed780c260ce32a9d084ba8f3f38e53b0` |
| Dataset raw SHA-256 | `86d5ec4478afe29111256c954cf8840b9ee6857fa6af6e76de8e10de98062ee8` |
| Threshold raw SHA-256 | `5b8e311a86a87c5df116515eee06bff8c1cfb3b0ded3b499ed7c20ecd7f0c1bb` |
| Candidate-facing cases | 90 real local HTTP requests |
| Harness fault cases | 10 declared deterministic injections |

Redis reported zero keys before the run. The built-in HTTP adapter applied
request namespace
`gdev-eval-v1-5c65a837141710c3f31f9978823394bd6d51feb3889524dd1ca67bbcf27c4222`
to both `request_id` and `message_id`. The namespace is derived from the run ID,
candidate version, component revision, and dataset hash, so another candidate
or run cannot silently reuse these responses.

## Result

| Metric | Observed |
|---|---:|
| Reconciled pass rate | `0.32` |
| Classification accuracy | `0.244444` |
| Expected failures matched | `1.0` (`10/10`) |
| Unexpected failures | `68` |
| Blocking failures | `58` |
| Human-review-required outputs | `46` |
| Human escalation recall | `0.46` |
| Invalid structured output rate | `0.0` |
| Unsafe auto-approval rate | `0.0` |
| Cost per candidate case | `0.0 USD` in deterministic demo mode |
| Candidate latency p95 | `890.38 ms` |

Five gates failed: maximum blocking failures, minimum classification accuracy,
minimum human-review count, minimum human-escalation recall, and maximum
unexpected failures. Dataset cases and thresholds were not changed to make the
candidate pass.

The machine-readable source is
[challenge-run.json](gdev-agent-challenge/challenge-run.json). The generated
human view is
[challenge-report.md](gdev-agent-challenge/challenge-report.md). The terminal
run and seal are under [run/](gdev-agent-challenge/run/). The content-addressed
[manifest](gdev-agent-challenge/sha256-656face21f27b496d4d3e8bb0b588824f5737d122c1275c710f3e5b15ff94b4b.manifest.json)
declares all four generated artifacts.

## Verify

From the repository root:

```bash
python -m eval_ground_truth_lab.cli verify-evidence \
  --manifest docs/evidence/releases/v0.2.0/gdev-agent-challenge/sha256-656face21f27b496d4d3e8bb0b588824f5737d122c1275c710f3e5b15ff94b4b.manifest.json
```

Expected output includes `"verified": true`, `"artifact_count": 4`, and the
content address above.

## Reproduce

Start a clean `gdev-agent` Compose stack at the recorded component revision in
deterministic demo mode. Use a run store outside the evidence directory; the
command copies the sealed terminal run into the final package.

```bash
python -m eval_ground_truth_lab.cli run-gdev-agent-challenge \
  --dataset datasets/gdev_agent/challenge_v1.jsonl \
  --base-url http://127.0.0.1:8000 \
  --run-id <new-unique-run-id> \
  --run-dir /tmp/eval-lab-gdev-challenge-runs \
  --candidate-version gdev-agent-demo-0e4c5f0 \
  --component-revision 0e4c5f0fd50382bbf12ffd35cfca4632384fb0cc \
  --component-worktree-state clean \
  --component-image-digest sha256:7dc9fef2ec6fe25745405546ec69f6a6f64c1bfa9f052dc54abfd65498a6f6da \
  --environment-label local-compose-demo-clean-redis \
  --evidence-dir /tmp/gdev-challenge-evidence
```

The expected exit code for this exact candidate is `1`. Wall-clock latency and
the resulting content address can change between machines; dataset identity,
threshold identity, provenance, case outcomes, and the failed decision should
remain reviewable rather than being forced to match this byte-for-byte package.

## Interpretation boundary

The cases are self-authored synthetic data, the candidate runs locally, and the
ten provider failures are harness injections. This package does not establish
production quality, tenant-isolation enforcement, real-user behavior, external
adoption, independent labeling, or a production SLO. The public challenge is a
development diagnostic set, not a blind holdout.
