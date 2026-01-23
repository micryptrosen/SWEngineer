# External Runner Specification (RUN_HANDOFF)

## Purpose
This document defines how an **external execution environment** may consume
a RUN_HANDOFF artifact produced by SWEngineer.

SWEngineer **never executes commands**.

## Mandatory Rules
- GUI output is inert
- Runner MUST re-run all required gates
- Runner MUST verify payload_sha256 before execution
- Runner MUST require human authority before execution
- No commit/tag allowed unless gates are GREEN

## Minimal Runner Flow
1. Load RUN_HANDOFF JSON
2. Validate against run_handoff.schema.json
3. Recompute sha256 (excluding payload_sha256)
4. Re-run required gates
5. Require explicit human authorization
6. Execute commands (outside SWEngineer)
7. Record execution evidence separately

## Non-Negotiables
- SWEngineer is planner-only
- No auto-execution
- No implicit trust
