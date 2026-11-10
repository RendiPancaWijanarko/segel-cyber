# SEGEL Consolidated Limitations & Architectural Boundaries

This document records the architectural boundaries, MVP limitations, and operational trade-offs of the SEGEL platform per PRD v2.0, TAS, and decisions D1 through D22.

---

## 1. Cryptographic & Security Boundaries

### 1.1 Offline Revocation Awareness & Bounded Epoch Lifetimes
- **Reference**: PRD v2.0 §16, TAS §8.9
- **Architectural Reality**: Receivers operate in an air-gapped or offline posture with zero real-time outbound or inbound network access. Offline receivers cannot query real-time CRLs or OCSP endpoints.
- **Enforced Boundary**: Revocations and security holds take effect only when a new, signed Trust Update Package (TUP) advancing the trust root version and epoch is delivered to the unit.
- **Operational Requirement**: Deployments must configure bounded epoch lifetimes. If a receiver's epoch becomes stale (`receiver_epoch < min_epoch`), the receiver fails closed (`EPOCH_STALE`) until updated.

### 1.2 Single Builder in MVP (Dual-Builder Reproducibility Deferred)
- **Reference**: PRD v2.0 §6, FR-011, AT-043
- **MVP Implementation**: Releases are packaged and provenanced by a single builder entity signing the `application/vnd.segel.origin+json` attestation with an RFC 8032 Ed25519 key.
- **Security Boundary**: A compromise of the single builder's private key could allow an attacker to sign provenance for an altered bundle. However, author manifest signatures and deterministic inspector capability checks independently detect non-author files or prohibited capabilities.
- **Roadmap (P1)**: Dual independent builders producing independent provenance attestations with bit-for-bit reproducible build verification.

### 1.3 Cryptographic Tamper Evidence vs. Absolute Storage Immutability
- **Reference**: PRD v2.0 §8, TAS §8.6
- **Architectural Reality**: The Transparency Ledger utilizes SQLite with Write-Ahead Logging (`PRAGMA journal_mode=WAL`) and database triggers prohibiting `UPDATE` and `DELETE` operations on log tables. However, SQLite operates at the application level; a host administrator or process with direct disk access could alter raw bytes on disk.
- **Enforced Boundary**: Immutability is enforced cryptographically, not via OS-level storage claims:
  1. RFC 6962 SHA-256 Merkle tree root hashes.
  2. Ledger Signer digital signatures over checkpoints (`size`, `root_hash`).
  3. External Witness cosignatures over Merkle consistency proofs.
  Any modification of historical entries on disk invalidates subsequent checkpoint signatures and witness consistency proofs (`CHECKPOINT_FORK`).

### 1.4 Single-Process Demonstration Harness Key Separation
- **Reference**: PRD v2.0 §15, SEC-004, Decision D1
- **MVP Implementation**: In the competition demonstration harness (`scripts/demo.py`, `src/release_desk/app.py`), approver keys are encapsulated within `StandaloneApproverSigner`, while remaining role keys reside in memory within the demo state bundle for ease of evaluation.
- **Operational Requirement**: In production, every role (Author, Builder, Inspector, Ledger, Witness, Approver, Receiver) MUST run on separate physical hosts, isolated containers, or dedicated Hardware Security Modules (HSMs), communicating exclusively via signed DSSE envelopes.

### 1.5 Trust Root Transition Chains
- **Reference**: PRD v2.0 SEC-035, DEV-10
- **MVP Implementation**: Verifiers validate that `root_version` increases monotonically. Dual-threshold M-of-N transition signature chains between successive trust roots are not evaluated in MVP.
- **Operational Requirement**: Trust roots are provisioned statically out-of-band in the prototype.

---

## 2. Adapter & Deployment Lifecycles

### 2.1 Crash-Safe Journal & Host Filesystem Semantics
- **Reference**: PRD v2.0 FR-083, FR-086, SEC-017, Decision D3
- **Implementation**: `BaselineAdapter.recover_crash()` uses a persistent write-ahead journal (`.segel_journal.json`), automatic backup restoration, and staging debris cleanup, accompanied by SHA-256 hash-chained JSON-lines audit logs (`audit.jsonl`).
- **Limitation**: Crash safety and journal recovery depend on underlying host operating system and filesystem flush semantics (`fsync`).

### 2.2 Cross-Platform File Permission Variations (POSIX vs Windows NTFS)
- **Reference**: PRD v2.0 §10, SEC-025
- **Implementation**: Deployed files are marked read-only (`0o444`). On POSIX systems, this applies standard UNIX permissions (`-r--r--r--`). On Windows NTFS, this sets the Win32 `FILE_ATTRIBUTE_READONLY` flag.
- **Handling**: Rollback mechanisms in `BaselineAdapter` handle cross-platform file clearing by resetting `stat.S_IWRITE` prior to atomic unlinking or replacement. Windows ACL inheritance may vary based on parent directory defaults.

