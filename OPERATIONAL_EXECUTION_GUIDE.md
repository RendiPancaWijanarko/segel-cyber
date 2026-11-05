# SEGEL Operational Execution Guide & Operator Runbook

**Target System**: SEGEL MVP Version 0.1.0-MVP  
**Audience**: Release Engineers, AppSec Officers, and Fleet Operators  
**Purpose**: Standard Operating Procedure (SOP) for executing release lifecycles, canary promotion, and offline deployment  

---

## 1. Release Lifecycle Architecture Overview

SEGEL enforces a 5-stamp cryptographic pipeline:
$$\text{Origin} \xrightarrow{\text{Stamp 1}} \text{Inspect} \xrightarrow{\text{Stamp 2}} \text{Approve} \xrightarrow{\text{Stamp 3}} \text{Record} \xrightarrow{\text{Stamp 4}} \text{Test} \xrightarrow{\text{Stamp 5}} \text{Promote}$$

Every transition is recorded in a cryptographically bound DSSE envelope. No release can be applied to an offline receiver unless all required stamps are present and valid.

---

## 2. Service Startup & Pre-Flight Checks

### 2.1 Starting the Transparency Ledger & Release Desk
On the Release Desk host, start the service as a Single-Writer daemon:
```bash
uvicorn release_desk.app:app --host 0.0.0.0 --port 8000 --workers 1
```

> [!WARNING]
> Never increase `--workers` beyond 1. Multiple worker processes will cause primary key collisions on SQLite entries due to process-local in-memory Merkle tree state.

Verify health:
```bash
curl -s http://localhost:8000/healthz | jq .
```

### 2.2 Starting the Witness Daemon
On the independent Witness host, launch the witness service:
```bash
segel-witness serve --key /etc/segel/keys/witness.priv.json --port 8080
```

---

## 3. End-to-End Operational Release Workflow

### Step 1: Author Creates & Signs Release Manifest
The configuration author defines the payload files and produces the signed manifest:
```bash
python -c "
from builder.builder import build_release_package, sign_manifest
from segel_core.crypto.ed25519 import KeyPair
from pathlib import Path
import json

# Define configuration payload
files = {
    'config/app.yaml': b'server:\n  port: 8080\n',
    'config/logging.yaml': b'log_level: info\nlog_file: /var/log/app.log\n'
}

# Load author key
author_data = json.loads(Path('/etc/segel/keys/author.priv.json').read_text())
author_kp = KeyPair.from_private_bytes(bytes.fromhex(author_data['private_key_hex']))

# Build package bundle
bundle = build_release_package(
    files=files,
    release_id='REL-2026-001',
    sequence=1,
    purpose='Production baseline parameter update',
    canary_targets=['canary-1', 'canary-2'],
    general_scope=['canary-1', 'canary-2', 'unit-3']
)

# Author signs manifest
manifest_env = sign_manifest(bundle, author_kp)
Path('staged_manifest.json').write_text(manifest_env.model_dump_json(indent=2))
print(f'[+] Manifest signed: {bundle.manifest_digest}')
"
```

### Step 2: Builder Issues Origin Provenance (Stamp 1)
The automated build machine produces the SLSA-aligned Origin DSSE envelope:
```bash
python -c "
from builder.builder import sign_origin
from segel_core.crypto.ed25519 import KeyPair
from pathlib import Path
import json

builder_data = json.loads(Path('/etc/segel/keys/builder.priv.json').read_text())
builder_kp = KeyPair.from_private_bytes(bytes.fromhex(builder_data['private_key_hex']))

origin_env = sign_origin(bundle, builder_kp)
Path('staged_origin.json').write_text(origin_env.model_dump_json(indent=2))
print('[+] STAMP 1 (Origin) issued.')
"
```

### Step 3: Inspector Policy Analysis (Stamp 2)
The policy engine deterministically extracts capabilities (`network_listen`, `file_write`) and evaluates security policies:
```bash
python -c "
from inspector.inspector import inspect_release, create_inspect_attestation, sign_inspect
from segel_core.crypto.ed25519 import KeyPair
from pathlib import Path
import json

inspector_data = json.loads(Path('/etc/segel/keys/inspector.priv.json').read_text())
inspector_kp = KeyPair.from_private_bytes(bytes.fromhex(inspector_data['private_key_hex']))

inspection = inspect_release(files=files, manifest=bundle.manifest, manifest_digest=bundle.manifest_digest, ai_enabled=False)
inspect_stmt = create_inspect_attestation(inspection, bundle.manifest, bundle.manifest_digest)
inspect_env = sign_inspect(inspect_stmt, inspector_kp)
Path('staged_inspect.json').write_text(inspect_env.model_dump_json(indent=2))
print(f'[+] STAMP 2 (Inspect) issued: verdict={inspection.verdict}')
"
```

