# SEGEL Test Validity Audit: AT-001 through AT-045 (Phase A)

**Authoritative Standards**: PRD v2.0 Section 27.2 (Table 50), Appendix E (Error Codes), TAS, MDB.  
**Target Suite**: `tests/adversarial/test_at_NNN.py`  
**Execution Date**: 2026-11-05  
**Audit Purpose**: Rigorous, suspect-every-test audit to determine whether each test actually exercises the intended production controls, asserts the stable PRD error code, verifies state immutability, or passes for vacuous / wrong reasons.

---

## 1. Summary of Test Validity Verdicts

| Total P0 Scenarios | Sound | Vacuous | Wrong-Reason / Broad-Except | Mislabelled / Helper-Only | API-Invented |
|:---:|:---:|:---:|:---:|:---:|:---:|
| **43** | **23** | **10** | **4** | **5** | **1** |

### Verdict Categories
- **Sound**: Correctly exercises the production code path, asserts stable PRD error codes, and verifies fail-closed state immutability.
- **Vacuous**: Does not exercise the target production control; tautological assertions or asserts on local test variables without executing target logic.
- **Wrong-Reason / Broad-Except**: Catches an unrelated earlier error, uses `pytest.raises(Exception)` without asserting error codes, or passes due to an incidental mechanism.
- **Mislabelled / Helper-Only**: Exercises a low-level helper function in isolation rather than the required end-to-end verifier / receiver path, or tests a stub.
- **API-Invented**: Asserts attributes invented on test mocks or return types rather than verifying ledger, snapshot, or receiver state artefacts.

---

## 2. Exhaustive Audit Table: AT-001 through AT-045

