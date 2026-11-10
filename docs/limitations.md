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

---

## 7. AI Scope Boundaries and Security Guarantees (AI-8)
1. **Advisory Role Only**:
   - The AI Inspector (`qwen3:4b`) provides advisory purpose classification (`source="ai"`, `severity="warn"`).
   - Findings derived from AI classification are strictly capped at severity `warn`.
   - The AI component can NEVER emit a `reject` finding, can NEVER escalate the overall release verdict to `REJECT`, and can NEVER lower or downgrade a deterministic `REJECT` or `WARN` finding to `PASS`.
   - The model's natural-language justification is treated as untrusted advisory commentary and is never parsed to drive automated security decisions.
2. **Analysis Scope**:
   - The AI Inspector compares the declared textual manifest `purpose` against extracted capability diffs (e.g., firewall modifications, user additions, dependency bumps).
   - It does NOT perform binary reverse-engineering, machine-code vulnerability detection, or zero-day malware identification in compiled artifacts.
3. **Key Isolation**:
   - The AI worker subprocess executes in a scrubbed environment stripped of all secret, key, token, and credential variables (`build_scrubbed_env`).
   - The AI model never sees private keys, never holds keys in memory, and never produces digital signatures.

---

## 8. Partial CPU Offload & Inference Hardware Profile (AI-8)
1. **Execution Split**:
   - Local Ollama `qwen3:4b` inference executes with partial GPU/CPU offload (~72% GPU VRAM, ~28% CPU system RAM on the evaluation host).
   - In environments without GPU acceleration or under constrained system resources, token generation throughput falls (measured mean throughput: 7.00 tokens/sec), increasing per-item query latency (mean 22.01s, max 289.86s).
2. **Fail-Closed Timeout Semantics**:
   - When inference exceeds the parent timeout threshold (e.g. `TEST-27` taking >50s), the subprocess is terminated.
   - The system sets `ai_status="failed"` with `ai_error_code="TIMEOUT"`.
   - The overall release inspection fails closed: deterministic findings and gates remain active, and no unauthorized pass is granted.

---

## 9. Single-Process Desk Key Bundle in Prototype (AI-8)
1. **Demo Harness Scope**:
   - In the competition prototype (`src/release_desk/app.py`, `scripts/demo.py`), while approver signing keys are encapsulated in `StandaloneApproverSigner`, other synthetic role keys (author, builder, inspector, ledger, witness, receiver) reside within the demo state bundle.
2. **Production Separation Requirement**:
   - In a production deployment, each role (Builder, Inspector, Ledger, Witness, Receiver) MUST run on separate physical hosts, isolated containers, or dedicated Hardware Security Modules (HSMs), communicating only via signed DSSE envelopes.

---

## 10. Evaluation Corpus Constraints & Decision D21 Determination (AI-8)
1. **Corpus Size**:
   - The evaluation corpus contains 60 synthetic items (24 dev, 36 test) with Baseline v1 JSON specifications.
   - Sample size $N=36$ on the test split limits statistical generalizability.
2. **Decision D21 Result**:
   - On the frozen test split, B1 union AI detected 10 out of 11 silent mismatch items with 0 false positives.
   - Baseline B1b detected 11 out of 11 silent items (at the expense of 2 false positives).
   - Because $10 \ngtr 11$, under Decision D21, the headline claim "AI adds value" is NOT permitted. The claim is strictly limited to measured empirical results.
3. **Claims Audit Policy**:
   - Prohibited marketing hype terms ("secure", "guarantee", "verified", "100%", confidence percentages) are excluded from project claims.
   - In SEGEL documentation and specifications, all security statements cite specific named tests or explicit architectural boundaries. References to "verified" in code signatures denote Ed25519 DSSE envelope cryptographic signature checks rather than an assertion of zero systemic flaws.

