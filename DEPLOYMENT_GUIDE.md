# SEGEL Deployment & Operations Guide

This guide provides instructions for deploying, operating, and troubleshooting the SEGEL platform across containerized, local, and air-gapped environments.

---

## 1. System Architecture & Topology

```
                  ┌──────────────────────────────────────────────┐
                  │                 AUTHOR / CI                  │
                  │   Creates bundle files & signs manifest      │
                  └───────────────────────┬──────────────────────┘
                                          │
                                          ▼
                  ┌──────────────────────────────────────────────┐
                  │                   BUILDER                    │
                  │   Generates deterministic tar.gz & Origin    │
                  └───────────────────────┬──────────────────────┘
                                          │
                                          ▼
                  ┌──────────────────────────────────────────────┐
                  │                  INSPECTOR                   │
                  │   Capability extraction & policy evaluation  │
                  └───────────────────────┬──────────────────────┘
                                          │
                                          ▼
                  ┌──────────────────────────────────────────────┐
                  │               APPROVER QUORUM                │
                  │   Air-gapped QR review & multi-signing       │
                  └───────────────────────┬──────────────────────┘
                                          │
                                          ▼
                  ┌──────────────────────────────────────────────┐
                  │             TRANSPARENCY LEDGER              │
                  │   Append-only Merkle log + Witness cosign    │
                  │   Candidate Passport Assembled               │
                  └───────────────┬──────────────────────────────┘
                                  │
                 ┌────────────────┴────────────────┐
                 ▼                                 ▼
      ┌─────────────────────┐           ┌─────────────────────┐
      │   CANARY UNIT 1     │           │   CANARY UNIT 2     │
      │  Verify & Deploy    │           │  Verify & Deploy    │
      │  Generate Receipt   │           │  Generate Receipt   │
      └──────────┬──────────┘           └──────────┬──────────┘
                 │                                 │
                 └────────────────┬────────────────┘
                                  ▼
                  ┌──────────────────────────────────────────────┐
                  │             PROMOTION CONTROLLER             │
                  │   Evaluates health receipts vs criteria      │
                  │   Records promotion event in Ledger          │
                  │   General Passport Assembled                 │
                  └───────────────────────┬──────────────────────┘
                                          │
                                          ▼ (Physical / Air-Gap Transfer)
                  ┌──────────────────────────────────────────────┐
                  │           OFFLINE GENERAL RECEIVER           │
                  │   No Network Interface (`network_mode: none`)│
                  │   Verifies all 5 stamps independently        │
                  │   Applies config atomically (0o444 read-only)│
                  │   Generates signed deployment receipt        │
                  └──────────────────────────────────────────────┘
```

---

## 2. Docker & Containerized Lab Deployment

The fastest way to test the complete multi-unit topology is the Docker Compose lab.

### Step 1: Clone and Build Containers
```bash
docker compose -f lab/compose.yml up --build -d
```

### Step 2: Verify Running Services
```bash
docker compose -f lab/compose.yml ps
```
You should see:
- `segel-release-desk` running on `0.0.0.0:8000`
- `segel-canary-1` running in background
- `segel-canary-2` running in background
- `segel-unit-3` running with `network_mode: none` (completely offline)

### Step 3: Access Release Desk
Open your browser to:
```
http://localhost:8000
```
From the Release Desk, you can author releases, trigger canary deployments, and promote candidate passports to general distribution.

### Step 4: Tear Down
```bash
docker compose -f lab/compose.yml down -v
```

---

## 3. Local Bare-Metal Installation

For installing SEGEL directly on production hosts, build servers, or control workstations.

### Step 1: Install Package
```bash
# In a virtual environment:
python -m venv .venv
source .venv/bin/activate  # On Linux/macOS
# or .venv\Scripts\Activate.ps1 on Windows

pip install --upgrade pip
pip install -e ".[dev]"
```

### Step 2: Verify Installed CLI Tools
```bash
segel-receiver --help
segel-approver --help
segel-witness --help
```

---

## 4. Air-Gapped Offline Receiver Operations

General production units must be isolated from the network. Follow this protocol for distributing and deploying releases offline:

### Step 1: Export Release Bundle and Passport
On the connected build/promotion workstation:
```bash
# Files created during the promotion step:
# - release-BASELINE-UNIT-42-seq-1.tar.gz
# - general-passport-BASELINE-UNIT-42-seq-1.json
```
Copy these files to trusted removable media along with the SHA-256 checksums file:
```bash
sha256sum release-*.tar.gz general-passport-*.json > CHECKSUMS.txt
```