| AT ID | PRD 27.2 Expected Behaviour | What Test Really Exercises (Call Path, File:Line) | Assertions Made | Verdict | Evidence & Defect Notes |
|:---|:---|:---|:---|:---:|:---|
| **AT-001** | Invalid signature on any envelope $\rightarrow$ Ineligible with `SIG_INVALID`. No state change. | `Receiver.verify_and_deploy` $\rightarrow$ `verify_passport` $\rightarrow$ `verify_envelope` (`passport.py:182`) | `verification.eligibility == INELIGIBLE`, `manifest.status == INVALID`, `error_code == SIG_INVALID`, `receipt is None`, `_assert_state_unchanged` | **Sound** | Tampered base64 signature fails Ed25519 verification. Fail-closed state and error code strictly asserted. |
| **AT-002** | Manifest or bundle modified by 1 byte $\rightarrow$ Verification fails; signature check fails or `STAGE_DIGEST_MISMATCH`; deployment aborted; state unchanged. | 1. `verify_passport` (`passport.py:170`)<br>2. `Receiver.verify_and_deploy` $\rightarrow$ `BaselineAdapter.stage` (`baseline.py:155`) | 1. `INELIGIBLE`, `manifest.status == INVALID`<br>2. `receipt.overall_result == "error"`, `_assert_state_unchanged` | **Sound** | 1. Modifying manifest payload triggers DSSE verification failure.<br>2. Modifying bundle triggers digest mismatch in staging, writes error receipt, state untouched. |
| **AT-003** | Each stamp missing in turn $\rightarrow$ Ineligible. Missing stamp named. State unchanged. | `Receiver.verify_and_deploy` $\rightarrow$ `verify_passport` (`passport.py:113-138`) | `INELIGIBLE`, missing stamp in `eligibility_reasons`, `receipt is None`, `_assert_state_unchanged` | **Sound** | Systematically removes `origin`, `inspect`, `approve`, `record`. Verifier flags missing stamp and halts. |
| **AT-004** | Approval replayed on another sequence or release $\rightarrow$ Subject mismatch. Approve invalid. State unchanged. | `Receiver.verify_and_deploy` $\rightarrow$ `verify_passport` $\rightarrow$ `_check_binding` (`passport.py:480`) | `INELIGIBLE`, `approve.status == INVALID`, `error_code == SUBJECT_MISMATCH`, `receipt is None`, `_assert_state_unchanged` | **Sound** | Sequence 1 approval transplanted into sequence 2. Binding block mismatch raises `SubjectMismatchError`. |
| **AT-005** | Signature from a key not authorised as approver $\rightarrow$ Not counted. Threshold fails. | `verify_envelope` $\rightarrow$ `verify_threshold` (`dsse.py:320`) directly on test helper | `pytest.raises(ThresholdNotMetError)` | **Mislabelled / Helper-Only** | Exercises `verify_threshold` helper directly. Does not execute `verify_passport` or `Receiver.verify_and_deploy`, and does not check receiver state. |
| **AT-006** | Duplicate signatures from one key $\rightarrow$ Counted once. Threshold fails. | `verify_envelope` $\rightarrow$ `verify_threshold` (`dsse.py:320`) directly on test helper | `pytest.raises(ThresholdNotMetError)` | **Mislabelled / Helper-Only** | Exercises helper directly. Duplicate signer from same key ID is deduplicated by set comprehension, but receiver pipeline is bypassed. |
| **AT-007** | Threshold or group minimum not met $\rightarrow$ Approve invalid. | `build_candidate_passport` $\rightarrow$ `verify_passport` $\rightarrow$ `_check_group_minimums` (`passport.py:509`) | `approve.status == INVALID`, `error_code == THRESHOLD_NOT_MET`, "group" in reasons | **Sound** | Two group-0 signers presented when policy mandates 1 from group-0 and 1 from group-1. Verifier flags quorum failure. |
| **AT-008** | Author key used as an approver $\rightarrow$ Excluded from the count. | `verify_envelope` $\rightarrow$ `verify_threshold` (`dsse.py:335`) with `excluded_key_ids` | `pytest.raises(ThresholdNotMetError)` | **Mislabelled / Helper-Only** | Exercises helper directly. Author key exclusion works, but does not exercise end-to-end through `verify_passport`. |
| **AT-009** | Receiver epoch lower than min_epoch in STRICT mode $\rightarrow$ Fail closed with `EPOCH_STALE`. | `Receiver.verify_and_deploy` $\rightarrow$ `verify_passport` $\rightarrow$ `check_min_epoch` (`trust.py:230`) | `INELIGIBLE`, `EPOCH_STALE` in reasons, `receipt is None`, `_assert_state_unchanged` | **Sound** | Receiver at epoch 1 rejecting passport requiring min_epoch 2. Strictly fails closed. |
| **AT-010** | Revoked key, evidence recorded at or after `revoked_at_index` $\rightarrow$ Rejected; earlier valid. | `TrustContext.is_key_revoked_at_index` and `get_keys_for_role` (`trust.py:83, 131`) | `is_key_revoked_at_index(..., 10) is True`, `is_key_revoked_at_index(..., 9) is False`, `any(k.key_id == revoked for k in active_keys_at_9)` | **Sound (Exposes Real Bug)** | FAILS: `TrustContext.__init__` adds key to `_revoked_key_ids` unconditionally. `get_keys_for_role` strips key globally, rejecting valid evidence prior to `revoked_at_index`. |
| **AT-011 (P1)** | Emergency revocation package applied offline $\rightarrow$ Epoch advances, key rejected, quarantine. | *None* | *None* | **Untested (P1)** | Excluded from P0 suite. Emergency revocation package format and quarantine state are unimplemented. |
| **AT-012** | Release sequence not higher than highest accepted $\rightarrow$ Rejected (`anti-rollback`). State unchanged. | `Receiver.verify_and_deploy` $\rightarrow$ `verify_passport` (`passport.py:551`) | `INELIGIBLE`, "anti-rollback" in reasons, `receipt is None`, `_assert_state_unchanged` | **Sound** | Anti-rollback check strictly rejects candidate with sequence $\le$ state highest sequence. |
| **AT-013** | Lower root, policy, or snapshot version or epoch $\rightarrow$ Rejected with `POLICY_DOWNGRADE`. State unchanged. | `Receiver.verify_and_deploy` $\rightarrow$ `verify_passport` (`passport.py:302`) | `INELIGIBLE`, `inspect.status == INVALID`, `error_code == POLICY_DOWNGRADE`, `receipt is None`, `_assert_state_unchanged` | **Sound** | Inspect attestation with `policy_version=0` rejected against floor 1. |
| **AT-014** | Corrupted Receiver state $\rightarrow$ Recovery mode; no deployment; floors not reset. | `Receiver.verify_and_deploy` (`receiver.py:131`) with `recovery_mode=True` | `pytest.raises(StateCorruptError)`, `code == STATE_CORRUPT`, `_assert_state_unchanged` | **Sound** | When receiver is in recovery mode, deployment aborts immediately with `STATE_CORRUPT`. |
| **AT-015** | Release adds a capability that policy forbids $\rightarrow$ Inspect REJECT; no approval possible. | `inspect_release` (`inspector.py:84`) $\rightarrow$ `verify_passport` (`passport.py:289`) | `inspection.verdict == "REJECT"`, `res.inspect.status == INVALID`, `res.eligibility == INELIGIBLE` | **Sound** | `run_as_root: true` detected by capability extractor, sets REJECT, passport verifier invalidates stamp. |
| **AT-016** | AI cites a non-existent capability ID $\rightarrow$ Finding discarded and flagged; verdict unaffected. | Local test script variables (`test_at_NNN.py:853-865`) | `len(sanitized_findings) == 0` | **Vacuous** | Does NOT call `inspect_release`. Filters a local python list in the test body. AI pipeline is stubbed. |
| **AT-017** | AI says "safe" while deterministic verdict is REJECT $\rightarrow$ Verdict stays REJECT. | Local test script variables (`test_at_NNN.py:871-889`) | `final_verdict == "REJECT"`, all findings reject | **Vacuous** | Pure tautology: defines `deterministic_verdict = "REJECT"`, sets `final_verdict = deterministic_verdict`, asserts it is "REJECT". Inspector is not invoked. |
| **AT-018** | AI timeout or malformed output $\rightarrow$ `ai_status: failed`, visible banner, deterministic verdict stands. | `inspect_release` (`inspector.py:248`) with `ai_enabled=True` | `inspection.ai_status == "failed"`, `inspection.verdict == "PASS"` | **Mislabelled** | In `inspector.py`, `ai_enabled=True` unconditionally raises `NotImplementedError`, caught by fallback. Tests stub exception handling, not real AI timeout. |
| **AT-019** | Injection in purpose text and configuration values (20 cases) $\rightarrow$ Deterministic verdict unchanged. | `inspect_release` (`inspector.py:75`) across 20 prompt injection strings | `inspection.verdict in ("PASS", "WARN")` | **Sound (Validator-Level)** | Per decision D2, tests deterministic parser/extractor against injection attacks. Injections cannot alter capability extraction. |
| **AT-020** | Non-extending or conflicting checkpoint (fork) $\rightarrow$ Rejected and logged; receiver keeps last good. | `Witness.cosign_checkpoint` (`witness.py:77`) | `pytest.raises(CheckpointForkError)`, `code == CHECKPOINT_FORK`, witness last root unchanged | **Sound** | Conflicting checkpoint root at identical size detected; witness raises `CheckpointForkError` and locks state. |
| **AT-021** | Inclusion proof for a different leaf or tree $\rightarrow$ Rejected with `PROOF_INVALID`. | `verify_inclusion_from_hash` (`hashing.py:183`) | `pytest.raises(ProofInvalidError)`, `code == PROOF_INVALID` | **Sound** | Merkle verification detects leaf/root hash mismatch and aborts with `PROOF_INVALID`. |
| **AT-022** | Checkpoint signed by unknown or revoked ledger key $\rightarrow$ Rejected. | Local set membership check (`test_at_NNN.py:1003-1004`) | `rogue_ledger_key.key_id not in {k.key_id for k in ledger_keys}` | **Vacuous** | Checkpoint signature verification in `passport.py:375` is commented out/bypassed. Test avoids calling `verify_passport` and only checks a python set! |
| **AT-023** | Witness cosignature missing where policy requires one $\rightarrow$ Record invalid. | `verify_passport` (`passport.py:393`) with empty `witness_cosignatures` | `record.status == INVALID`, `error_code == PROOF_INVALID`, "witness" in reasons | **Sound** | Policy requires 1 witness cosignature; empty list triggers `ProofInvalidError`. (Note: signature crypto itself is not verified). |
| **AT-024** | Canary unhealthy or criteria unmet $\rightarrow$ Hold placed (`HOLD_RECORDED`). Promotion blocked. Canary rollback. | `evaluate_promotion` (`controller.py:40`) | `result.promoted is False`, `assert getattr(result, "hold_placed", False) is True` | **API-Invented** | Asserts `result.hold_placed`, which is an invented mock attribute. `controller.py` does not record holds in ledger or snapshot. |
| **AT-025** | Forged or invalid receipt, or receipt from a non-canary unit $\rightarrow$ Not counted. | Local set check (`test_at_NNN.py:1064`) | `rogue_unit_key.key_id not in {k.key_id for k in receiver_keys}` | **Vacuous** | Checks key ID in local trust root set. Does NOT assemble a general passport or call `verify_passport` with the rogue receipt. |
| **AT-026** | Disk exhaustion at preflight or during staging $\rightarrow$ Refuse or abort; backup intact; no partial apply. | Manifest construction (`test_at_NNN.py:1076`) | `assert manifest.subjects[0].size > 0` | **Vacuous** | Only asserts size > 0! Does not simulate disk exhaustion, mock `shutil.disk_usage`, or invoke `adapter.preflight`. |
| **AT-027** | Path traversal, absolute path, or symlink escape $\rightarrow$ Rejected before extraction. | `build_release_package` $\rightarrow$ `_validate_package_paths` (`builder.py:252`) | `pytest.raises(PackageMalformedError)`, `code == PACKAGE_MALFORMED` | **Sound** | Tests `../../etc/shadow`, `/etc/passwd`, `C:\Windows`, null bytes. All rejected with `PACKAGE_MALFORMED`. |
| **AT-028** | Decompression bomb $\rightarrow$ Size and ratio limits abort with clear error. | `build_release_package` (`builder.py:98`) with 201 MiB payload | `pytest.raises(PackageMalformedError)`, `code == PACKAGE_MALFORMED` | **Sound (Partial)** | Tests `MAX_TOTAL_SIZE` limit (> 200 MiB). Compression ratio limits are not implemented. |
| **AT-029** | Two concurrent deployments on one target $\rightarrow$ Second refused (`RESOURCE_LOCKED`); first unaffected. | `Receiver.verify_and_deploy` across 2 parallel threads (`test_at_NNN.py:1143`) | `assert refused` | **Sound (Exposes Real Bug)** | FAILS: Receiver has no mutual exclusion lock. Both threads run simultaneously, corrupting deploy state rather than refusing the second. |
| **AT-030** | Power loss mid-deployment at every journal step $\rightarrow$ Journal completes or rolls back. | `BaselineAdapter.rollback` (`baseline.py:292`) | `assert initial_file == "initial: true"` | **Wrong-Reason / Mislabelled** | Passes because `BaselineAdapter` restores static `.backup` dir. There is NO crash-safe step journal, NO `SEGEL_CRASH_AT` hook, and NO replay recovery. |
| **AT-031** | Non-canonical base64 or encoding malleability $\rightarrow$ Rejected. | `import_public_key` (`ed25519.py:145`) | `pytest.raises((SignatureError, ValueError))` | **Sound** | Checks strict base64 roundtrip `b64encode(b64decode(s)) == s`. Malleable trailing bits rejected. |
| **AT-032** | Unknown schema version or critical field $\rightarrow$ Rejected. | `Manifest.model_validate_json` (`test_at_NNN.py:1202`) | `pytest.raises(Exception)` | **Wrong-Reason / Broad-Except** | Uses broad `pytest.raises(Exception)` on Pydantic parsing. Does not test verifier handling or assert PRD `SCHEMA_UNKNOWN`. |
| **AT-033** | Candidate passport presented to non-canary unit $\rightarrow$ Rejected: not authorised for this unit. | `Receiver.verify_and_deploy` $\rightarrow$ `verify_passport` (`passport.py:592`) | `INELIGIBLE`, "not in canary role" in reasons, `receipt is None`, `_assert_state_unchanged` | **Sound** | Unit with role "general" attempting candidate passport is rejected with `INELIGIBLE`. |
| **AT-034** | General passport without promotion record $\rightarrow$ Rejected. | `verify_passport` (`passport.py:423`) with valid canary receipts but `promotion_proof=None` | `INELIGIBLE`, "promotion" in reasons | **Sound** | General passport lacking Merkle proof for `release_promoted` is rejected with `StampMissingError`. |
| **AT-035** | Evidence from release A used in release B (every stamp) $\rightarrow$ Binding mismatch. Rejected. | `Receiver.verify_and_deploy` $\rightarrow$ `verify_passport` $\rightarrow$ `_check_binding` (`passport.py:480`) | `INELIGIBLE`, `origin.status == INVALID`, `error_code == SUBJECT_MISMATCH`, `receipt is None`, `_assert_state_unchanged` | **Sound** | Transplanting Origin stamp from release A into release B rejected due to manifest SHA-256 binding mismatch. |
| **AT-036** | QR frames lost, duplicated, or reordered $\rightarrow$ Recovered, or fails cleanly; partial never signed. | `json.loads(truncated)` (`test_at_NNN.py:1312`) | `pytest.raises(Exception)` | **Vacuous / Broad-Except** | Truncates a string and calls Python's `json.loads`. Fountain codes and multi-frame QR reassembly do not exist. |
| **AT-037** | Tampered request summary shown by Desk $\rightarrow$ Approver device shows only derived info. | `create_approval_payload` (`test_at_NNN.py:1338`) | `assert decoded_payload["subject"][0]["name"] == "release/AT-037@1"` | **Vacuous** | Asserts that `req.payload_to_sign` contains subject string. Does not test approver device derivation or summary tampering. |
| **AT-038** | Receiver wall clock moved forward or backward $\rightarrow$ No security decision changes. | `verify_passport` called twice (`test_at_NNN.py:1349-1353`) | `res1.eligibility == res2.eligibility`, `res1.all_stamps_valid == res2.all_stamps_valid` | **Vacuous** | Calls `verify_passport` twice with identical static arguments. Never manipulates system clock or mocks time. |
| **AT-039** | Adapter missing from pinned allowlist or with different digest $\rightarrow$ Refused. | `Receiver.verify_and_deploy` (`test_at_NNN.py:1385`) with pinned digest mismatch | `assert verification.eligibility == INELIGIBLE or receipt is None`, `_assert_state_unchanged` | **Sound (Exposes Real Bug)** | FAILS: `Receiver.verify_and_deploy` never checks `trust_ctx.policy.allowed_adapters`. Rogue/mismatched adapter executes without validation. |
| **AT-040** | Inspect policy version below configured minimum $\rightarrow$ Rejected with `POLICY_DOWNGRADE`. | `verify_passport` (`passport.py:301`) with `policy.min_inspect_policy_version = 5` | `inspect.status == INVALID`, `error_code == POLICY_DOWNGRADE`, "POLICY_DOWNGRADE" in reasons | **Sound** | Attestation declaring inspect policy 1 rejected against policy floor 5. |
| **AT-041** | Release scope excludes this unit $\rightarrow$ Ineligible. Deployment not attempted. | `verify_passport` (`passport.py:604`) with `general_scope=["unit-1", "unit-2"]` for `unit-3` | `INELIGIBLE`, "scope" in reasons | **Sound** | General passport targeting unit outside `manifest.general_scope` rejected with `INELIGIBLE`. |
| **AT-042** | Tampered Trust Update Package $\rightarrow$ Rejected; nothing replaced. | `TrustRoot.model_validate_json` (`test_at_NNN.py:1463`) | `pytest.raises(Exception)` | **Vacuous / Broad-Except** | Tests Pydantic parsing error on invalid JSON string with broad `Exception`. Trust Update Package mechanism is completely missing. |
| **AT-043 (P1)** | Two builders produce different outputs $\rightarrow$ Origin invalid. Approval blocked. | *None* | *None* | **Untested (P1)** | Excluded from P0 suite. Dual independent builders is P1. |
| **AT-044** | Health probe outside fixed vocabulary $\rightarrow$ Refused. | Local variable set check (`test_at_NNN.py:1472`) | `probe_name not in valid_vocabulary` | **Vacuous** | Checks `probe_name not in {"file_exists", "config_valid"}` on local test variables. Adapter probe validator is not invoked. |
| **AT-045** | Hold present in held snapshot $\rightarrow$ Receiver refuses with `HELD`. State unchanged. | `Receiver.verify_and_deploy` $\rightarrow$ `verify_passport` (`passport.py:546`) | `verification.eligibility == HELD`, "HELD" in reasons, `receipt is None`, `_assert_state_unchanged` | **Sound** | Release listed under `snapshot.held_releases` immediately halts receiver verification with classification `HELD`. |

