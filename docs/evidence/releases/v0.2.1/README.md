# Eval Lab v0.2.1 fail-closed comparison evidence

This content-addressed pack records five synthetic, local executions of the
shared comparison contract from implementation commit `31120c809cc4935c9f5ffbb2cb539a3018d38d92`
and tree `8cbbff195bbae0ee5309d94c38ad27e8215c755e`. The loaded execution binding is
`423d9bc2bf89438b147485f88b4b251b6c872d62b00fea998c97904828da15b3`.

The scenarios demonstrate the complete comparison CLI exit contract:

1. a valid no-regression comparison passes every metric and exits `0`;
2. an arbitrary-category validator receipt changing from pass to fail blocks
   even when all five metric thresholds pass;
3. an exact `0.1` high-magnitude cost delta blocks against `0.09999` instead of
   cancelling through binary-float subtraction;
4. an exact `-1/3` accuracy delta blocks against the finite decimal threshold
   `0.3333333333333333`;
5. recursively invalid JSON exits `2` and removes a pre-existing stale report.

The three valid regressions exit `1`, so the pack covers statuses `0`, `1`, and
`2` without treating invalid input as an ordinary policy decision.

`receipts/command-results.json` records normalized commands, exit codes, exact
decisions, report hashes, stale-target invalidation, package provenance, and the
execution binding. The reports link only pack-relative raw inputs. Verify the
pack with `eval-ground-truth-lab verify-evidence --manifest sha256-*.manifest.json`.

## Reproduce

From the evidence commit that contains the generator, create a clean detached
worktree for the recorded implementation and choose a new empty output path:

```bash
SOURCE=/tmp/eval-lab-v021-source
OUTPUT=/tmp/eval-lab-v021-evidence
git worktree add --detach "$SOURCE" 31120c809cc4935c9f5ffbb2cb539a3018d38d92
test ! -e "$OUTPUT"
python3 tools/generate_v021_release_evidence.py --source-root "$SOURCE" --output-root "$OUTPUT"
diff -qr docs/evidence/releases/v0.2.1 "$OUTPUT"
```

On the receipt's recorded Python/platform runtime, generation is byte-stable:
`diff -qr` is silent and exits `0`, including the manifest filename and content
address. A different runtime or platform is recorded explicitly and therefore
can produce a different receipt and content address.

## Claim boundary

v0.2.1 is an internal correctness and security patch. This pack is not evidence
of external-feedback-driven maintenance, external users, adoption, design
partners, production execution, or production quality. All run inputs are
self-authored synthetic fixtures executed locally; no financial or business
outcome is evaluated.
