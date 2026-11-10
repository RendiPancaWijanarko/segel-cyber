# SEGEL ID & Error Code Reconciliation

**Authoritative Standards**: PRD v2.0 Section 27.2 (Table 50), Appendix B/C/D (Requirements Taxonomy), Appendix E (Error Codes), TAS, MDB.  
**Branch**: `hardening/p2b-p5`  
**Purpose**: Map all test IDs to genuine PRD requirement IDs, eliminate invented identifiers, reconcile error codes against PRD Appendix E, and catalog all uncovered P0 requirements.

---

## 1. Test ID to PRD Requirement & Error Code Mapping

The table below reconciles all 43 tests in [`tests/adversarial/test_at_NNN.py`](../tests/adversarial/test_at_NNN.py) against official PRD requirements and PRD Appendix E error codes:

| Test Function | Target AT ID | PRD Req IDs | PRD Expected Error Code | Current Implementation Behaviour | Reconciliation Action Needed |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `test_at_001_invalid_signature_on_envelope` | AT-001 | SEC-007, FR-070 | `SIG_INVALID` | Raises `SignatureError(SIG_INVALID)`; `origin.status == INVALID` | **Aligned**: asserts stable `ErrorCode.SIG_INVALID`. |
| `test_at_002_manifest_or_bundle_modified_by_one_byte` | AT-002 | FR-004, SEC-008 | `DIGEST_MISMATCH` | Baseline adapter raises `PackageMalformedError` during staging; passport verification fails subject binding | **Aligned**: asserts digest mismatch in eligibility reasons. |
| `test_at_003_each_stamp_missing_in_turn` | AT-003 | FR-036, FR-070 | `STAMP_MISSING` | `PassportVerificationResult` marks missing stamp `StampStatus.MISSING` with error `STAMP_MISSING` | **Aligned**: asserts `ErrorCode.STAMP_MISSING`. |
| `test_at_004_approval_replayed_on_another_sequence` | AT-004 | SEC-008, SEC-010 | `SUBJECT_MISMATCH` | `_check_binding()` raises `SubjectMismatchError` with `sequence` mismatch details | **Aligned**: isolated check asserts `ErrorCode.SUBJECT_MISMATCH` & `"sequence"`. |
| `test_at_005_signature_from_a_key_not_authorised` | AT-005 | FR-033, SEC-007 | `THRESHOLD_NOT_MET` | Helper `verify_threshold()` returns False; currently bypasses `verify_passport()` | **Rewrite required**: invoke full `verify_passport()` with candidate passport. |
| `test_at_006_duplicate_signatures_from_one_key` | AT-006 | FR-071, SEC-007 | `THRESHOLD_NOT_MET` | Helper `verify_threshold()` deduplicates key IDs; currently bypasses `verify_passport()` | **Rewrite required**: invoke full `verify_passport()`. |
| `test_at_007_threshold_or_group_minimum_not_met` | AT-007 | FR-033 | `THRESHOLD_NOT_MET` | `_check_group_minimums()` sets `approve.status = INVALID`, `approve.error_code = THRESHOLD_NOT_MET` | **Aligned**: asserts `ErrorCode.THRESHOLD_NOT_MET`. |
| `test_at_008_author_key_used_as_an_approver` | AT-008 | FR-034, SEC-001 | `THRESHOLD_NOT_MET` | Asserts `author_key` excluded from count in TrustContext; does not assert passport rejection | **Rewrite required**: assert passport rejection with `THRESHOLD_NOT_MET`. |
| `test_at_009_receiver_epoch_lower_than_min_epoch_in_strict_mode` | AT-009 | FR-062, SEC-011 | `EPOCH_STALE` | `check_min_epoch()` sets `res.eligibility = INELIGIBLE`, reasons contain `EPOCH_STALE` | **Aligned**: asserts `ErrorCode.EPOCH_STALE`. |
| `test_at_010_revoked_key_index_ordering` | AT-010 | FR-063, SEC-012 | `KEY_REVOKED` | Currently FAILS: `TrustContext` unconditionally marks key revoked without checking ledger index | **Fix required**: implement `is_key_revoked_at_index` in `verify_passport()`. |
| `test_at_011_emergency_revocation_package_offline` | AT-011 | FR-066, SEC-036 | `PROOF_INVALID` / `SIG_INVALID` | Currently tests string mutation on synthetic checkpoint dictionary | **Rewrite required**: test real emergency package verification. |
| `test_at_012_release_sequence_not_higher_than_highest_accepted` | AT-012 | SEC-010, SEC-011 | `SEQUENCE_REPLAY` | `_determine_eligibility()` detects sequence replay; sets `SEQUENCE_REPLAY` | **Aligned**: asserts `ErrorCode.SEQUENCE_REPLAY`. |
| `test_at_013_lower_policy_version_or_epoch_rejected` | AT-013 | FR-061, SEC-011 | `POLICY_DOWNGRADE` | `verify_passport()` rejects policy downgrade with `POLICY_DOWNGRADE` | **Aligned**: asserts `ErrorCode.POLICY_DOWNGRADE`. |
| `test_at_014_corrupted_receiver_state_enters_recovery_mode` | AT-014 | FR-075, SEC-019 | `STATE_CORRUPT` | `Receiver.verify_and_deploy()` detects `recovery_mode=True` and raises `StateCorruptError` | **Aligned**: asserts `ErrorCode.STATE_CORRUPT`. |
| `test_at_015_release_adds_forbidden_capability` | AT-015 | FR-021, SEC-013 | `INELIGIBLE` (verdict `REJECT`) | Policy engine assigns `verdict = REJECT`; `verify_passport()` marks passport `INELIGIBLE` | **Aligned**: asserts `EligibilityClass.INELIGIBLE` & inspect verdict `REJECT`. |
| `test_at_016_ai_cites_non_existent_capability_id` | AT-016 | FR-022, SEC-013 | N/A (Validator-level per D2) | Tests validator function `validate_ai_findings()` discarding fabricated capability ID | **Classified limitation (D2)**: relabelled validator-level. |
| `test_at_017_ai_says_safe_while_deterministic_verdict_reject` | AT-017 | FR-023, SEC-013 | N/A (Validator-level per D2) | Tests escalation-only logic in `sign_inspect()` | **Classified limitation (D2)**: relabelled validator-level. |
| `test_at_018_ai_timeout_or_malformed_output_fallback` | AT-018 | FR-022, SEC-013 | `AI_FAILED` (advisory) | Sets `ai_status = "failed"`, deterministic verdict stands | **Classified limitation (D2)**: relabelled validator-level. |
| `test_at_019_prompt_injection_in_purpose_and_config` | AT-019 | FR-024, SEC-013 | N/A (Validator-level per D2) | Tests prompt sanitization against 20 attack strings | **Classified limitation (D2)**: relabelled validator-level. |
| `test_at_020_non_extending_or_conflicting_checkpoint_fork` | AT-020 | FR-053 | `CHECKPOINT_FORK` | `Witness.cosign_checkpoint()` detects root fork on same size and raises `CheckpointForkError` | **Aligned**: asserts `ErrorCode.CHECKPOINT_FORK`. |
| `test_at_021_inclusion_proof_for_different_leaf_or_tree` | AT-021 | FR-050 | `PROOF_INVALID` | `verify_inclusion_from_hash()` raises `ProofInvalidError` | **Aligned**: asserts `ErrorCode.PROOF_INVALID`. |
| `test_at_022_checkpoint_signed_by_unknown_or_revoked_ledger_key` | AT-022 | FR-050, SEC-007 | `KEY_NOT_AUTHORISED` | Passes currently because checkpoint signature verification was commented out | **Fix required**: uncomment checkpoint signature verification in `passport.py`. |
| `test_at_023_witness_cosignature_missing_where_policy_requires` | AT-023 | FR-053 | `THRESHOLD_NOT_MET` | `verify_passport()` checks `actual_witnesses < required_witnesses` and marks record `INVALID` | **Aligned**: asserts `THRESHOLD_NOT_MET`. |
| `test_at_024_canary_unhealthy_or_criteria_unmet` | AT-024 | FR-044 | `HELD` | Currently FAILS: Promotion blocked, but hold is not placed in ledger | **Fix required**: implement automatic ledger hold placement. |
| `test_at_025_forged_or_invalid_receipt_not_counted` | AT-025 | FR-041, FR-042 | `THRESHOLD_NOT_MET` | Currently vacuous (`assert True`) | **Rewrite required**: verify corrupted receipt rejection in promotion controller. |
| `test_at_026_disk_exhaustion_at_preflight` | AT-026 | SEC-014 | `RESOURCE_LIMIT` | Currently vacuous (`assert True`) | **Rewrite required**: simulate disk space exhaustion during preflight. |
| `test_at_027_path_traversal_absolute_path_symlink_escape` | AT-027 | FR-002, SEC-014 | `PACKAGE_MALFORMED` | `build_release_package()` and baseline adapter reject path escapes with `PackageMalformedError` | **Aligned**: asserts `ErrorCode.PACKAGE_MALFORMED`. |
| `test_at_028_decompression_bomb` | AT-028 | FR-002, SEC-014 | `PACKAGE_MALFORMED` | `build_release_package()` checks `total_size > MAX_TOTAL_SIZE` and raises `PackageMalformedError` | **Aligned**: asserts `ErrorCode.PACKAGE_MALFORMED`. |
| `test_at_029_two_concurrent_deployments_on_one_target` | AT-029 | FR-086 | `RESOURCE_LIMIT` / `STATE_CORRUPT` | Currently FAILS: Race condition, concurrent invocations race without locking | **Fix required**: implement cross-process file locking on `deploy_root`. |
| `test_at_030_power_loss_mid_deployment_journal_recovery` | AT-030 | FR-083 | Journal recovery | Currently in-memory adapter test; real crash injection written in `test_c5_at030_crash.py` | **Rewrite required**: migrate real crash injection from `test_c5` to `test_at_030`. |
| `test_at_031_non_canonical_base64_or_encoding_malleability` | AT-031 | SEC-007, AT-031 | `SIG_INVALID` | `import_public_key()` detects dirty padding bits and raises `SignatureError` | **Aligned**: asserts `ErrorCode.SIG_INVALID`. |
| `test_at_032_unknown_schema_version_or_critical_field` | AT-032 | SEC-006 | `SCHEMA_UNKNOWN` | Pydantic validation rejects unknown version with `ValidationError` | **Improvement required**: test Receiver-level `SCHEMA_UNKNOWN` rejection. |
| `test_at_033_candidate_passport_presented_to_non_canary_unit` | AT-033 | FR-040, SEC-008 | `SCOPE_MISMATCH` | `verify_passport()` marks `INELIGIBLE` ("Unit canary-1 is not in canary role") | **Aligned**: asserts `INELIGIBLE` and role check reason. |
| `test_at_034_general_passport_without_promotion_record` | AT-034 | FR-043 | `STAMP_MISSING` | `verify_passport()` raises `StampMissingError("record_promotion_proof missing")` | **Aligned**: asserts `STAMP_MISSING` & `INELIGIBLE`. |
| `test_at_035_evidence_from_release_a_used_in_release_b` | AT-035 | SEC-008 | `SUBJECT_MISMATCH` | `_check_binding()` raises `SubjectMismatchError("Binding manifest_sha256 mismatch")` | **Aligned**: asserts `ErrorCode.SUBJECT_MISMATCH`. |
| `test_at_036_qr_frames_lost_duplicated_or_reordered` | AT-036 | FR-030 | `SCHEMA_UNKNOWN` / `PACKAGE_MALFORMED` | Tests `json.loads` on truncated string | **Rewrite required**: test QR frame assembler. |
| `test_at_037_tampered_request_summary_shown_by_desk` | AT-037 | FR-031 | `SUBJECT_MISMATCH` | Asserts string difference between request summary and payload | **Rewrite required**: test CLI decoding canonical payload. |
| `test_at_038_receiver_clock_skew_does_not_affect_security` | AT-038 | SEC-009 | N/A (Verification invariant) | Tests `verify_passport` without wall-clock dependencies | **Aligned**: asserts monotonic floor ordering. |
| `test_at_039_adapter_missing_from_pinned_allowlist` | AT-039 | FR-081, SEC-015 | `ADAPTER_NOT_ALLOWED` | Currently FAILS: `Receiver.verify_and_deploy()` does not check `policy.allowed_adapters` | **Fix required**: implement adapter policy verification in Receiver. |
| `test_at_040_inspect_policy_version_below_configured_minimum` | AT-040 | FR-061 | `POLICY_DOWNGRADE` | `verify_passport()` rejects inspect policy version below minimum with `POLICY_DOWNGRADE` | **Aligned**: asserts `ErrorCode.POLICY_DOWNGRADE`. |
| `test_at_041_release_scope_excludes_this_unit` | AT-041 | SEC-008 | `SCOPE_MISMATCH` | `verify_passport()` marks `INELIGIBLE` ("Release scope excludes unit") | **Aligned**: asserts `SCOPE_MISMATCH` & `INELIGIBLE`. |
| `test_at_042_tampered_trust_update_package` | AT-042 | FR-066 | `SIG_INVALID` | Currently tests dictionary modification without real TUP | **Fix required**: use real TUP verification from `test_c4`. |
| `test_at_043_dual_builder_output_mismatch` | AT-043 | SEC-002 | `DIGEST_MISMATCH` | P1 requirement; asserts approved envelope collection | **Classified limitation**: Dual builder is P1. |
| `test_at_044_health_probe_outside_fixed_vocabulary` | AT-044 | FR-082 | `SCHEMA_UNKNOWN` | `HealthResult` Pydantic model rejects invalid probe string | **Aligned**: asserts schema rejection. |
| `test_at_045_hold_present_in_held_snapshot_refused_with_held` | AT-045 | FR-073 | `HELD` | `verify_passport()` checks `trust_ctx.is_release_held()` and assigns `EligibilityClass.HELD` | **Aligned**: asserts `ErrorCode.HELD`. |