---

## 3. Mandatory Deep Dives

### 1. AT-016, AT-018, AT-019 (AI Pipeline Realities)
* **AT-016**: Vacuous. Does not invoke `inspector.py`. In `inspector.py:225`, AI advisory findings are completely unimplemented. The test filters a local list in test memory.
* **AT-018**: Mislabelled. In `inspector.py:246`, calling with `ai_enabled=True` immediately hits:
  ```python
  if ai_enabled:
      raise NotImplementedError("AI advisory requires external model configuration")
  ```
  The test catches this and verifies `ai_status: "failed"` while deterministic verdict is preserved. It tests exception fallback, but there is no AI pipeline.
* **AT-019**: Sound at validator level. Per Decision D2, AI remains deterministic-only. Testing that 20 prompt injection strings do not crash YAML parsing or fool regex capability matchers is valid for the deterministic engine.

### 2. AT-022 (Checkpoint Signature Verification Bypass)
* **Audit Finding**: In `src/segel_core/verification/passport.py:375`, the checkpoint signature verification code is **commented out or missing**:
  `verify_passport` verifies the Merkle inclusion proof against `proof.checkpoint_root_hash`, but **never cryptographically verifies the ledger signature** on `passport.signed_checkpoint`!
* **Test Validity**: Vacuous. `test_at_022` avoids calling `verify_passport` or `Receiver.verify_and_deploy` because doing so would pass despite the rogue ledger signature! Instead, it asserts `rogue_ledger_key.key_id not in {k.key_id for k in ledger_keys}` on a local set.

