# SWEngineer Flow Spine Contract (Phase1A)

- head: 14c9544613a54133c364eb0132cc94212a8c3380
- date: 2026-01-31 00:25:25

## Objective

Restore Best Build Practices ordering by enforcing a single internal flow spine that owns side effects.

## Canonical Flow Order

1. build_plan(intent)  -> Plan
2. validate_plan(plan) -> ValidatedPlan (or fail with report)
3. execute_plan(validated_plan, context) -> RunResult (side effects allowed)
4. emit_evidence(run_result) -> receipts/manifests (deterministic)
5. publish_if_allowed(run_result) -> publish outputs (gated + explicit unlock)

## Authority Rules

- Single execution authority: only execute_plan() may perform side effects.
- Validation boundary: execute_plan() MUST reject unvalidated plans.
- Help vs identity separation: CLI help text is documentation only; runtime identity belongs in evidence/run_result.
- CLI is a thin adapter: CLI parses args, loads inputs, calls the spine. No execution decisions in CLI.

## Test Layering Rules

- Help tests assert help availability/format only.
- Execution identity tests assert evidence/run_result fields only (never help output).
- Determinism tests re-run execute_plan() and compare canonical evidence (json+sha where required).

## Non-goals (Phase1A)

- No behavior changes.
- No new commands.
- No refactors outside the spine boundary definition.

