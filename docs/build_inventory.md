# SWEngineer Build Inventory (Phase0)

- generated: 2026-01-31 00:21:02
- anchor tag: v0.2.9-phase5-step5it-publish-interlock_20260130_095545
- head: e24447ce5afa8c047273bce79f9412dacf67a78e
- branch: work-flow-reorg-from-anchor

## CLI / Entry Points

- app/gui/__main__.py
- app/gui/main.py
- app/main.py
- src/swe_runner/main.py

## Runner Surfaces

- contracts/run_handoff.schema.json

## Planner

- (none detected by heuristic)

## Validator / Schemas

- app/schema_locator.py
- app/validation/schema_validation.py
- tools/validate_ci.py

## Evidence / Receipts / Manifests

- (none detected by heuristic)

## Tests

- tests/conftest.py
- tests/test_gui_handoff_runner_parity.py
- tests/test_gui_imports.py
- tests/test_gui_store.py
- tests/test_handoff_schema_negative.py
- tests/test_handoff_sha256.py
- tests/test_phase2e_canonical_sha256.py
- tests/test_phase2f_bootstrap_imports.py
- tests/test_phase2f_entrypoints_bootstrap.py
- tests/test_phase3_step3d_vendor_schema_root.py
- tests/test_phase3_step3h_validator_uses_vendor_root.py
- tests/test_phase3_step3j_isolated_import_invariant.py
- tests/test_phase3_step3k_isolation_contract.py
- tests/test_phase3_step3l_runner_validator_schema_root_unified.py
- tests/test_phase3_step3m_runner_no_schema_root_cache.py
- tests/test_phase3_step3n_isolated_import_planner.py
- tests/test_phase3_step3o_isolated_e2e_planner_handoff_validation.py
- tests/test_phase4_step4a_schema_coverage_gate.py
- tests/test_phase5_step5a_contract_id_normalization.py
- tests/test_phase5_step5io_no_refresolver_regression.py
- tests/test_phase5_step5is_publish_interlock_guard.py
- tests/test_planner_approval.py
- tests/test_planner_clone_supersede.py
- tests/test_planner_run_plan.py
- tests/test_schema_root_vendor.py
- tests/test_schema_validation_negative_fixtures.py
- tests/test_schema_validation_runner_parity.py
- tests/test_sha_legacy_window_governance.py
- tests/test_smoke.py