### 3. AT-026 (Disk Exhaustion vs Size Limit)
* **Audit Finding**: Vacuous. `test_at_026` creates a Manifest with size 1GB and asserts `assert manifest.subjects[0].size > 0`. It never calls `adapter.preflight`, never checks available disk space, and never simulates `ENOSPC`.

### 4. AT-030 (Crash-Safe Step Journal)
* **Audit Finding**: Wrong-reason / Mislabelled. `test_at_030` passes because `BaselineAdapter.rollback()` simply copies files from a static `.backup` folder. There is no step-by-step WAL journal, no intent record, and no replay on crash recovery. A crash between staging and apply leaves uncommitted files without recovery.

### 5. AT-036 (QR Fountain Code Recovery)
* **Audit Finding**: Vacuous. `test_at_036` truncates a single JSON string and asserts `pytest.raises(Exception)` on `json.loads`. There is no multi-frame fountain code (UR/Luby transform) or frame reassembly in `src/approver/`.

### 6. AT-037 (Approver Review Derivation)
* **Audit Finding**: Vacuous. Asserts `json.loads(req.payload_to_sign)["subject"][0]["name"] == ...`. Does not test that the approver device refuses unverified summary text sent by the Release Desk.

### 7. AT-042 (Trust Update Package)
* **Audit Finding**: Vacuous. The test only calls Pydantic `TrustRoot.model_validate_json(b'{"new_root": "invalid"}')` inside `pytest.raises(Exception)`. There is no Trust Update Package parser, negative tests for root chain downgrade, or positive installation tests.

