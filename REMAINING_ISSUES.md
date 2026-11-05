# SEGEL Remaining Issues, Risks, Limitations, and Blocked Items

This document provides a technical accounting of all remaining non-blocking defects, architectural limitations, operational risks, and roadmap items identified during the independent technical verification of SEGEL MVP.

---

## 1. Defect Status & Open Bug Inventory

Following the remediation of the 16 defects detailed in `BUG_FIX_LOG.md` and the addition of `DeploymentReceipt` test coverage, there are currently **0 critical, 0 high, and 0 medium severity open defects** in the core codebase.

### Minor / Informational Items:
1. **INF-01: Upstream Test Client Deprecation Warning**:
   - `StarletteDeprecationWarning: Using 'httpx' with 'starlette.testclient' is deprecated; install 'httpx2' instead.`
   - *Impact*: Zero functional impact. Pytest outputs 1 warning during web route tests.
   - *Remediation*: Non-urgent; upgrade Starlette test harnesses when `httpx2` reaches general availability.
2. **INF-02: Pytest-Asyncio Default Fixture Loop Scope Warning**:
   - `PytestDeprecationWarning: The configuration option 'asyncio_default_fixture_loop_scope' is unset.`
   - *Impact*: Zero functional impact. Pytest outputs 1 configuration notice.
   - *Remediation*: Explicitly configure `asyncio_default_fixture_loop_scope = "function"` in `pyproject.toml` in v2.1.

---

## 2. Inherent Architectural Risks & Mitigations

### RISK-01: Offline Revocation Blind Spot
- **Risk Statement**: An offline Receiver cannot query real-time Certificate Revocation Lists (CRLs) or OCSP responders. If a private key is compromised, an offline receiver will continue accepting signatures signed by that key until a new signed Trust Update Package is physically delivered.
- **Architectural Impact**: Critical in theory, but inherent to air-gapped systems.
- **Mitigation Enforced**:
  - Verification policy supports `freshness_mode = "strict"`, enforcing maximum epoch age.
  - If `receiver_epoch < required_min_epoch`, the receiver fails closed (`EPOCH_STALE`).
  - Releases can be placed on `HELD` status in trust snapshots.
- **Operator Requirement**: Security operations must enforce disciplined physical media rotation for trust root updates on a defined cadence (e.g., daily or weekly).

### RISK-02: Single-Point-of-Failure on Storage File Ownership
- **Risk Statement**: The Transparency Ledger stores entries in an SQLite database file (`ledger.db`). While SQL triggers prohibit `UPDATE` and `DELETE` queries at the application level, a privileged root/admin user with direct write access to the underlying storage filesystem could tamper with raw database bytes.
- **Architectural Impact**: Moderate.
- **Mitigation Enforced**:
  - Immutability is anchored cryptographically, not by SQLite file permissions.
  - Checkpoints are signed with the Ledger Signer's private key.
  - External Witnesses verify Merkle consistency proofs and cosign checkpoints.
  - Any out-of-band byte alteration corrupts the Merkle tree root and triggers `CHECKPOINT_FORK` on the witness and verifier nodes.

### RISK-03: Windows vs. POSIX File Permission Divergence
- **Risk Statement**: SEC-025 requires deployed files to be read-only (`0o444`). POSIX filesystems support exact octal modes (`-r--r--r--`). Windows NTFS maps `0o444` to the Win32 `FILE_ATTRIBUTE_READONLY`, which can be cleared by any process with write ACLs on the parent directory.
- **Architectural Impact**: Low.
- **Mitigation Enforced**:
  - The Baseline Adapter implements `_safe_rmtree` and `_safe_unlink` to ensure atomic rollback functions cleanly on both operating systems.
  - In production, Windows administrators must configure NTFS ACL inheritance to restrict parent directory write access to the service account.

---

## 3. Scope Limitations of the MVP

The following architectural capabilities described in PRD v2.0 are intentionally scoped out of the MVP milestone:

| Limitation ID | Feature / Component | PRD v2.0 Section | MVP State | Production Target (v2.1+) |
|:---|:---|:---:|:---|:---:|
| **LIM-01** | Dual Independent Builders | §6.2 | Single builder provenance | Dual independent builders with bit-for-bit reproducible build checking |
| **LIM-02** | Distributed Witness Federation | §8.3 | Single witness default (`cosignature_count=1`)| 3-node Byzantine fault-tolerant witness network |
| **LIM-03** | Optical QR Scanner Mobile App | §17.3 | Compact JSON/CBOR air-gap payload CLI | Native mobile/tablet optical camera QR scanner application |
| **LIM-04** | Hardware Security Module (HSM) | §15.2 | File-based private keys (`0o600` permissions) | PKCS#11 / YubiKey PIV / CloudHSM hardware integration |
| **LIM-05** | CycloneDX SBOM Generation | §19 | Declared dependencies in `pyproject.toml` | Automated CycloneDX v1.5 JSON SBOM generation per release |
| **LIM-06** | AI Advisory Model Service | §7.3 | Optional/skipped when Ollama is unavailable | Local containerized Ollama LLM service with Llama-3 model |

---

## 4. Blocked Items Requiring Production Infrastructure

The following validation tasks cannot be executed within the synthetic demonstration environment and require external enterprise infrastructure:

1. **Physical Air-Gap Optical Camera Testing**:
   - *Blocker*: Requires physical optical hardware (scanner gun, mobile camera, or tablet display).
   - *Status*: **BLOCKED FOR MVP LAB**; validated via CBOR/JSON payload serialization and simulation.
2. **Hardware Security Module (HSM) Key Signing**:
   - *Blocker*: Requires physical cryptographic hardware token (YubiKey or HSM appliance).
   - *Status*: **BLOCKED FOR MVP LAB**; validated using software Ed25519 keypairs stored with restricted permissions (`0o600`).
3. **Multi-Host Geographic Network Latency Testing**:
   - *Blocker*: Requires distributed multi-cloud or multi-datacenter deployment.
   - *Status*: **BLOCKED FOR LOCAL AUDIT**; validated via Docker container networking and isolated network namespaces (`network_mode: none`).

---

## 5. Risk Remediation Plan & Roadmap Recommendations

### Phase 1: Pre-Pilot Hardening (Immediate)
- Mandate formal key generation ceremonies for all 7 key roles using air-gapped workstations.
- Lock down private key directory permissions to `0o700` and files to `0o600`.
- Distribute signed `trust_root.json` and `policy.json` out-of-band to all participant nodes.

### Phase 2: Version 2.1 Enhancements (Next Release Cycle)
- Implement secondary independent builder worker to enable bit-for-bit reproducible packaging.
- Deploy a secondary witness daemon and increase `witness_cosignature_count` to 2 in `policy.json`.
- Integrate optical QR scanning library into a mobile companion client.

### Phase 3: Version 2.2 Enterprise Hardening
- Implement PKCS#11 hardware signing integration for approver and ledger keys.
- Integrate automated CycloneDX SBOM generation into the build pipeline.

