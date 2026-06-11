# CODEX_PROMPT.md

Version: 1.0
Date: 2026-06-11
Phase: 1

This file is the session-state handoff for Codex work. Repository artifacts,
tests, eval outputs, CI, and audit reports outrank chat memory and generated
summaries.

## Current State

- Phase: 4
- Baseline: 34 passing tests
- Ruff: configured
- Last CI run: not yet run
- Last updated: 2026-06-11
- Session tokens (approx): not tracked
- Cumulative phase tokens (approx): not tracked
- Session cost (approx): not tracked
- Cumulative phase cost (approx): not tracked
- Budget status: within budget; T09 judge path uses injected providers only and
  no real model spend has been recorded

## Continuity Pointers

- Decision log: `docs/DECISION_LOG.md`
- Implementation journal: `docs/IMPLEMENTATION_JOURNAL.md`
- Evidence index: `docs/EVIDENCE_INDEX.md`
- Cost budget: `docs/COST_BUDGET.md`
- Task-scoped context: read `Context-Refs` in `docs/tasks.md` before broad searching
- Project brief: `docs/PROJECT_BRIEF.md`

## Instructions for Codex

Before starting any task:

1. Read `docs/IMPLEMENTATION_CONTRACT.md`.
2. Read the target task in `docs/tasks.md`.
3. Read only the task's `Context-Refs` unless the change is architecture-shaping,
   security-sensitive, ambiguous, or blocked by missing context.
4. Run `python -m pytest tests -q --tb=short` to capture the current baseline.
5. Run `ruff check src tests` and `ruff format --check src tests`.
6. Stop for approval before changing mode, runtime tier, judge authority, budget
   limits, threshold policy, or profile status.

Implementation rules:

- Work one task at a time.
- Keep edits within the declared file scope unless the task evidence proves a
  scope change is necessary.
- Add or update tests with behavior changes.
- Do not self-review meaningful implementation changes.
- Update this file only at phase boundaries or when state changes materially.

## Next Task

T11: Seeded Regression CI Smoke Gate

## Fix Queue

empty

## Correction Budget

- Max implementation correction turns: 2.
- Max test-healing turns: 2 for normal tasks.
- Escalate after repeated failure output, increased failure count, out-of-scope
  file need, budget exhaustion, or any proposal to weaken tests or acceptance
  criteria.
- Preserve failed command output and changed-file evidence before a correction
  turn.

## Cost Budget State

- Budget artifact: `docs/COST_BUDGET.md`
- Telemetry source: provider-agnostic JSONL sink implemented in T09;
  conventional path is `docs/ai_cost_telemetry.jsonl`
- Last rollup: not run
- Per-task budget: deterministic tasks use 0 USD model spend
- Per-run budget: judge-enabled benchmark cap is 2 USD unless approved
- Monthly project budget: provisional 25 USD until revised
- Approval required before: model escalation, judge fan-out increase, retry
  expansion, tool-call expansion, scheduled judge runs, or budget overrun
- Last recorded AI/model cost: none; T09 tests used synthetic injected providers

If the next task would exceed the declared budget, increase model class, increase
retry/fan-out/tool-call limits, or add recurring AI usage, stop for approval
before implementation.

## Open Findings

none

## Profile State: RAG

- RAG Status: OFF
- Active corpora: n/a
- Retrieval baseline: n/a
- Open retrieval findings: none
- Index schema version: n/a
- Pending reindex actions: none
- Retrieval-related next tasks: none
- Retrieval-driven tasks: none

## Tool-Use State

- Tool-Use Profile: OFF
- Registered tool schemas: n/a
- Unsafe-action guardrails: n/a
- Open tool findings: none

## Agentic State

- Agentic Profile: OFF
- Active agent roles: n/a
- Loop termination contract version: n/a
- Cross-iteration state mechanism: n/a
- Open agent findings: none

## Planning State

- Planning Profile: OFF
- Plan schema version: n/a
- Plan validation method: n/a
- Open plan findings: none

## Compliance State

- Compliance Status: OFF
- Active frameworks: n/a
- Controls implemented: n/a
- Controls partial: n/a
- Controls not started: n/a
- Evidence artifact: n/a
- Open compliance findings: none