### Step 2: Transfer to Offline Host
Mount the media on the offline unit:
```bash
# Verify checksums before processing
sha256sum -c CHECKSUMS.txt
```

### Step 3: Execute Receiver Verification & Deployment
Run the offline receiver CLI:
```bash
segel-receiver verify general-passport-BASELINE-UNIT-42-seq-1.json \
    --bundle release-BASELINE-UNIT-42-seq-1.tar.gz \
    --trust-root /etc/segel/trust_root.json \
    --policy /etc/segel/policy.json \
    --key /etc/segel/keys/receiver_unit3.priv.json \
    --unit-id unit-3 \
    --unit-role general \
    --deploy-to /opt/app/config \
    --state-dir /var/lib/segel/state
```

The CLI performs:
1. Trust root and policy loading.
2. Monotonic sequence anti-rollback check against `/var/lib/segel/state/receiver_state.json`.
3. Offline verification of all 5 stamps:
   - **Origin**: Verifies builder signature on provenance.
   - **Inspect**: Confirms policy verdict is `PASS` or acceptable `WARN`.
   - **Approve**: Verifies approver signature threshold (author excluded).
   - **Record**: Verifies Merkle inclusion proof and witness cosignatures.
   - **Test**: Verifies signed canary receipts meeting promotion criteria.
4. Atomic staging, backup of existing files, deployment with `0o444` read-only permissions, and fixed vocabulary health probe verification.
5. Emits a signed deployment receipt: `deployment-receipt-unit-3.json`.

---

## 5. Operations & Administration Runbooks

### Runbook 1: Creating a New Release
1. Stage configuration files into a folder (e.g., `./configs/app.yaml`).
2. Run builder to generate manifest, tar.gz bundle, and builder provenance:
   ```python
   from builder.builder import build_release_package, sign_manifest, sign_origin
   # Or use Release Desk web UI at http://localhost:8000/release/new
   ```
3. Have the Author sign the manifest with the Author private key.

### Runbook 2: Air-Gapped Approver Signing (QR Workflow)
1. Export approval request payload:
   ```bash
   segel-approver request --manifest manifest.json --origin origin.json --inspect inspect.json --out approval_req.json
   ```
2. Display QR code or transfer JSON to air-gapped approver terminal.
3. Approver inspects the payload:
   ```bash
   segel-approver inspect approval_req.json
   ```
4. Approver signs the payload using the secure hardware or local approver key:
   ```bash
   segel-approver sign approval_req.json --key /path/to/approver_sec.priv.json --out response_sec.json
   ```
5. Transfer response back to Release Desk and aggregate into DSSE envelope.

### Runbook 3: Recovering from Interrupted Deployments
If a host loses power or crashes during deployment:
1. Inspect receiver state:
   ```bash
   segel-receiver status --state-dir /var/lib/segel/state
   ```
2. If `state_corrupt` or `in_progress` journal entry is detected:
   - The receiver fails closed and will reject new release deployments.
   - Run journal cleanup and rollback recovery:
     ```bash
     segel-receiver recover --state-dir /var/lib/segel/state --deploy-to /opt/app/config
     ```
   - Verify backup restored successfully and health check passes.

---

## 6. Troubleshooting & Error Code Guide

| Error Code | Meaning | Common Cause & Remediation |
|:---|:---|:---|
| `SIG_INVALID` | Signature verification failed | The key that signed the envelope is untrusted, wrong key ID, or payload was altered. Check trust root active keys. |
| `THRESHOLD_NOT_MET` | Insufficient approval signatures | Approval envelope does not meet threshold (e.g. 2-of-3). Remember: Author signature is excluded by policy (SEC-001). |
| `SEQUENCE_REPLAY` | Anti-rollback rejection | The release sequence is $\le$ the highest sequence previously applied on this receiver. Sequences must strictly increase. |
| `EPOCH_STALE` | Receiver epoch too low | The passport requires a newer trust epoch. Deploy a signed Trust Update Package to advance receiver epoch. |
| `STAMP_MISSING` | Required passport stamp absent | Attempted to deploy a candidate passport to a general unit, or promotion proof was omitted from general passport. |
| `DIGEST_MISMATCH` | File hash mismatch | File corrupted in transit or tampered. Ensure tar.gz matches `bundle_sha256` in manifest. |
| `ADAPTER_NOT_ALLOWED` | Disallowed deployment adapter | The adapter ID is not in `policy.json` `allowed_adapters` list. |
| `STATE_CORRUPT` | Receiver journal corrupted | Prior deployment interrupted. Check `/var/lib/segel/state/journal.log` and execute recovery runbook. |
| `HELD` | Release held in trust snapshot | Release was flagged as held by security operations. Do not deploy. |

