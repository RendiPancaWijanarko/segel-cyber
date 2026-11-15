# SEGEL Final Pilot Prerequisites & Operational Runbook Checklist

**Auditor**: Independent DevOps Auditor & Production Readiness Specialist  
**Target Milestone**: SEGEL MVP Version 0.1.0-MVP  
**Document Purpose**: Mandatory Actionable Checklist Prior to Controlled Pilot Deployment  
**Status**: **MANDATORY PRE-PILOT GATES**

---

## 1. Executive Summary & Purpose

The independent verification campaign has confirmed that the SEGEL software implementation satisfies all PRD v2.0 requirements, passes all 244 automated tests under Python 3.12, executes within a zero-network kernel namespace, and enforces crash resilience and atomic rollback.

However, moving from automated testing and synthetic demonstration into a **Controlled Pilot Deployment** requires human operational rigor.

> [!CRITICAL]
> Under no circumstances should synthetic keys, default demo credentials, or multi-process SQLite write configurations be used in a live pilot. The following prerequisites must be formally executed and signed off by the pilot operations team prior to accepting production traffic or critical configuration files.

---

## 2. Phase 1: Cryptographic Key Ceremony & Trust Distribution

- [ ] **1.1 Air-Gapped Key Generation**
  - **Requirement**: Each private key must be generated on its respective operational host or an air-gapped machine. Never generate all 11 keys on a single shared host for pilot operations.
  - **Required Keys**:
    1. Author Key (`author.priv.json` / `author.pub.json`)
    2. Builder Key (`builder.priv.json` / `builder.pub.json`)
    3. Inspector Signer Key (`inspector.priv.json` / `inspector.pub.json`)
    4. Approver 0 (Security, `group-0`): `approver_sec.priv.json`
    5. Approver 1 (Operations, `group-1`): `approver_ops.priv.json`
    6. Approver 2 (QA / Lead, `group-0`): `approver_qa.priv.json`
    7. Ledger Signer Key (`ledger.priv.json` / `ledger.pub.json`)
    8. Witness Key (`witness.priv.json` / `witness.pub.json`)
    9. Canary 1 Unit Key (`canary_1.priv.json` / `canary_1.pub.json`)
    10. Canary 2 Unit Key (`canary_2.priv.json` / `canary_2.pub.json`)
    11. General Unit Key (`receiver_general.priv.json` / `receiver_general.pub.json`)

- [ ] **1.2 Trust Root Assembly & Canonicalization**
  - Collect all 11 public keys (`*.pub.json`).
  - Assemble `trust_root.json` and `policy.json` (specifying 2-of-3 approver threshold with `group-0` and `group-1` representation).
  - Format using RFC 8785 Canonical JSON (`python -c "import segel_core.canonical..."`).
  - Compute canonical SHA-256 digests:
    ```bash
    sha256sum /etc/segel/trust_root.json
    sha256sum /etc/segel/policy.json
    ```

- [ ] **1.3 Out-of-Band Trust Distribution**
  - Physically transport `trust_root.json` and `policy.json` to all nodes (Release Desk, Witness, Canaries, General Receivers).
  - Operators must manually verify that the SHA-256 fingerprint matches the ceremony transcript on every target machine before starting any receiver service.

---

## 3. Phase 2: Host Hardening & File Permission Lockdown

- [ ] **2.1 File System Permissions (POSIX)**
  - Ensure private key files are restricted to the owning service account (`segel`):
    ```bash
    chmod 700 /etc/segel/keys
    chmod 600 /etc/segel/keys/*.priv.json
    chown -R segel:segel /etc/segel
    ```
  - Verify that group and other read/write permissions are strictly revoked (`-rw-------`).