---

## 2. Uncovered PRD P0 Requirements

Every official P0 requirement from PRD Appendix B, C, and D that currently lacks a sound automated test:

### 2.1. Uncovered Functional Requirements (P0 FR)

| PRD ID | Requirement Summary | Why Currently Uncovered | Action in Phase F |
| :--- | :--- | :--- | :--- |
| **FR-003** | Manifest signed by local author signer; Release Desk holds no private keys | Release Desk currently instantiates `author_key` and signs internally | Fix SEC-004 key separation (C1) and rewrite author workflow |
| **FR-022** | AI advisory findings schema validation and status reporting | AI pipeline is stubbed raising `NotImplementedError` | Relabelled limitation under Decision D2 |
| **FR-024** | Untrusted purpose and config text prompt injection corpus (20 cases) | Test corpus not written in test suite | Relabelled limitation under Decision D2 |
| **FR-026** | Approver MUST acknowledge every WARN finding; acknowledgement digest signed | `acknowledgement_digest` hardcoded to empty; no check | Implement WARN acknowledgement verification in `approver.py` |
| **FR-031** | Approver device decodes canonical payload; refuses unrenderable types | CLI reads outer unverified dictionary fields | Update `approver/cli.py` to decode canonical payload |
| **FR-042** | Promotion criteria observation window cycles evaluated | `observation_window_cycles` in schema is never checked | Add cycle check to `promotion/controller.py` |
| **FR-044** | Canary failure automatically places hold in ledger | Receiver rolls back locally, but does not append hold to ledger | Implement automatic ledger hold appending in `promotion/controller.py` |
| **FR-051** | Ledger verifies submitted evidence itself before appending release | `TransparencyLedger.append()` blindly appends without verifying DSSE | Implement autonomous evidence verification in `ledger.py` (C2) |
| **FR-052** | Ledger event types MUST include `hold_lifted` and `receipt_ingested` | `VALID_EVENT_TYPES` missing `hold_lifted` and `receipt_ingested` | Add missing event types to `VALID_EVENT_TYPES` in `ledger.py` |
| **FR-054** | Receiver persists highest checkpoint and rejects non-extending | `verify_passport()` does not compare checkpoint size against state | Add checkpoint size anti-rollback check to `passport.py` |
| **FR-060** | Receiver trust root fingerprint shown for manual confirmation | CLI lacks root fingerprint display command | Add `segel-receiver trust-info` command |
| **FR-063** | Key revocation ordered by ledger index, not self-asserted time | `verify_passport()` does not check `is_key_revoked_at_index` | Enforce index-ordered revocation in `passport.py` / `trust.py` |
| **FR-066** | Trust Update Package verified before use (anti-rollback, root quorum) | No TUP schema or updater existed | Implement `TrustUpdatePackage` and `apply_trust_update` (C4) |
| **FR-074** | Receiver verify-only mode that changes nothing | Receiver CLI lacks `--verify-only` flag | Add `--verify-only` flag to `receiver/cli.py` |
| **FR-075** | Corrupted state triggers recovery mode in Receiver CLI | CLI creates clean state rather than reading disk state | Update `receiver/cli.py` to load and validate persistent state |
| **FR-081** | Deployment adapter digest pinned by policy; unpinned refused | `policy.allowed_adapters` is never checked | Implement adapter allowlist & digest check in `receiver.py` |
| **FR-082** | Declarative health probe vocabulary enforced | Custom probes not rejected by policy | Enforce probe allowlist validation |
| **FR-083** | Crash-safe deployment journaling survives power loss | Deployment state is purely in-memory | Implement persistent atomic write-ahead journal (C5) |
| **FR-086** | Mutual exclusion: only one deployment per target at a time | No file lock on `deploy_root`; concurrent runs race | Implement cross-process file locking on `deploy_root` |
| **FR-091** | Approver review screen derives findings from canonical payload | Outer unverified wrapper parsed | Update `approver/cli.py` parsing |
| **FR-092** | Receiver screen provides next recommended action on failure | Explains error but omits next action guidance | Add recommended actions to `PassportVerificationResult.summary()` |
| **FR-095** | Export self-contained evidence bundle for audit | Export functionality missing | Add `segel-receiver export-evidence` command |

---

### 2.2. Uncovered Security Requirements (P0 SEC)

| PRD ID | Requirement Summary | Why Currently Uncovered | Action in Phase F |
| :--- | :--- | :--- | :--- |
| **SEC-002** | Builder key MUST NOT be Author or Approver key | `passport.py` checks Author key, but does not check Approver keys | Add `builder_key not in approver_keys` check to `passport.py` |
| **SEC-003** | Inspector Signer key isolated from AI runtime | AI and inspector key reside in same web server memory | Move inspector signer to standalone service (Decision D1/D2) |
| **SEC-004** | Release Desk holds no private keys | Release Desk `DemoState` generates and stores 11 private keys | Move approver keys to separate signer process (D1 / C1) |
| **SEC-005** | Ledger Signer and Witness keys held by different processes | Both keys held in same web server memory in demo harness | Document demo harness limitation; separate in production |
| **SEC-012** | Key revocation ordered by ledger index | `is_key_revoked_at_index()` is dead code | Enforce index-ordered revocation in `passport.py` |
| **SEC-014** | Package parsers enforce decompression ratio limits | Single-file and total size checked; compression ratio not checked | Add decompression ratio check to `builder.py` |
| **SEC-015** | Adapters pinned by digest in policy | `policy.allowed_adapters` never validated | Add adapter digest verification in `receiver.py` |
| **SEC-016** | PIN/passphrase attempt throttling for encrypted private keys | Scrypt encryption exists; attempt throttling not implemented | Add attempt counter and backoff to key loader |
| **SEC-017** | Local hash-chained audit log records security-relevant events | No audit logging module exists in Receiver | Implement `AuditLogger` with SHA-256 hash chaining (C3) |
| **SEC-035** | Trust root transition dual-signed by previous and new roots | Root rotation mechanism missing | Implement in TUP verification (C4) |
| **SEC-036** | Revocation processing works at P0 | Index-ordered revocation not hooked up | Connect index-ordered revocation in `trust.py` |

---

### 2.3. Uncovered Attack Tests (P0 AT)

| PRD AT ID | Scenario & Expected Error | Defect / Reason for Absence | Action in Phase F |
| :--- | :--- | :--- | :--- |
| **AT-005** | Unauthorised approver key $\rightarrow$ `THRESHOLD_NOT_MET` | Current test calls helper, not full receiver pipeline | Rewrite as sound end-to-end receiver test |
| **AT-006** | Duplicate signatures from one key $\rightarrow$ Counted once | Current test calls helper, not full receiver pipeline | Rewrite as sound end-to-end receiver test |
| **AT-008** | Author key as approver $\rightarrow$ Excluded; threshold fails | Asserts TrustContext, not receiver passport rejection | Rewrite to assert `PassportVerificationResult.approve.status == INVALID` |
| **AT-010** | Revocation index ordering $\rightarrow$ `KEY_REVOKED` | Implementation defect: `verify_passport` ignores entry index | Implement index ordering fix in `trust.py` |
| **AT-011** | Emergency revocation package $\rightarrow$ `PROOF_INVALID` | Test mocks dictionary mutation | Rewrite using real signed emergency package |
| **AT-022** | Checkpoint signed by rogue ledger key $\rightarrow$ `KEY_NOT_AUTHORISED` | Checkpoint signature check commented out in `passport.py` | Uncomment and fix checkpoint signature verification |
| **AT-024** | Canary unhealthy $\rightarrow$ `HELD`, promotion blocked | Automatic ledger hold event is not implemented | Implement ledger hold placement on canary failure |
| **AT-025** | Non-canary receipt $\rightarrow$ `THRESHOLD_NOT_MET` | Test is vacuous `assert True` | Rewrite with forged receipt presented to promotion controller |
| **AT-026** | Disk exhaustion $\rightarrow$ `RESOURCE_LIMIT` | Test is vacuous `assert True` | Implement disk space preflight probe and test |
| **AT-029** | Two concurrent deployments $\rightarrow$ Second refused | Mutual exclusion lock missing on `deploy_root` | Implement cross-process file lock on `deploy_root` |
| **AT-030** | Power loss mid-deployment $\rightarrow$ Journal recovery | In-memory mock; real test in `test_c5_at030_crash.py` | Implement persistent journal and promote `test_c5` to `AT-030` |
| **AT-032** | Unknown schema version $\rightarrow$ `SCHEMA_UNKNOWN` | Currently asserts Pydantic validation only | Assert Receiver rejection with `SCHEMA_UNKNOWN` |
| **AT-036** | QR frame loss / reordering $\rightarrow$ Recovery / clean fail | Single JSON frame; multi-frame assembler missing | Document limitation / implement QR frame assembler |
| **AT-037** | Tampered request summary shown by Desk | CLI displays unverified outer JSON dictionary | Update `approver/cli.py` to render canonical payload |
| **AT-039** | Adapter missing from pinned allowlist $\rightarrow$ `ADAPTER_NOT_ALLOWED` | `receiver.py` never checks `allowed_adapters` | Implement adapter allowlist check in Receiver |
| **AT-042** | Tampered Trust Update Package $\rightarrow$ `SIG_INVALID` | TUP not implemented; test mocked | Promote `test_c4` to sound `AT-042` |
| **AT-043** | Dual independent builders differ $\rightarrow$ Approval blocked | P1 requirement (MVP implements single builder) | Document as P1 limitation in `docs/limitations.md` |
| **AT-044** | Health probe outside fixed vocabulary $\rightarrow$ Refused | Only model schema tested | Enforce probe allowlist in Receiver adapter |
