# SEGEL Architectural Boundaries & Known MVP Limitations

This document provides a technical account of the security boundaries, architectural trade-offs, and operational limitations of the SEGEL MVP implementation compared to the full PRD v2.0 specification.

---

## 1. Cryptographic & Security Boundaries

### LIM-001: Offline Revocation Awareness & Epoch Window
- **PRD v2.0 Reference**: §16 (Trust Management & Revocation Model)
- **Architectural Reality**: Receivers operate in an air-gapped or offline posture with zero real-time outbound or inbound network access. Consequently, an offline receiver cannot learn of out-of-band key revocations or release holds via real-time CRLs or OCSP stapling.
- **Enforced Security Guarantee**: Revocations and holds take effect only when a new, signed **Trust Update Package** (advancing the trust root version and epoch) is physically delivered to the receiver.
- **Mitigation & Operational Requirement**: Organizations must enforce bounded epoch lifetimes (e.g., 24-hour or 7-day epochs). If an offline receiver's epoch becomes stale (`receiver_epoch < required_min_epoch`), the receiver strictly fails closed (`EPOCH_STALE`) until updated.

---

### LIM-002: Single Builder in MVP (Dual Builder Reproducibility Deferred)
- **PRD v2.0 Reference**: §6 (SLSA-Aligned Provenance & Dual Builder Architecture)
- **MVP Implementation**: Releases are packaged and provenanced by a single builder entity signing the `application/vnd.segel.origin+json` attestation.
- **Security Boundary**: A compromise of the single builder's private key could allow an attacker to sign provenance for an altered bundle (though the separate author manifest signature and deterministic inspector policy evaluation would still detect non-author files or prohibited capabilities).
- **Roadmap (v2.1)**: Dual independent builders producing independent provenance attestations with bit-for-bit reproducible build verification.

---

### LIM-003: Tamper Evidence vs. Absolute Storage Immutability
- **PRD v2.0 Reference**: §8 (Transparency Ledger & Append-Only Log)
- **Architectural Reality**: The Transparency Ledger utilizes SQLite with Write-Ahead Logging (`PRAGMA journal_mode=WAL`) and SQL triggers preventing `UPDATE` and `DELETE` queries on `ledger_entries` and `checkpoints`. However, SQLite is an application-level library; a host OS administrator or compromised database file owner could alter raw bytes on disk.
- **Enforced Security Guarantee**: Immutability is **not** claimed through SQLite file properties. Cryptographic tamper evidence is strictly guaranteed through:
  1. RFC 6962 SHA-256 Merkle tree root hashes.
  2. Ledger Signer digital signatures over checkpoints (`size`, `root_hash`).
  3. External Witness cosignatures over Merkle consistency proofs.
  Any modification of historical entries on disk invalidates all subsequent checkpoints and witness consistency checks (`CHECKPOINT_FORK`).

---

### LIM-004: In-Memory Synthetic Keys in Demonstration Harness
- **PRD v2.0 Reference**: §15 (Key Ceremonies & Key Management)
- **MVP Implementation**: `scripts/demo.py` generates synthetic Ed25519 keypairs in-memory at process startup to demonstrate the end-to-end multi-party workflow without requiring pre-existing physical infrastructure.
- **Operational Requirement**: In production, private keys must be generated during a formal key ceremony, stored on dedicated HSMs or restricted POSIX filesystems (`0o600`), and loaded by the respective CLI entry points via `--key` arguments.

---

### LIM-005: Cross-Platform File Permission Variations (POSIX vs Windows)
- **PRD v2.0 Reference**: §10 (Receiver Baseline Adapter & Deployment Protections)
- **Implementation Detail**: Requirement SEC-025 mandates deployed files be marked read-only (`0o444`). On POSIX systems, `chmod 0444` sets standard UNIX permissions (`-r--r--r--`). On Windows NTFS, this sets the Win32 `FILE_ATTRIBUTE_READONLY`.
- **Handling**: Rollback mechanisms in `BaselineAdapter` handle cross-platform file clearing by resetting `stat.S_IWRITE` prior to atomic unlinking or replacement. Windows ACL inheritance may vary based on parent directory defaults.

---

## 2. Functional & Workflow Limitations

### LIM-006: AI Advisory Inference Optionality & Isolation
- **PRD v2.0 Reference**: §7 (Inspection & AI Advisory Analysis)
- **Design Boundary**: AI advisory evaluation (via local Ollama inference) is strictly non-authoritative.
- **Implemented Behavior**:
  - If Ollama is unreachable, unconfigured, or returns an error, the inspector records `ai_status = "skipped"` or `ai_status = "failed"`.
  - Under no circumstances can AI advisory output downgrade a deterministic `REJECT` verdict, authorize a release, or override human approver quorums.
  - The deterministic capability extraction engine provides the authoritative security gate.

---

### LIM-007: QR Air-Gapped Transfer Simulation in Release Desk
- **PRD v2.0 Reference**: §17 (Air-Gapped QR Transfer Protocol)
- **MVP Implementation**: The approver CLI (`segel-approver`) generates compact CBOR/JSON QR request payloads and validates signed responses. In the automated demo script, this transfer occurs in-memory.
- **Roadmap**: Mobile/tablet scanner client integrating device cameras for physical optical QR scanning and animated multi-frame QR streams for payloads exceeding 2 KB.

---

### LIM-008: Single Witness Configuration Default
- **PRD v2.0 Reference**: §8.3 (Witness Network & Equivocation Prevention)
- **MVP Implementation**: The default verification policy enforces `witness_cosignature_count = 1`.
- **Capability**: The architecture and schema natively support multi-witness verification (`witness_cosignatures: list[dict]`). To enforce a multi-witness quorum, administrators simply configure `witness_cosignature_count: 2` or higher in `policy.json` and deploy additional witness daemons.

---

## 3. Previously Reported Items Remediated During Audit

| Previous Finding ID | Description | Remediation Status |
|:---|:---|:---:|
| **PREV-01** | Missing unit test suites for individual pipeline modules | **RESOLVED**: 234 automated tests implemented across all 15 components. |
| **PREV-02** | Hypothesis property-based testing not executed | **RESOLVED**: 16 Hypothesis property tests passing in `tests/unit/test_properties.py`. |
| **PREV-03** | Windows read-only file rollback permission error | **RESOLVED**: `_safe_rmtree` and `_safe_unlink` implemented with error recovery. |
| **PREV-04** | Starlette TemplateResponse compatibility error | **RESOLVED**: Updated template rendering across `app.py`. |
| **PREV-05** | SQLite multi-thread connection sharing | **RESOLVED**: `check_same_thread=False` and connection context management added. |
| **PREV-06** | Mypy strict mode type discrepancies | **RESOLVED**: 65 type annotations added; mypy passes with 0 errors across 41 files. |