- [ ] **2.2 Receiver State & Deploy Root Isolation**
  - Create persistent state directory:
    ```bash
    mkdir -p /var/lib/segel/state
    chmod 700 /var/lib/segel/state
    chown -R segel:segel /var/lib/segel
    ```
  - Create deployment target root:
    ```bash
    mkdir -p /opt/app/config
    chown segel:segel /opt/app/config
    chmod 755 /opt/app/config
    ```
  - Confirm that the Receiver baseline adapter will apply released files with read-only mode `0o444`.

---

## 4. Phase 3: Single-Writer Transparency Ledger Deployment

- [ ] **3.1 Single Uvicorn / Service Process Enforcement**
  - **Constraint**: To guarantee RFC 6962 Merkle tree consistency, the Transparency Ledger service must run as a **single process** (workers = 1).
  - **Verification**: In systemd service unit or container startup, verify:
    ```bash
    uvicorn release_desk.app:app --host 0.0.0.0 --port 8000 --workers 1
    ```
  - Never run multiple worker processes (`--workers > 1`) or horizontal multi-pod replicas against a single SQLite ledger file.

- [ ] **3.2 SQLite WAL & Busy Timeout Verification**
  - Verify that the ledger database initializes with:
    - `PRAGMA journal_mode = WAL;`
    - `PRAGMA busy_timeout = 5000;`
    - `PRAGMA synchronous = NORMAL;`
    - `PRAGMA foreign_keys = ON;`

- [ ] **3.3 Disaster Recovery & Backup Schedule**
  - Establish a cron job or scheduled task executing the online backup API:
    ```bash
    python -c "
    from ledger.ledger import TransparencyLedger
    import sys
    l = TransparencyLedger('/var/lib/segel/ledger.db')
    l.backup('/backup/segel/ledger_backup.db')
    "
    ```
  - Verify that the backup file is copied to secondary, write-once or offsite storage.

---

## 5. Phase 4: Air-Gapped Transport & Pilot Fleet Operation

- [ ] **4.1 Dedicated Physical Removable Media**
  - Format dedicated USB drives with ext4 (or FAT32) for release transport.
  - Where available, use physical hardware write-protect switch drives when reading from air-gapped receivers.

- [ ] **4.2 End-to-End Pilot Staging Workflow**
  1. **Authoring & Build**: Author signs manifest; CI pipeline generates Origin provenance.
  2. **Inspection**: Deterministic inspector verifies capabilities; Inspect attestation issued.
  3. **Multi-Party Approval**: Approvers review Inspect attestation and sign via QR or air-gap terminal (2-of-3 with cross-group representation).
  4. **Ledger & Witness**: Candidate release appended to Transparency Ledger; Witness cosigns checkpoint.
  5. **Canary Staging**: Transport candidate package and candidate passport to Canary units.
  6. **Canary Deployment**: Canary receivers execute `segel-receiver apply`; signed health receipts generated.
  7. **Promotion Execution**: Receipts returned to Release Desk; Promotion Controller evaluates criteria; Ledger records promotion; General Release Passport assembled.
  8. **General Deployment**: Transport general package and passport to disconnected General Receivers; offline verification confirms all 5 stamps; configurations deployed atomically.

---

## 6. Pilot Operational Sign-Off Form

| Verification Checkpoint | Lead Responsible | Date & Time | Signature / Status |
|---|---|---|:---:|
| 1. Cryptographic Key Ceremony Completed | Security Lead | | [ ] PENDING |
| 2. Trust Root Distributed & Verified | DevOps Lead | | [ ] PENDING |
| 3. File Permissions Locked Down (`chmod 600`) | System Admin | | [ ] PENDING |
| 4. Single-Writer Ledger Confirmed (Workers=1) | Architect | | [ ] PENDING |
| 5. Backup Cron Configured & Verified | DBA / DevOps | | [ ] PENDING |
| 6. Air-Gap Transport Media Prepared | Pilot Operator | | [ ] PENDING |
| **FINAL AUTHORIZATION FOR PILOT TRAFFIC** | **Release Board** | | **[ ] APPROVED** |

