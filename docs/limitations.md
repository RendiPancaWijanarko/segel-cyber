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
- **Verification & Failure Semantics** (see Section 4 for operational limitations):
  - Verified by crash-recovery tests (`test_at030_crash_recovery`): simulated abrupt process termination mid-deployment leaves backups intact and enables journaled recovery to clean or restored state within test scenario parameters (subject to host filesystem flush semantics).
  - All deployment and verification events are recorded in local SHA-256 hash-chained JSON-lines (`audit.jsonl`) for tamper evidence.

---

## 4. Priority P1 Requirements Deferred
1. **Dual Independent Builders (FR-011, AT-043)**:
   - MVP uses a single builder provenancing the bundle with RFC 8032 Ed25519 signatures.
   - Dual-builder bit-for-bit reproducibility is deferred to post-MVP P1.
2. **Fountain Codes & Multi-Frame QR Streaming (AT-036)**:
   - MVP approver CLI generates compact QR payloads. Multi-frame fountain code transmission is deferred to P1 mobile companion clients.
3. **Emergency Revocation Push (AT-011)**:
   - Air-gapped receivers operate offline; revocation packages are physically delivered via Trust Update Packages (TUP).

---

## 5. AI Purpose Classifier and Evaluation Corpus Limitations (AI-4b)
1. **Single-Purpose Policy**: Corpus labels follow a strict single-purpose policy: a declared change class is expected to touch only its own canonical capability kind. For example, a log-destination change that also opens an outbound firewall rule is labelled inconsistent, although bundling such changes may be legitimate in operational practice.
2. **Common Assistant Authorship**: The evaluation corpus, the B1 keyword taxonomy lists (`docs/b1_keywords.md`), and the inspection prompt templates were authored by the same assistant. While developed independently to generic criteria, this introduces potential shared stylistic bias.
3. **Small Sample Size (Indicative Results)**: The development split contains only 7 silent inconsistent items and 3 hard items missed by B1 (`DEV-14`, `DEV-17`, `DEV-18`). Evaluation results on the dev split are indicative and provide sample evidence rather than broad statistical significance.
4. **Deterministic-Subset Coverage**: All deterministic-subset inconsistent items are caught by default-severity rules (`reject` on `privilege_granted`, `warn` on `logging_disabled` or `broad_change`) regardless of the stated release purpose.

---

## 6. Headless Browser Screenshot Limitation (AI-7)
- **Context**: Decision D18 and task specification requested saving a visual screenshot of the Release Detail page (`docs/evaluation/ai_panel.png`) if a browser tool was available.
- **Limitation**: No headless browser automation framework (such as Playwright, Puppeteer, or Selenium) is installed within the sandboxed Python execution environment, and external package installation is prohibited per repository security rules.
- **Verification Alternative**: The HTML rendering, AI advisory panel structure, status banners (ok, failed, skipped), variable escaping, absence of confidence percentages, and footer disclaimer are verified by automated unit tests in `tests/unit/test_ai_7_ack_and_manifest.py`.