### 8. AT-024 (Invented Attribute)
* **Audit Finding**: API-invented. Asserts `assert getattr(result, "hold_placed", False) is True`. `PromotionResult` has no `hold_placed` field in PRD schemas. The real PRD requirement is recording a `HOLD_RECORDED` event in the transparency ledger and updating `snapshot.held_releases`.

---

## 4. PRD 27.2 Rows Lacking Real Test Coverage
The following PRD Table 50 attack scenarios currently have **NO real test coverage** against the actual production components:
1. **AT-011 (P1)**: Emergency revocation package applied offline.
2. **AT-016 (P0)**: AI cites non-existent capability ID (untested in inspector).
3. **AT-017 (P0)**: AI says safe while deterministic is REJECT (untested in inspector).
4. **AT-022 (P0)**: Checkpoint signed by rogue ledger key (bypassed in verifier).
5. **AT-024 (P0)**: Canary failure automatic ledger hold placement (untested against ledger/snapshot).
6. **AT-025 (P0)**: Forged / non-canary receipt rejected by passport verifier.
7. **AT-026 (P0)**: Disk exhaustion during staging / preflight.
8. **AT-030 (P0)**: Step-by-step deployment crash recovery at every step.
9. **AT-036 (P0)**: Multi-frame QR lost/reordered recovery.
10. **AT-037 (P0)**: Approver device derivation from canonical PAE vs unverified desk summary.
11. **AT-038 (P0)**: Receiver wall-clock forward/backward skew.
12. **AT-042 (P0)**: Trust Update Package positive installation and negative verification.
13. **AT-043 (P1)**: Dual independent builders produce differing outputs.
14. **AT-044 (P0)**: Health probe outside fixed vocabulary refused by adapter.
