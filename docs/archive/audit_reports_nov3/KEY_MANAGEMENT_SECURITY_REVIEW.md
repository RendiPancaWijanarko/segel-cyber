# SEGEL Cryptographic Key Management & Security Review

**Auditor**: Independent Application Security Engineer & Cryptographic Assessor  
**Target Milestone**: SEGEL MVP Version 0.1.0-MVP  
**Review Date**: November 3, 2026  
**Final Status**: **ACCEPTABLE FOR CONTROLLED PILOT (WITH DOCUMENTED LIMITATIONS)**

---

## 1. Executive Summary & Review Scope

Cryptographic integrity is the foundation of SEGEL. Under PRD v2.0 §13/§16, TAS §8.10, and Security Principles SEC-001 through SEC-004:
- All releases, attestations, approvals, ledger entries, and deployment receipts are signed using **Ed25519** (RFC 8032) wrapped in **DSSE** (Dead Simple Signing Envelope, RFC 9162 / in-toto specification).
- Trust is established through an immutable `TrustRoot` containing public key records and role threshold rules, verified against a `VerificationPolicy` and `TrustSnapshot`.

This independent security review examined:
1. The architecture and composition of the **11-key hierarchy**.
2. Role separation, duty segregation, and multi-party quorum enforcement.
3. Trust metadata compilation and canonical serialization (RFC 8785).
4. Physical/file-level key permissions and disk storage hygiene.
5. Verification that zero private keys or secrets are leaked into the repository.
6. Identified architectural limitations and the operational prerequisites required prior to live pilot key generation.

---

## 2. The 11-Key Hierarchy & Role Mapping

The SEGEL MVP security model establishes an 11-key operational hierarchy across seven distinct functional roles:

| # | Key Identifier | Functional Role | Group / Domain | Minimum Threshold | Purpose & Boundary |
|---|---|---|---|:---:|---|
| 1 | `author` | `author` | `default` | 1 | Signs manifest envelope; excluded from acting as approver. |
| 2 | `builder` | `builder` | `ci-pipeline` | 1 | Generates Origin provenance (Stamp 1); binds source commit and package digest. |
| 3 | `inspector` | `inspector_signer` | `sec-engine` | 1 | Evaluates deterministic policy & capability rules; signs Inspect attestation (Stamp 2). |
| 4 | `approver_sec` | `approver` | `group-0` (Security) | 2-of-3 Quorum | Reviews Inspect attestation and diff; signs Approve envelope (Stamp 3). |
| 5 | `approver_ops` | `approver` | `group-1` (Operations)| 2-of-3 Quorum | Operations approval; cross-group threshold enforcement. |
| 6 | `approver_qa` | `approver` | `group-0` (QA / Lead) | 2-of-3 Quorum | Alternate quorum member; satisfies 2-of-3 threshold. |
| 7 | `ledger` | `ledger` | `transparency` | 1 | Appends to RFC 6962 Merkle tree; signs tree checkpoints (Stamp 4). |
| 8 | `witness` | `witness` | `independent` | 1 | Cosigns ledger checkpoints; detects ledger split-brain or fork attacks. |
| 9 | `canary_1` | `receiver` | `canary-fleet` | 1 | Deploys canary candidate; signs health test receipt (Stamp 5). |
| 10 | `canary_2` | `receiver` | `canary-fleet` | 1 | Deploys canary candidate; signs health test receipt (Stamp 5). |
| 11 | `receiver_general` | `receiver` | `production-fleet` | 1 | Deploys promoted release; signs general deployment receipt. |

---

## 3. Role Separation & Segregation of Duties

The implementation enforces cryptographic separation of duties across all trust boundaries:

### 3.1 Author vs. Builder Separation (SEC-002)
- **Constraint**: The Author (developer specifying files) cannot produce the Origin provenance.
- **Enforcement**: [`src/builder/builder.py`](file:///c:/Users/Rendi/OneDrive/ドキュメント/Dokumen Pribadi/KOMPETISI/segel-cyber/src/builder/builder.py) requires an independent builder key. The builder computes the SHA-256 package hash and issues the SLSA-aligned Origin envelope.

### 3.2 Author Exclusion from Approval Quorum (SEC-003 & AT-008)
- **Constraint**: The Author of a release cannot approve their own release, even if the Author key is mistakenly assigned the `approver` role in the trust root.
- **Enforcement**: [`src/segel_core/verification/passport.py`](file:///c:/Users/Rendi/OneDrive/ドキュメント/Dokumen Pribadi/KOMPETISI/segel-cyber/src/segel_core/verification/passport.py) extracts `manifest_author_key_id` from the signed manifest envelope. When validating approval signatures in `_verify_approve_stamp()`, any signature matching `manifest_author_key_id` is filtered out before computing quorum.
- **Evidence**: Verified in unit test `test_adversarial.py::test_at008_author_self_approval_rejected` and `scripts/demo.py` Step 18.

### 3.3 Multi-Party Approver Quorum (2-of-3 with Disjoint Groups)
- **Constraint**: Approvals require at least 2 distinct signatures representing at least 1 from `group-0` and 1 from `group-1`.
- **Enforcement**: [`src/approver/approver.py`](file:///c:/Users/Rendi/OneDrive/ドキュメント/Dokumen Pribadi/KOMPETISI/segel-cyber/src/approver/approver.py) and verification policy check:
  ```python
  RoleThreshold(role="approver", threshold=2, group_minimums={"group-0": 1, "group-1": 1})
  ```
- **Evidence**: Two approvers from `group-0` alone cannot satisfy policy requirements without `group-1` participation.

### 3.4 Ledger vs. Witness Independence
- **Constraint**: The Transparency Ledger cannot vouch for its own checkpoints without third-party witness cosignatures.
- **Enforcement**: [`src/witness/witness.py`](file:///c:/Users/Rendi/OneDrive/ドキュメント/Dokumen Pribadi/KOMPETISI/segel-cyber/src/witness/witness.py) operates independently. The passport assembler strictly requires `witness_cosignatures` on `LedgerProof`. A passport missing witness cosignatures fails validation at the Receiver (`MISSING_WITNESS_COSIGNATURE`).

---

## 4. Key Storage, Permissions & Leakage Verification

### 4.1 Key Storage Format & Permission Controls
[`scripts/init_keys.py`](file:///c:/Users/Rendi/OneDrive/ドキュメント/Dokumen Pribadi/KOMPETISI/segel-cyber/scripts/init_keys.py) generates keys and writes them to disk:
1. **Private Keys**: Saved to `*.priv.json` with strict POSIX permissions `0o600` (read/write by owner only; group/other denied). Directories are created with `0o700`.
2. **Public Keys**: Exported as base64-encoded raw 32-byte Ed25519 public keys in `*.pub.json` and compiled into `trust_root.json`.
3. **Canonical Serialization**: All trust structures are normalized using RFC 8785 Canonical JSON (`src/segel_core/canonical.py`), preventing signature malleability or whitespace divergence.

### 4.2 Leakage & Git Hygiene Audit
A deep filesystem scan was executed across the entire repository:
1. **File Extension Scan**: Searched for `*.priv.json`, `*.key`, `*.pem`, `*.p12`, `*.pfx`:
   - **Result**: Zero private key files detected in the workspace.
2. **Source Code & Documentation Grep**: Searched for `BEGIN PRIVATE KEY`, `private_key_hex`, and private key raw byte literals:
   - **Result**: Only the schema and serialization templates in `scripts/init_keys.py` were matched. No hardcoded private keys exist in source code, configuration files, or markdown documentation.
3. **Git Ignore Hardening**:
   [`c:\Users\Rendi\OneDrive\ドキュメント\Dokumen Pribadi\KOMPETISI\segel-cyber\.gitignore`](file:///c:/Users/Rendi/OneDrive/ドキュメント/Dokumen Pribadi/KOMPETISI/segel-cyber/.gitignore) was inspected and verified to contain:
   ```gitignore
   .env
   *.priv.json
   *.key
   *.pem
   lab/keys/*.priv.json
   ```

---

## 5. Weaknesses & Limitations (Pilot Risk Analysis)

The MVP key management architecture was evaluated against production standards. The following limitations were identified and must be managed operationally during the controlled pilot:

| Identified Limitation | Risk Level | Description | Pilot Mitigation | Production Roadmap (v2.1) |
|---|:---:|---|---|---|
| **Software-Only Key Storage** | **Medium** | Private keys exist as unencrypted JSON files on disk. | Host OS file permission lockdown (`chmod 600`), encrypted filesystem mounts, isolated host access. | Hardware Security Module (HSM), PKCS#11, TPM 2.0 integration. |
| **All-in-One Synthetic Keygen** | **Low (MVP)** | `scripts/init_keys.py` generates all 11 keys on a single workstation. | Used strictly for local test and demonstration environments. For pilot, run manual distributed key ceremony. | Multi-party air-gapped key ceremony with ceremony transcripts. |
| **Air-Gap Revocation Propagation** | **Medium** | Air-gapped receivers cannot receive dynamic revocations mid-epoch. | Strict anti-rollback monotonic sequence checks; 2-of-3 approver quorums mitigate single key compromise. | Regular scheduled epoch advancements distributed via removable media. |
| **Lack of Split-Knowledge Key Recovery** | **Low (Pilot)** | If an approver or ledger private key is lost, no Shamir secret sharing exists. | Manual disaster recovery from offline encrypted backup media. | Shamir's Secret Sharing (SLIP-0039) for root trust and approver key recovery. |

---

## 6. Audit Verdict

| Security Control | PRD / TAS Requirement | Verification Status |
|---|---|:---:|
| Ed25519 DSSE Implementation | RFC 8032 / RFC 9162 | **VERIFIED PASS** |
| 11-Key Hierarchy & Role Mapping | PRD v2.0 §13/§16 | **VERIFIED PASS** |
| Separation of Duties (SEC-002) | Author != Builder | **VERIFIED PASS** |
| Author Self-Approval Exclusion (SEC-003) | Author signature rejected for approval | **VERIFIED PASS** |
| 2-of-3 Multi-Group Approver Quorum | Group-0 + Group-1 enforcement | **VERIFIED PASS** |
| Zero Private Key Leaks | No secrets in repo or documentation | **VERIFIED PASS** |
| Restricted File Permissions | `chmod 600` / `0700` implemented | **VERIFIED PASS** |

**Conclusion**: The cryptographic key management subsystem is **APPROVED FOR CONTROLLED PILOT DEPLOYMENT WITH DOCUMENTED MITIGATIONS**. Live pilot keys must be generated during a formal key ceremony following the prerequisites checklist.

