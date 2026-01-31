# Flow Spine Discovery Report (Phase1A)

- head: 14c9544613a54133c364eb0132cc94212a8c3380
- date: 2026-01-31 00:25:25

## Candidate entrypoints (heuristic)

## build_plan / planner

pattern: Planner
* app\gui\main.py:2  SWEngineer GUI Shell (Planner-only)
* app\gui\main.py:59  from .planner import (
* app\gui\main.py:147  hint = QLabel("Planner-only. Tasks are inert records. Append-only task events.")
* app\gui\main.py:260  self._append_create(title, "User-added task (planner-only).")
* app\gui\main.py:267  self._append_status(t.task_id, t.title, "DONE", "Marked DONE in GUI (planner-only).")
* app\gui\main.py:561  subtitle = QLabel("Planner-only (Phase 2B)")
* app\gui\planner.py:2  Planner (Phase 2B)
* app\gui\planner.py:300  Emit fresh planner artifacts (plan + approval + handoff) into out_dir using the same code-path
* app\gui\planner.py:325  # Use existing planner primitives to ensure payload shape matches real GUI.
* app\gui\planner.py:350  "emitter": "app.gui.planner.emit_for_tests",
* app\gui\planner.py:428  # Tests call: planner.main(["--out", <dir>]) (preferred), else planner.main() fallback.

pattern: plan_
* app\gui\planner.py:9  - RUN_PLAN_APPROVAL
* app\gui\planner.py:10  - RUN_PLAN_SUPERSEDED
* app\gui\planner.py:38  supersedes_plan_ev_id: Optional[str] = None
* app\gui\planner.py:45  plan_ev_id: str
* app\gui\planner.py:55  prior_plan_ev_id: str
* app\gui\planner.py:56  new_plan_ev_id: str
* app\gui\planner.py:64  plan_ev_id: str
* app\gui\planner.py:112  supersedes_plan_ev_id=None,
* app\gui\planner.py:119  if plan.supersedes_plan_ev_id:
* app\gui\planner.py:121  f"RUN_PLAN {plan.task_id}: {plan.task_title} (supersedes {plan.supersedes_plan_ev_id})"
* app\gui\planner.py:135  store: GuiStore, prior_plan_rec: EvidenceRecord, new_notes: str
* app\gui\planner.py:137  prior = _json_loads_best_effort(prior_plan_rec.body)
* app\gui\planner.py:155  supersedes_plan_ev_id=prior_plan_rec.ev_id,
* app\gui\planner.py:160  def make_approval(plan_ev_id: str, reviewer: str, decision: str, notes: str) -> RunPlanApproval:
* app\gui\planner.py:165  contract="runplan_approval/1.0",
* app\gui\planner.py:167  plan_ev_id=plan_ev_id,
* app\gui\planner.py:176  summary = f"RUN_PLAN_APPROVAL {approval.plan_ev_id}: {approval.decision} by {approval.reviewer or 'UNKNOWN'}"
* app\gui\planner.py:179  kind="RUN_PLAN_APPROVAL",
* app\gui\planner.py:188  def make_superseded(prior_plan_ev_id: str, new_plan_ev_id: str, reason: str) -> RunPlanSuperseded:
* app\gui\planner.py:190  contract="runplan_superseded/1.0",
* app\gui\planner.py:192  prior_plan_ev_id=prior_plan_ev_id,
* app\gui\planner.py:193  new_plan_ev_id=new_plan_ev_id,
* app\gui\planner.py:200  summary = f"RUN_PLAN_SUPERSEDED {marker.prior_plan_ev_id} -> {marker.new_plan_ev_id}"
* app\gui\planner.py:203  kind="RUN_PLAN_SUPERSEDED",
* app\gui\planner.py:212  def _find_latest_approved_approval(store: GuiStore, plan_ev_id: str) -> Optional[EvidenceRecord]:
* app\gui\planner.py:215  if rec.kind != "RUN_PLAN_APPROVAL":
* app\gui\planner.py:218  if str(obj.get("plan_ev_id") or "") != plan_ev_id:
* app\gui\planner.py:226  store: GuiStore, plan_rec: EvidenceRecord, runner_label: str, notes: str
* app\gui\planner.py:228  if plan_rec.kind != "RUN_PLAN":
* app\gui\planner.py:231  approval = _find_latest_approved_approval(store, plan_rec.ev_id)
* app\gui\planner.py:235  plan_obj = _json_loads_best_effort(plan_rec.body)
* app\gui\planner.py:236  required_gates = list(plan_obj.get("required_gates") or [])
* app\gui\planner.py:237  commands = list(plan_obj.get("commands") or [])
* app\gui\planner.py:243  "plan_ev_id": plan_rec.ev_id,
* app\gui\planner.py:262  plan_ev_id=payload_no_sha["plan_ev_id"],
* app\gui\planner.py:283  summary = f"RUN_HANDOFF {plan_rec.ev_id} -> {handoff.runner_label}"
* app\gui\planner.py:306  plan_rec = persist_run_plan(s, plan)
* app\gui\planner.py:307  appr = make_approval(plan_rec.ev_id, reviewer="Michael A. Trosen", decision="APPROVED", notes="ok")
* app\gui\planner.py:309  persist_handoff_from_plan(s, plan_rec, runner_label="TEST_RUNNER", notes="handoff note")
* app\gui\planner.py:329  plan_rec = persist_run_plan(s, plan)

## validate_plan / validator

pattern: validate_
* app\gui\planner.py:24  from app.validation.schema_validation import validate_payload, canonical_sha256_for_payload
* app\gui\planner.py:280  validate_payload(payload)
* app\validation\schema_validation.py:109  def validate_payload(payload: Dict[str, Any]) -> None:
* app\validation\schema_validation.py:121  from app.validation.vendor_schema_loader import validate_against_vendor_schema
* app\validation\schema_validation.py:126  validate_against_vendor_schema(payload)
* app\validation\vendor_schema_loader.py:111  def validate_against_vendor_schema(payload: Dict[str, Any], schema_root: Optional[Path] = None) -> None:

pattern: schema
* app\engine\actions.py:9  # JSON actions schema (reference):
* app\engine\engine.py:13  "Schema:\n"
* app\gui\main.py:32  _VENDOR = _REPO / 'vendor' / 'swe-schemas'
* app\gui\planner.py:24  from app.validation.schema_validation import validate_payload, canonical_sha256_for_payload
* app\validation\schema_validation.py:8  import swe_schemas
* app\validation\schema_validation.py:11  class SchemaValidationError(Exception):
* app\validation\schema_validation.py:15  def resolve_schema_root(schema_root: Optional[str] = None) -> str:
* app\validation\schema_validation.py:18  - default resolves via swe_schemas.resolve_schema_root() (vendor-backed)
* app\validation\schema_validation.py:19  - MUST NOT silently fall back if missing; must raise SchemaValidationError.
* app\validation\schema_validation.py:22  if schema_root is None:
* app\validation\schema_validation.py:23  root = Path(swe_schemas.resolve_schema_root()).resolve()
* app\validation\schema_validation.py:25  root = Path(str(schema_root)).resolve()
* app\validation\schema_validation.py:27  raise SchemaValidationError(f"failed to resolve schema root: {e}") from e
* app\validation\schema_validation.py:30  raise SchemaValidationError(f"vendor schema root missing: {root}")
* app\validation\schema_validation.py:111  Validate vendor schema payload and enforce (canonical + legacy-window) SHA policy.
* app\validation\schema_validation.py:112  Raises SchemaValidationError on any validation failure.
* app\validation\schema_validation.py:115  raise SchemaValidationError("payload must be an object")
* app\validation\schema_validation.py:118  _ = resolve_schema_root(None)
* app\validation\schema_validation.py:121  from app.validation.vendor_schema_loader import validate_against_vendor_schema
* app\validation\schema_validation.py:123  raise SchemaValidationError(f"validator wiring error: {e}") from e
* app\validation\schema_validation.py:126  validate_against_vendor_schema(payload)
* app\validation\schema_validation.py:128  raise SchemaValidationError(str(e)) from e
* app\validation\schema_validation.py:132  raise SchemaValidationError("payload_sha256 missing")
* app\validation\schema_validation.py:135  raise SchemaValidationError("payload_sha256 mismatch (not canonical and not within legacy window)")
* app\validation\vendor_schema_loader.py:7  import jsonschema
* app\validation\vendor_schema_loader.py:12  # Replace deprecated jsonschema.RefResolver usage with referencing.Registry.
* app\validation\vendor_schema_loader.py:17  # vendor_schema_loader.py lives at: app/validation/vendor_schema_loader.py
* app\validation\vendor_schema_loader.py:18  # repo root is 3 parents up (vendor_schema_loader.py -> validation -> app -> repo)
* app\validation\vendor_schema_loader.py:28  def _build_registry(schema_root: Path) -> Registry:
* app\validation\vendor_schema_loader.py:30  Build a referencing.Registry containing *all* JSON resources under schema_root.
* app\validation\vendor_schema_loader.py:35  schema_root = Path(schema_root).resolve()
* app\validation\vendor_schema_loader.py:37  for fp in sorted(schema_root.rglob("*.json")):
* app\validation\vendor_schema_loader.py:41  # Skip non-JSON or unreadable files quietly; schemas should be valid JSON.
* app\validation\vendor_schema_loader.py:59  def _resolve_schema_root(schema_root: Optional[Path]) -> Path:
* app\validation\vendor_schema_loader.py:61  Default: vendor/swe-schemas (via swe_schemas.resolve_schema_root()).
* app\validation\vendor_schema_loader.py:64  if schema_root is None:
* app\validation\vendor_schema_loader.py:65  import swe_schemas  # vendor-pinned package
* app\validation\vendor_schema_loader.py:66  schema_root = Path(swe_schemas.resolve_schema_root())
* app\validation\vendor_schema_loader.py:67  schema_root = Path(schema_root).resolve()
* app\validation\vendor_schema_loader.py:68  if not schema_root.exists():

## execute_plan / execution

pattern: run_plan
* app\gui\main.py:60  clone_run_plan,
* app\gui\main.py:62  make_run_plan,
* app\gui\main.py:66  persist_run_plan,
* app\gui\main.py:274  plan = make_run_plan(t.task_id, t.title, notes=t.details)
* app\gui\main.py:275  persist_run_plan(self.store, plan)
* app\gui\main.py:277  self.detail.toPlainText() + "\n\nRun Plan saved to Evidence (kind=RUN_PLAN)."
* app\gui\main.py:340  self.btn_approve = QPushButton("Approve Selected RUN_PLAN")
* app\gui\main.py:350  self.btn_clone = QPushButton("Clone Selected RUN_PLAN (supersede)")
* app\gui\main.py:362  self.btn_handoff = QPushButton("Generate RUN_HANDOFF from Approved RUN_PLAN")
* app\gui\main.py:464  if sel is None or sel.kind != "RUN_PLAN":
* app\gui\main.py:476  if sel is None or sel.kind != "RUN_PLAN":
* app\gui\main.py:479  new_plan = clone_run_plan(self.store, sel, new_notes=new_notes)
* app\gui\main.py:489  if sel is None or sel.kind != "RUN_PLAN":
* app\gui\planner.py:8  - RUN_PLAN
* app\gui\planner.py:9  - RUN_PLAN_APPROVAL
* app\gui\planner.py:10  - RUN_PLAN_SUPERSEDED
* app\gui\planner.py:92  def make_run_plan(task_id: str, task_title: str, notes: str) -> RunPlan:
* app\gui\planner.py:116  def persist_run_plan(store: GuiStore, plan: RunPlan) -> EvidenceRecord:
* app\gui\planner.py:118  summary = f"RUN_PLAN {plan.task_id}: {plan.task_title}"
* app\gui\planner.py:121  f"RUN_PLAN {plan.task_id}: {plan.task_title} (supersedes {plan.supersedes_plan_ev_id})"
* app\gui\planner.py:125  kind="RUN_PLAN",
* app\gui\planner.py:134  def clone_run_plan(
* app\gui\planner.py:157  return persist_run_plan(store, plan)
* app\gui\planner.py:176  summary = f"RUN_PLAN_APPROVAL {approval.plan_ev_id}: {approval.decision} by {approval.reviewer or 'UNKNOWN'}"
* app\gui\planner.py:179  kind="RUN_PLAN_APPROVAL",
* app\gui\planner.py:200  summary = f"RUN_PLAN_SUPERSEDED {marker.prior_plan_ev_id} -> {marker.new_plan_ev_id}"
* app\gui\planner.py:203  kind="RUN_PLAN_SUPERSEDED",
* app\gui\planner.py:215  if rec.kind != "RUN_PLAN_APPROVAL":
* app\gui\planner.py:228  if plan_rec.kind != "RUN_PLAN":
* app\gui\planner.py:229  raise ValueError("selected evidence is not RUN_PLAN")
* app\gui\planner.py:233  raise ValueError("no APPROVED approval found for selected RUN_PLAN")
* app\gui\planner.py:305  plan = make_run_plan("T0001", "do thing", notes="n1")
* app\gui\planner.py:306  plan_rec = persist_run_plan(s, plan)
* app\gui\planner.py:328  plan = make_run_plan("T0001", "do thing", notes="n1")
* app\gui\planner.py:329  plan_rec = persist_run_plan(s, plan)
* app\gui\planner.py:338  (od / "run_plan.json").write_text(plan_rec.body, encoding="utf-8")
* app\gui\planner.py:403  plan = make_run_plan("T0001", "do thing", notes="n1")
* app\gui\planner.py:404  plan_rec = persist_run_plan(s, plan)
* app\gui\planner.py:414  (od / "run_plan.json").write_text(json.dumps(plan_obj, indent=2, sort_keys=True), encoding="utf-8")
* app\gui\planner.py:419  "emitted": ["run_plan.json", "run_handoff.json"],

## evidence emission

pattern: _evidence
* app\gui\main.py:193  ev = self.store.read_evidence()
* app\gui\main.py:207  self.store.append_evidence(
* app\gui\main.py:227  self.store.append_evidence(
* app\gui\main.py:406  ev = self.store.read_evidence()
* app\gui\main.py:417  self.store.append_evidence(rec)
* app\gui\main.py:428  self.store.append_evidence(rec)
* app\gui\main.py:455  def _selected_evidence(self) -> EvidenceRecord | None:
* app\gui\main.py:460  return next((e for e in self.store.read_evidence() if e.ev_id == ev_id), None)
* app\gui\main.py:463  sel = self._selected_evidence()
* app\gui\main.py:475  sel = self._selected_evidence()
* app\gui\main.py:488  sel = self._selected_evidence()
* app\gui\main.py:502  items = self.store.read_evidence()
* app\gui\main.py:515  match = next((e for e in self.store.read_evidence() if e.ev_id == ev_id), None)
* app\gui\main.py:569  self.btn_evidence = QPushButton("Evidence")
* app\gui\main.py:571  nav_layout.addWidget(self.btn_evidence)
* app\gui\main.py:579  self.panel_evidence = EvidencePanel(self.store, root)
* app\gui\main.py:584  content.addWidget(self.panel_evidence, 1)
* app\gui\main.py:590  self.btn_evidence.clicked.connect(lambda: self._show("evidence"))
* app\gui\main.py:595  self.panel_evidence.setVisible(which == "evidence")
* app\gui\main.py:599  self.panel_evidence.reload()
* app\gui\planner.py:124  ev_id=f"E{len(store.read_evidence()) + 1:04d}",
* app\gui\planner.py:130  store.append_evidence(rec)
* app\gui\planner.py:178  ev_id=f"E{len(store.read_evidence()) + 1:04d}",
* app\gui\planner.py:184  store.append_evidence(rec)
* app\gui\planner.py:202  ev_id=f"E{len(store.read_evidence()) + 1:04d}",
* app\gui\planner.py:208  store.append_evidence(rec)
* app\gui\planner.py:214  for rec in reversed(store.read_evidence()):
* app\gui\planner.py:285  ev_id=f"E{len(store.read_evidence()) + 1:04d}",
* app\gui\planner.py:291  store.append_evidence(rec)
* app\gui\store.py:101  def append_evidence(self, rec: EvidenceRecord) -> None:
* app\gui\store.py:104  def read_evidence(self) -> list[EvidenceRecord]:

pattern: manifest
* app\gui\planner.py:348  # Also emit a tiny manifest for debugging (harmless)
* app\gui\planner.py:355  (od / "emit_manifest.json").write_text(json.dumps(m, indent=2, sort_keys=True), encoding="utf-8")
* app\gui\planner.py:383  - keeps emit_manifest.json (JSON) but includes contract_id so the *.json sweep passes
* app\gui\planner.py:417  manifest = _ensure_contract_id(
* app\gui\planner.py:420  "note": "phase5a test emitter manifest",
* app\gui\planner.py:422  fallback="emit_manifest/1.0",
* app\gui\planner.py:424  (od / "emit_manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")

pattern: sha256
* app\gui\main.py:10  - RUN_HANDOFF (machine-readable inert handoff with sha256)
* app\gui\main.py:319  hint = QLabel("Append-only evidence stream. RUN_HANDOFF is inert and sha256-stamped.")
* app\gui\planner.py:18  from app.validation.canonical import canonical_json, sha256_hex
* app\gui\planner.py:24  from app.validation.schema_validation import validate_payload, canonical_sha256_for_payload
* app\gui\planner.py:71  payload_sha256: str
* app\gui\planner.py:88  def _sha256_hex(text: str) -> str:
* app\gui\planner.py:89  return hashlib.sha256(text.encode("utf-8")).hexdigest()
* app\gui\planner.py:257  sha = sha256_hex(canonical_json(payload_no_sha))
* app\gui\planner.py:269  payload_sha256=sha,
* app\gui\planner.py:272  # Validate final handoff payload (includes payload_sha256)
* app\gui\planner.py:274  # Phase 2E: always compute canonical payload_sha256 before validation
* app\gui\planner.py:275  payload["payload_sha256"] = canonical_sha256_for_payload(payload)
* app\gui\planner.py:277  handoff.payload_sha256 = payload["payload_sha256"]  # keep record consistent
* app\util\canonical_json.py:19  def canonical_sha256_for_payload(payload: Dict[str, Any]) -> str:
* app\util\canonical_json.py:21  Canonical SHA256 over payload-without-sha.
* app\util\canonical_json.py:24  p.pop("payload_sha256", None)
* app\util\canonical_json.py:26  return hashlib.sha256(b).hexdigest()
* app\validation\canonical.py:20  def sha256_hex(text: str) -> str:
* app\validation\canonical.py:21  return hashlib.sha256(text.encode("utf-8")).hexdigest()
* app\validation\canonical.py:24  def compute_payload_sha256(payload_no_sha: Dict[str, Any]) -> str:
* app\validation\canonical.py:25  """Compute payload_sha256 over the payload WITHOUT payload_sha256 field."""
* app\validation\canonical.py:26  if "payload_sha256" in payload_no_sha:
* app\validation\canonical.py:27  raise ValueError("compute_payload_sha256 expects payload without 'payload_sha256'")
* app\validation\canonical.py:28  return sha256_hex(canonical_json(payload_no_sha))
* app\validation\canonical.py:31  def verify_payload_sha256(payload_with_sha: Dict[str, Any]) -> bool:
* app\validation\canonical.py:32  """Verify payload_sha256 matches canonical hash of payload minus payload_sha256."""
* app\validation\canonical.py:33  if "payload_sha256" not in payload_with_sha:
* app\validation\canonical.py:35  got = payload_with_sha.get("payload_sha256")
* app\validation\canonical.py:39  p.pop("payload_sha256", None)
* app\validation\canonical.py:40  want = compute_payload_sha256(p)
* app\validation\schema_validation.py:49  def _sha256_hex(b: bytes) -> str:
* app\validation\schema_validation.py:50  return hashlib.sha256(b).hexdigest()
* app\validation\schema_validation.py:56  payload_sha256 field itself.
* app\validation\schema_validation.py:59  env.pop("payload_sha256", None)
* app\validation\schema_validation.py:63  def canonical_sha256_for_payload(payload: Dict[str, Any]) -> str:
* app\validation\schema_validation.py:65  return _sha256_hex(_canonical_json_bytes(env, trailing_newline=True))
* app\validation\schema_validation.py:68  def compute_payload_sha256(payload: Dict[str, Any]) -> str:
* app\validation\schema_validation.py:71  returns canonical sha256 over the envelope (excluding payload_sha256).
* app\validation\schema_validation.py:73  return canonical_sha256_for_payload(payload)
* app\validation\schema_validation.py:81  variants.append(_sha256_hex(_canonical_json_bytes(env, trailing_newline=True)))

## CLI entrypoints

pattern: main(
* app\gui\planner.py:358  def main(argv=None) -> int:
* app\gui\planner.py:428  # Tests call: planner.main(["--out", <dir>]) (preferred), else planner.main() fallback.
* app\gui\planner.py:435  def main(argv=None):  # noqa: F811
* app\gui\planner.py:446  return _phase5a_orig_main(argv)
* app\gui\planner.py:448  return _phase5a_orig_main()
* app\main.py:1030  def main() -> int:
* app\main.py:1038  raise SystemExit(main())

pattern: cli
* app\core\types\messages.py:42  id: str = Field(..., description="Client-generated id (uuid recommended).")
* app\engine\providers\ollama.py:66  with httpx.Client(timeout=self.config.timeout_sec) as client:
* app\engine\providers\ollama.py:67  r = client.get(url)
* app\engine\providers\ollama.py:104  with httpx.Client(timeout=self.config.timeout_sec) as client:
* app\engine\providers\ollama.py:105  r = client.post(url, json=payload)
* app\engine\engine.py:54  with httpx.Client(timeout=self.config.timeout_seconds) as client:
* app\engine\engine.py:55  r = client.get(url)
* app\engine\engine.py:77  with httpx.Client(timeout=self.config.timeout_seconds) as client:
* app\engine\engine.py:78  r = client.post(url, json=payload)
* app\gui\main.py:155  self.btn_add.clicked.connect(self._on_add_task)
* app\gui\main.py:157  self.btn_done.clicked.connect(self._on_mark_done)
* app\gui\main.py:159  self.btn_plan.clicked.connect(self._on_generate_plan)
* app\gui\main.py:161  self.btn_refresh.clicked.connect(self.reload)
* app\gui\main.py:328  self.btn_apply_tpl.clicked.connect(self._on_apply_template)
* app\gui\main.py:341  self.btn_approve.clicked.connect(self._on_approve_selected_plan)
* app\gui\main.py:351  self.btn_clone.clicked.connect(self._on_clone_selected_plan)
* app\gui\main.py:363  self.btn_handoff.clicked.connect(self._on_handoff_selected_plan)
* app\gui\main.py:377  self.btn_save_note.clicked.connect(self._on_save_note)
* app\gui\main.py:379  self.btn_save_gate.clicked.connect(self._on_save_gate)
* app\gui\main.py:381  self.btn_refresh.clicked.connect(self.reload)
* app\gui\main.py:589  self.btn_taskq.clicked.connect(lambda: self._show("taskq"))
* app\gui\main.py:590  self.btn_evidence.clicked.connect(lambda: self._show("evidence"))
* app\gui\planner.py:360  Minimal CLI surface for tests:
* app\main.py:236  self.btn_copy.clicked.connect(self._copy_diff)
* app\main.py:260  QApplication.clipboard().setText(self.diff_view.toPlainText())
* app\main.py:261  QMessageBox.information(self, "Copied", "Diff copied to clipboard.")
* app\main.py:479  self.tree.doubleClicked.connect(self._tree_open)
* app\main.py:485  self.chat_send.clicked.connect(self._chat_send)
* app\main.py:556  if msg.clickedButton() == btn_verify:
* app\main.py:576  if msg.clickedButton() == btn_save:
* app\main.py:771  if msg.clickedButton() == btn_save:
* app\main.py:774  elif msg.clickedButton() == btn_discard:
* app\main.py:1018  if msg.clickedButton() == btn_save:
* app\main.py:1022  elif msg.clickedButton() == btn_discard:

