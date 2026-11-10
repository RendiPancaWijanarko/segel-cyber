# SEGEL Comprehensive Security Review (Phase E)

**Authoritative Standards**: PRD v2.0, TAS (Architecture Spec), MDB (MVP Blueprint), PRD Appendix E (Error Codes).  
**Branch**: `hardening/p2b-p5`  
**Scope**: In-depth read-only security review of all source code under `src/`.  
**Review Status**: Complete — zero application code modified under `src/`.

---

## 1. Executive Summary

A comprehensive line-by-line security audit was performed across all modules under `src/` (`segel_core`, `builder`, `inspector`, `approver`, `ledger`, `witness`, `receiver`, `promotion`, `release_desk`).

While SEGEL's core cryptographic primitives (`dsse.py`, `ed25519.py`, `hashing.py`) strictly adhere to RFC 8032 and in-toto DSSE specifications with strict canonical base64 and deduplication, the operational implementation exhibits **critical trust boundary violations, incomplete fail-closed paths, and concurrency hazards** that must be resolved prior to controlled pilot deployment.

### Top 5 Highest-Risk Security Findings
1. **CRITICAL — Private Key Colocation in Release Desk Web Process (SEC-004)**: `DemoState` generates and stores private keys for all roles in web server memory, destroying the architectural security boundary.
2. **CRITICAL — Ledger Checkpoint Signature Verification Bypassed in Receiver (AT-022, FR-050)**: `verify_passport()` comments out checkpoint signature verification, allowing unverified root hashes to be accepted.
3. **HIGH — Ledger Appends Unverified Evidence (FR-051, SEC-016)**: `TransparencyLedger.append()` inserts arbitrary payloads into the Merkle tree without validating DSSE envelopes or policy thresholds.
4. **HIGH — Lack of Deployment Concurrency Mutual Exclusion (FR-086, AT-029)**: `Receiver.verify_and_deploy()` lacks a process-level file lock on `deploy_root`, allowing concurrent deployments to race and corrupt state.
5. **HIGH — Missing Persistent Crash-Safe Deployment Journal (FR-083, AT-030)**: Deployment lifecycle progress is tracked purely in memory; power interruption mid-apply leaves corrupted configurations without rollback.

---

## 2. In-Depth Security Findings by Category

### Category 1: Trust Boundary Violations (Components Trusting Unverified Input)

