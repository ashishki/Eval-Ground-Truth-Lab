# Trader Risk Audit sanitized evidence adapter

Status: implemented pinned import/replay contract for one fully synthetic fixture.

## Product boundary

Trader Risk Audit remains a separate applied FinTech product. It owns trade
normalization, policy rules, deterministic findings, P&L attribution, reporting,
and the upstream `eval-export` command. Eval Ground Truth Lab owns the versioned
expected case, fail-closed import adapter, deterministic comparison, sealed run,
gate decision, and content-addressed replay evidence.

There is no code import from Trader Risk Audit and no product merge. The adapter
reads only its sanitized JSON export. It does not run the Trader rule engine,
read raw trades, choose risk thresholds, infer financial ground truth, or apply
investment advice.

## Pinned source

The committed v1 fixture is exported by Trader Risk Audit package `0.2.0` using
contract `trader-risk-audit-evidence-v1`. Its provenance record pins:

- path-purged publication-candidate commit
  `bf755a24450ff7c17328fa6d447f36bea8ea0fe5`;
- tree `1a2c4ff91a7504642a1bae05a9487fa2e898e0b6`;
- Git blob `9a64dc98e8edbe1ec39756611a6cb3b73b4994b9`;
- protected public-candidate bundle SHA-256
  `2c5b36afa9b2a9847de1c97789c52c57600e1d38cfd4947458906ee3bb3992ca`;
- fixture SHA-256
  `9925144d39bd41d6fdf8f54a1bbd900c871f1bb73cd008980baa2ae1f2d51ced`;
- upstream evidence content hash
  `d7e6fe92f50ba410a2c23882ea617b38081a8bbe84fe66727dfaecca115eb63f`.

The adapter independently recomputes the fixture SHA-256, Git blob identity,
and upstream evidence content hash. The bundle digest is a provenance pin; the
protected bundle is not distributed or opened by this command. Local hashes
detect drift but do not authenticate a publisher.

## Fail-closed validation

Before Eval validators run, the adapter requires the exact v1 field shape and
checks all of the following:

- contract, package, case, and provenance version agreement;
- lowercase SHA-256 and full Git object identifiers;
- source fixture bytes against the pinned SHA-256 and Git blob;
- canonical upstream `evidence_content_hash` recomputation;
- required, unique, name-sorted artifact digests without artifact paths;
- exact boolean manifest, trace-resolution, and P&L checks;
- bounded finite metrics and status/check consistency;
- opaque `sha256-v1` rule, row, and violation trace-reference shapes;
- dataset cases cannot select a different evidence path or configure execution.

Eval validators then compare the verified export with the versioned one-case
synthetic expectation: adapter/contract version, source commit/tree/bundle,
evidence identities, candidate version, checks, aggregate observations, and
status. A mismatch returns a failing gate and still writes evidence. A malformed
or tampered source fails loading before a gate can be claimed.

## Reproduce

Keep the mutable run store outside the evidence pack:

```bash
eval-ground-truth-lab run-trader-risk-audit-replay \
  --dataset datasets/trader_risk_audit/synthetic_quickstart_v1.jsonl \
  --evidence datasets/trader_risk_audit/fixtures/synthetic_quickstart_v1/eval-evidence.json \
  --provenance datasets/trader_risk_audit/synthetic_quickstart_v1.provenance.json \
  --run-id trader-synthetic-quickstart-v1 \
  --run-dir /tmp/eval-lab-trader-runs \
  --evidence-dir /tmp/eval-lab-trader-evidence

eval-ground-truth-lab verify-evidence \
  --manifest /tmp/eval-lab-trader-evidence/sha256-*.manifest.json
```

The first command writes the replay JSON, Markdown decision, exact input files,
checksum-sealed run record, and content-addressed manifest. Its decision is
deterministic for the pinned inputs; timestamps and the resulting pack content
address identify the individual execution and therefore are not expected to be
byte-identical across new runs.

## Evidence interpretation

The committed input contains four invented trade observations and seven
deterministic rule observations. It represents no person, account, broker,
customer, design partner, or production workload. Independent annotators: `0`.
External workflow owners represented: `0`.

A PASS proves only that Eval Lab can verify and apply exact expectations to this
specific sanitized contract fixture. It does not establish raw-data correctness,
suitable policy thresholds, investment performance, production reliability,
external adoption, or the audit report's usefulness to a real user. A real
external adapter/case study and real design-partner validation remain separate
milestones that cannot be satisfied by this repository-authored fixture.

The committed 2026-07-13 replay is indexed at
`docs/evidence/integrations/README.md` and verifies at content address
`sha256:ed96a622a850f72dda4e0c804e4d4251932e646ac7384ed1499d379afef203c9`.
