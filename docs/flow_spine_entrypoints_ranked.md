# Flow Spine Entrypoints Ranked (Phase1B)

- head: cddc0ef127ba496d0dfab3a21dd6fd34c55e5881
- date: 2026-01-31 00:26:45

## Scoring

Files are ranked by a heuristic score across entrypoint indicators (e.g., __main__, argparse, def main, evidence markers, publish guard).
This report is advisory; Phase1C will select one spine authority and keep behavior unchanged.

## Top Candidates

| score | file | __main__ | argparse | def_main | main( | run( | validate | contract_id | receipt.latest | _evidence | publish_guard |
|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 77 | app\gui\planner.py | 0 | 0 | 3 | 5 | 0 | 3 | 11 | 0 | 9 | 0 |
| 62 | app\gui\main.py | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 20 | 0 |
| 8 | app\validation\schema_validation.py | 0 | 0 | 0 | 0 | 0 | 4 | 0 | 0 | 0 | 0 |
| 8 | app\validation\vendor_schema_loader.py | 0 | 0 | 0 | 0 | 0 | 4 | 0 | 0 | 0 | 0 |
| 8 | app\main.py | 0 | 0 | 1 | 2 | 0 | 0 | 0 | 0 | 0 | 0 |
| 6 | app\gui\store.py | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 0 |

## Next

Phase1C will:
- pick the single spine authority file/function from the top candidates
- introduce a stable internal spine wrapper (no behavior change)
- then thin CLI to call the spine

