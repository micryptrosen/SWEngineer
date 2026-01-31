# Flow Spine Selection (Phase1C)

- head: 8d6610d538f53d467c4d10c4b970d9e3e6a547d8
- date: 2026-01-31 00:29:02

## Selected authority nucleus

- app\\gui\\planner.py

## Rationale

- Highest Phase1B heuristic score.
- Concentrates plan/validate/contract_id references.
- Evidence-related references present (likely current operational center).

## Phase rule

- Phase1C adds a stable internal spine wrapper module only.
- No rewiring of CLI/GUI entrypoints in this phase.
- No behavior changes.

## Next (Phase1D)

- Wire the thinnest entrypoint to call swe_runner.flow_spine.run_flow(...).
- Keep pytest green and preserve existing outputs.