### 2.3 Standalone Payload Evaluation vs. Predecessor Diffing
- **Reference**: PRD v2.0 FR-014, DEV-07
- **Implementation**: `src/inspector/inspector.py` inspects files present in the current release payload standalone, without loading or diffing against prior sequence manifests.
- **Boundary**: Extracted capabilities reflect full current release contents rather than delta relative to previous version.

---

## 3. AI Advisory Subsystem Scope & Operational Boundaries

### 3.1 Advisory Role and Severity Cap
- **Reference**: Decisions D1, D7, D12, D14, PRD v2.0 §7
- **Implementation**:
  - The AI Inspector (`qwen3:4b`) provides advisory purpose classification (`source="ai"`, `severity="warn"`).
  - Findings derived from AI classification are strictly capped at severity `warn`.
  - The AI subsystem can NEVER emit a `reject` finding, can NEVER escalate an overall release verdict to `REJECT`, and can NEVER lower or suppress a deterministic `REJECT` or `WARN` finding to `PASS`.
  - The model's natural-language justification is treated as untrusted advisory commentary and is never parsed to drive automated security decisions.

### 3.2 Capability Analysis Scope
- **Implementation**: The AI Inspector compares declared textual manifest `purpose` strings against extracted capability diffs (e.g., firewall modifications, user additions, dependency bumps).
- **Boundary**: It does NOT perform binary reverse-engineering, machine-code vulnerability detection, or zero-day malware identification in compiled artifacts.

### 3.3 Key Isolation & Process Sandboxing
- **Reference**: Decisions D1, D5, D6, D14
- **Implementation**: The AI worker subprocess executes in a scrubbed environment stripped of all secret, key, token, and credential variables (`build_scrubbed_env`).
- **Boundary**: The AI model never sees private keys, never holds keys in memory, and never produces digital signatures.

### 3.4 Hardware Profile & Partial CPU Offload
- **Reference**: Decision D11, AI-8 Evaluation
- **Measurement**: On the evaluation host, local Ollama `qwen3:4b` inference executes with partial GPU/CPU offload (~66-72% GPU VRAM, ~28-34% CPU system RAM).
- **Limitation**: In environments without GPU acceleration or under constrained system memory, token generation throughput falls (measured mean throughput: 7.00 tokens/sec), increasing query latency.
- **Fail-Closed Semantics**: When inference exceeds the timeout threshold (`SEGEL_AI_TIMEOUT_S=30`), the subprocess is terminated, setting `ai_status="failed"` with `ai_error_code="TIMEOUT"`. Deterministic rules and gates remain fully active.

### 3.5 Evaluation Corpus & Methodology Limitations
- **Reference**: AI-4b, AI-7, AI-8
- **Single-Purpose Policy**: Corpus labels follow a strict single-purpose policy: a declared change class is expected to touch only its own canonical capability kind.
- **Common Assistant Authorship**: The evaluation corpus, B1 keyword taxonomy lists, and inspection prompt templates were authored with assistance from the same AI coding assistant.
- **Sample Size**: The development split contains 36 items (7 silent inconsistent items; 3 hard items missed by B1: `DEV-14`, `DEV-17`, `DEV-18`). Results are indicative of capability rather than broad statistical significance.
- **Deterministic-Subset Coverage**: All deterministic-subset inconsistent items are caught by default-severity rules (`reject` on `privilege_granted`, `warn` on `logging_disabled` or `broad_change`) regardless of the stated release purpose.

### 3.6 Headless Browser Screenshot Limitation
- **Reference**: Decision D18, AI-7
- **Limitation**: No headless browser automation framework (such as Playwright or Selenium) is installed within the sandboxed environment. Visual layout, escaping, AI panel structure, and disclaimers are validated via automated unit test assertions in `tests/unit/test_ai_7_ack_and_manifest.py`.

---

## 4. Priority P1 Features Deferred to Post-MVP

1. **Dual Independent Builders (FR-011, AT-043)**: Dual-builder bit-for-bit reproducibility deferred to P1.
2. **Fountain Codes & Multi-Frame QR Streaming (AT-036)**: Multi-frame animated QR transmission for payloads >2 KB deferred to P1 mobile companion clients.
3. **Emergency Revocation Push (AT-011)**: Air-gapped receivers operate offline; revocation packages are physically delivered via Trust Update Packages (TUP).