### Step 4: Multi-Party Approver Quorum (Stamp 3)
Approvers review the Inspect attestation and diff. At least 2 approvals across disjoint groups (`group-0` and `group-1`) must be collected.

```bash
# Approver 1 (Security, group-0) signs
segel-approver sign \
    --key /etc/segel/keys/approver_sec.priv.json \
    --payload staged_approval_req.json \
    --output sig_approver_sec.json

# Approver 2 (Operations, group-1) signs
segel-approver sign \
    --key /etc/segel/keys/approver_ops.priv.json \
    --payload staged_approval_req.json \
    --output sig_approver_ops.json

# Aggregate signatures into the Approve DSSE envelope
segel-approver aggregate \
    --statement staged_approval_stmt.json \
    --request staged_approval_req.json \
    --signatures sig_approver_sec.json,sig_approver_ops.json \
    --output staged_approve.json
```

### Step 5: Transparency Ledger Recording (Stamp 4)
The candidate release is appended to the Merkle tree:
1. Entry appended: `candidate_recorded`.
2. Checkpoint signed by Ledger.
3. Witness daemon cosigns checkpoint.
4. Merkle inclusion proof generated.
5. **Candidate Release Passport** assembled.

### Step 6: Canary Staging & Receipt Collection (Stamp 5)
1. Copy candidate package and passport to USB drive:
   ```bash
   cp -r candidate_bundle/ /media/usb/
   ```
2. On `canary-1` and `canary-2`, execute:
   ```bash
   segel-receiver apply \
       --passport /media/usb/candidate_passport.json \
       --package /media/usb/bundle.tar.gz \
       --state-dir /var/lib/segel/state \
       --trust-root /etc/segel/trust_root.json \
       --key /etc/segel/keys/canary_1.priv.json \
       --output-receipt /media/usb/canary_1_receipt.json
   ```
3. Return USB drive to Release Desk.

### Step 7: Promotion Evaluation & General Passport Assembly
The Release Desk evaluates canary receipts against pre-committed criteria:
1. `evaluate_promotion()` confirms 2 healthy canary receipts.
2. Ledger records `promotion_recorded` entry.
3. **General Release Passport** assembled containing all 5 stamps.

### Step 8: Offline General Deployment
1. Copy general release package and general passport to air-gapped general receivers via physical USB media.
2. Execute deployment on `unit-3`:
   ```bash
   segel-receiver apply \
       --passport /media/usb/general_passport.json \
       --package /media/usb/bundle.tar.gz \
       --state-dir /var/lib/segel/state \
       --trust-root /etc/segel/trust_root.json \
       --key /etc/segel/keys/receiver_general.priv.json \
       --output-receipt /media/usb/unit_3_receipt.json
   ```
3. The offline receiver:
   - Independently verifies all 5 stamps against `/etc/segel/trust_root.json`.
   - Verifies Merkle tree inclusion proof and witness cosignatures.
   - Enforces anti-rollback monotonic sequence checks (`highest_sequence < new_sequence`).
   - Atomically deploys configuration files with read-only permissions (`0o444`).
   - Emits a signed deployment receipt.

---

## 4. Routine Maintenance & Backup Procedures

### 4.1 Daily Ledger Online Hot Backup
Run daily via cron or systemd timer:
```bash
python scripts/backup_ledger.py backup \
    --source /var/lib/segel/ledger.db \
    --target /var/backups/segel/ledger_$(date +%Y%m%d).db
```

### 4.2 Verifying Backup Integrity
```bash
python scripts/backup_ledger.py verify \
    --file /var/backups/segel/ledger_$(date +%Y%m%d).db
```
The utility reconstructs the Merkle tree from disk and verifies the root hash against signed checkpoints.

### 4.3 Disaster Recovery Restoration
In the event of hardware failure:
1. Restore backup file:
   ```bash
   cp /var/backups/segel/ledger_backup.db /var/lib/segel/ledger.db
   chmod 600 /var/lib/segel/ledger.db
   chown segel:segel /var/lib/segel/ledger.db
   ```
2. Start Release Desk service:
   ```bash
   systemctl start segel-release-desk
   ```
3. Write operations will safely resume from the restored checkpoint index without sequence gaps or data loss.

