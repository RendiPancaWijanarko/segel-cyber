# SEGEL MVP Limitations & Hardening Architectural Boundaries

This document records the architectural boundaries, MVP limitations, and design decisions codified during the SEGEL hardening pass per Decisions D1, D2, and D3, PRD v2.0, and TAS.

---

## 1. Decision D1: Key Separation in Demo Harness
- **PRD Reference**: `SEC-004`, `FR-003`
- **Hardening Action**:
  - Approver private keys were completely removed from the Release Desk process scope and encapsulated in `StandaloneApproverSigner` (`src/approver/service.py`).
  - Synthetic demo key generation was extracted into an isolated demo infrastructure module (`src/demo_infra/keys.py`).
  - In `src/release_desk/app.py`, approver signing is delegated exclusively via structured requests (`demo.approver_signer.sign_approval_request()`).
- **Limitation**:
  - Remaining synthetic keys (author, builder, inspector, ledger, witness, receiver) in the single-process demo harness (`scripts/demo.py`, `src/release_desk/app.py`) are stored in a private attribute (`self._demo_keys`).
  - In production deployment, all distinct roles MUST operate in separate physical processes, machines, or HSMs with their own private keys.

---

## 2. Decision D2: Deterministic AI Verification Pipeline
- **PRD Reference**: §7, §27.2 (AT-016, AT-017, AT-018, AT-019)
- **Hardening Action**:
  - SEGEL MVP implements deterministic capability extraction and policy enforcement.
  - Tests AT-016 through AT-019 are categorized as "validator-level" checks.
- **Limitation**:
  - No active external LLM / AI inference daemon is deployed in MVP.
  - All AI status fields default to `skipped` or `deterministic_only`.
  - Under no circumstances can AI advisory output downgrade a deterministic `REJECT` verdict, authorize a release, or override human approver quorums.

---

## 3. Decision D3: Crash-Safe Write-Ahead Journal & Audit Log
- **PRD Reference**: `FR-083`, `FR-086`, `SEC-017`, `AT-029`, `AT-030`
- **Hardening Action**:
  - Implemented `BaselineAdapter.recover_crash()` with persistent write-ahead journal (`.segel_journal.json`), automatic backup restoration, and staging debris cleanup.
  - Implemented `AuditLogger` writing append-only, SHA-256 hash-chained JSON-lines (`audit.jsonl`).
  - Implemented in-process threading mutual exclusion and atomic filesystem locks (`.deploy.lock`) on `deploy_root`.
- **Guarantee**:
  - Abrupt power loss or process kill mid-deployment leaves backups intact and enables zero-state-corruption recovery.
  - All deployment and verification events are cryptographically chained and tamper-evident.

---

## 4. Priority P1 Requirements Deferred
1. **Dual Independent Builders (FR-011, AT-043)**:
   - MVP uses a single builder provenancing the bundle with RFC 8032 Ed25519 signatures.
   - Dual-builder bit-for-bit reproducibility is deferred to post-MVP P1.
2. **Fountain Codes & Multi-Frame QR Streaming (AT-036)**:
   - MVP approver CLI generates compact QR payloads. Multi-frame fountain code transmission is deferred to P1 mobile companion clients.
3. **Emergency Revocation Push (AT-011)**:
   - Air-gapped receivers operate offline; revocation packages are physically delivered via Trust Update Packages (TUP).