#### SEC-FINDING-01: Release Desk Holds and Invokes Signer Private Keys
* **Severity**: **CRITICAL**
* **PRD Requirement**: `SEC-004`, `SEC-001`, `FR-003`
* **File & Line**: [`src/release_desk/app.py:121-185`](../src/release_desk/app.py#L121)
* **Exploit Scenario**: An attacker who compromises the Release Desk web application (e.g. via web vulnerability or SSRF) can extract all private keys (`author_key`, `builder_key`, `inspector_key`, `approver_keys[0..2]`, `ledger_key`, `witness_key`) directly from heap memory, allowing total forgery of Release Passports and ledger checkpoints.
* **Proposed Fix**: Move approver keys out of `ReleaseDesk` into an independent external signer process or service (Decision D1). Release Desk must only transport unsigned payloads and receive externally signed envelopes.

#### SEC-FINDING-02: Ledger Checkpoint Signature Verification Commented Out in Passport Verifier
* **Severity**: **CRITICAL**
* **PRD Requirement**: `AT-022`, `FR-050`, `SEC-007`
* **File & Line**: [`src/segel_core/verification/passport.py:374-378`](../src/segel_core/verification/passport.py#L374)
* **Exploit Scenario**: Lines 376–377 state `# (Simplified: trust the proof structure and verify Merkle inclusion)`. An attacker with distribution channel access can generate a rogue checkpoint with an arbitrary Merkle root and forge an inclusion proof. Because the checkpoint signature under the authorized ledger key is never verified, the Receiver accepts the record stamp as valid.
* **Proposed Fix**: Verify `signed_checkpoint.ledger_signature` against authorized active ledger keys loaded from `trust_ctx.get_keys_for_role("ledger")` using RFC 8032 Ed25519 verification before verifying inclusion proofs.

#### SEC-FINDING-03: Autonomous Ledger Evidence Verification Missing
* **Severity**: **HIGH**
* **PRD Requirement**: `FR-051`, `SEC-016`
* **File & Line**: [`src/ledger/ledger.py:162-202`](../src/ledger/ledger.py#L162)
* **Exploit Scenario**: An attacker submits a malformed or unauthorized `candidate_recorded` or `release_promoted` event directly to the ledger service. Because `TransparencyLedger.append()` only checks `event_type in VALID_EVENT_TYPES`, it commits the invalid event into the Merkle tree and issues signed checkpoints for invalid releases.
* **Proposed Fix**: Implement an autonomous evidence verification layer in `TransparencyLedger` that parses candidate DSSE envelopes, validates all signatures against trust root policy, checks approver thresholds, and verifies canary receipts before appending to the tree.

#### SEC-FINDING-04: Deployment Adapter Policy Pinning Bypassed
* **Severity**: **HIGH**
* **PRD Requirement**: `FR-081`, `SEC-015`, `AT-039`
* **File & Line**: [`src/receiver/receiver.py:156-175`](../src/receiver/receiver.py#L156)
* **Exploit Scenario**: An operator or attacker configures an untrusted custom adapter or points to an unauthorized adapter ID. `Receiver.verify_and_deploy()` executes the adapter without validating `adapter.adapter_id` or adapter digest against `trust_ctx.policy.allowed_adapters`.
* **Proposed Fix**: Validate `adapter.adapter_id` against `trust_ctx.policy.allowed_adapters` during receiver initialization and before invoking deployment steps; raise `AdapterNotAllowedError(ADAPTER_NOT_ALLOWED)` if unapproved.

#### SEC-FINDING-05: Approver Review Screen Parses Outer Unverified JSON
* **Severity**: **MEDIUM**
* **PRD Requirement**: `FR-031`, `AT-037`
* **File & Line**: [`src/approver/cli.py:42-70`](../src/approver/cli.py#L42)
* **Exploit Scenario**: Release Desk constructs an approval request where outer JSON summary fields say "harmless config change", while inner `payload_b64` contains a malicious binary update. An approver reviewing the request via CLI sees the outer summary and approves the payload.
* **Proposed Fix**: Update `approver/cli.py` to decode and deserialize `payload_b64` canonical JSON directly, deriving all display fields exclusively from the cryptographically verified inner statement.

---

### Category 2: Incomplete Fail-Closed Paths

#### SEC-FINDING-06: Global Key Revocation Breaks Historical Release Verification
* **Severity**: **HIGH**
* **PRD Requirement**: `FR-063`, `SEC-012`, `AT-010`
* **File & Line**: [`src/segel_core/verification/trust.py:77-135`](../src/segel_core/verification/trust.py#L77)
* **Exploit Scenario**: When an approver or author key is revoked after a security incident, `TrustContext` adds the key ID to `_revoked_key_ids` globally. When offline units verify or audit prior legitimate releases recorded *before* the revocation event, verification fails retroactively, causing denial of service.
* **Proposed Fix**: Hook up `is_key_revoked_at_index(key_id, ledger_index)`: only reject signatures if the evidence was recorded in the ledger at or after `revoked_at_index`.

#### SEC-FINDING-07: Receiver Missing On-Disk Recovery Mode Enforcement in CLI
* **Severity**: **MEDIUM**
* **PRD Requirement**: `FR-075`, `AT-014`
* **File & Line**: [`src/receiver/cli.py:27-50`](../src/receiver/cli.py#L27)
* **Exploit Scenario**: If a receiver's on-disk state file is corrupted, the core `Receiver` correctly blocks deployment if `recovery_mode=True`. However, `segel-receiver` CLI creates a default in-memory `ReceiverState` on every run rather than loading persisted state, bypassing the recovery mode lock.
* **Proposed Fix**: Ensure `receiver/cli.py` loads `state.json` from the state directory and strictly halts with `StateCorruptError` if corrupted or flagged in recovery mode.

#### SEC-FINDING-08: Checkpoint Size Floor Anti-Rollback Check Missing
* **Severity**: **MEDIUM**
* **PRD Requirement**: `FR-054`
* **File & Line**: [`src/segel_core/verification/passport.py:370-400`](../src/segel_core/verification/passport.py#L370)
* **Exploit Scenario**: An adversary presents an older valid checkpoint with a smaller size than the receiver has already verified. Because `verify_passport()` does not assert `checkpoint.size >= receiver_state["last_checkpoint_size"]`, the receiver accepts older ledger states.
* **Proposed Fix**: Add check `if checkpoint.size < receiver_state.get("last_checkpoint_size", 0): raise CheckpointForkError`.

#### SEC-FINDING-09: Automatic Ledger Hold Placement Missing on Canary Failure
* **Severity**: **MEDIUM**
* **PRD Requirement**: `FR-044`, `AT-024`
* **File & Line**: [`src/promotion/controller.py:80-98`](../src/promotion/controller.py#L80)
* **Exploit Scenario**: A canary unit reports unhealthy probes during testing. While promotion is blocked locally, no `hold` event is dispatched to the transparency ledger. Other nodes or controllers remain unaware of the failure and may attempt promotions.
* **Proposed Fix**: Implement automatic ledger hold generation when `evaluate_promotion()` detects canary health failures.

---

### Category 3: Path Traversal, Symlink, Archive-Bomb Edge Cases

#### SEC-FINDING-10: Decompression Bomb Ratio Limits Not Checked
* **Severity**: **MEDIUM**
* **PRD Requirement**: `SEC-014`, `AT-028`, `FR-002`
* **File & Line**: [`src/builder/builder.py:95-115`](../src/builder/builder.py#L95)
* **Exploit Scenario**: An attacker submits a highly compressible archive (e.g. 100 MB of zeros compressed into 100 KB) that fits within `MAX_FILE_SIZE` and `MAX_TOTAL_SIZE`. While total limits are enforced during builder packaging, decompression ratio limits are not verified during package ingestion.
* **Proposed Fix**: Enforce max compression ratio check (ratio <= 100:1) during package validation.

#### SEC-FINDING-11: Staging Directory Debris Left After Abrupt Crash
* **Severity**: **MEDIUM**
* **PRD Requirement**: `FR-083`, `AT-030`
* **File & Line**: [`src/receiver/adapter/baseline.py:165-185`](../src/receiver/adapter/baseline.py#L165)
* **Exploit Scenario**: If process termination or power loss occurs while writing `.segel_stage`, partially written files remain on disk. If a subsequent deployment runs without cleanup, orphaned files can contaminate the target directory.
* **Proposed Fix**: Ensure `preflight()` and adapter startup unconditionally purge `.segel_stage` and clean temporary staging trees.

---

### Category 4: Concurrency Hazards on Ledger SQLite and Receiver Filesystem

#### SEC-FINDING-12: Receiver Lacks Cross-Process Mutual Exclusion on Deploy Root
* **Severity**: **HIGH**
* **PRD Requirement**: `FR-086`, `AT-029`
* **File & Line**: [`src/receiver/receiver.py:117-175`](../src/receiver/receiver.py#L117)
* **Exploit Scenario**: Two deployment commands execute concurrently against the same target directory. Both pass preflight and snapshot, then simultaneously overwrite `backup` and `deploy_root`, leaving corrupt, half-deployed configurations and broken rollbacks.
* **Proposed Fix**: Acquire an OS-level cross-process non-blocking file lock on `<deploy_root>/.deploy.lock` at the start of `verify_and_deploy()`; refuse concurrent deployments with `ResourceLimitError(RESOURCE_LIMIT)`.

#### SEC-FINDING-13: Ledger In-Memory Merkle Tree Desynchronization Across Processes
* **Severity**: **HIGH**
* **PRD Requirement**: `SEC-030`, `FR-050`
* **File & Line**: [`src/ledger/ledger.py:93-102`](../src/ledger/ledger.py#L93)
* **Exploit Scenario**: `TransparencyLedger` synchronizes SQLite writes via WAL mode and a `threading.RLock()`. However, `self._tree` is an in-memory `MerkleTree`. If multiple worker processes or CLI commands write to the same SQLite database file, their in-memory Merkle trees diverge, producing conflicting root hashes and corrupted checkpoints.
* **Proposed Fix**: Reload or verify tree consistency on append or enforce single-writer architecture for the ledger database.

#### SEC-FINDING-14: In-Memory Deployment State Prevents Power-Loss Crash Recovery
* **Severity**: **HIGH**
* **PRD Requirement**: `FR-083`, `AT-030`
* **File & Line**: [`src/receiver/adapter/baseline.py:76-88`](../src/receiver/adapter/baseline.py#L76)
* **Exploit Scenario**: When power fails during step 6 (`apply`), the `DeploymentState` object in RAM is destroyed. On system reboot, the receiver has no persistent journal to indicate an interrupted deployment, leaving corrupted files in place without rolling back to `backup`.
* **Proposed Fix**: Implement an on-disk atomic write-ahead deployment journal (`deploy_journal.json`) tracking each lifecycle step; on receiver startup, inspect the journal and execute rollback if interrupted.

---

### Category 5: In-toto / DSSE / RFC 8032 Compliance

#### SEC-FINDING-15: Local Hash-Chained Audit Log Missing on Receiver
* **Severity**: **HIGH**
* **PRD Requirement**: `SEC-017`
* **File & Line**: *Entirely missing from `src/receiver/`*
* **Exploit Scenario**: Security-relevant events (verification failures, rejected releases, epoch downgrades, recovery events) are printed to console or discarded. No cryptographically chained forensic log exists to detect offline log tampering or audit past deployment decisions.
* **Proposed Fix**: Implement `AuditLogger` writing append-only, SHA-256 hash-chained JSON-lines (`audit.jsonl`) on the Receiver (codified in Red Test `test_c3_sec017`).

---

## 3. Review Conclusion & Gate 2 Check

All 15 findings are documented with concrete exploit scenarios and architectural fixes.  
No code under `src/` was modified during Phase E.

```powershell
PS segel-cyber> git diff --stat -- src/
# Output: (empty)
```
