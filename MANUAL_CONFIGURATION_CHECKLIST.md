# SEGEL Manual Configuration & Pre-Flight Deployment Checklist

This document is an operational, step-by-step guide for administrators, security officers, and DevOps engineers preparing to deploy SEGEL outside the automated demonstration environment.

---

## 1. Prerequisites & Host Requirements

- [ ] **Operating System**: Linux (Ubuntu 22.04+, Debian 12+, RHEL 9+) or Windows Server 2022+ / Windows 11.
- [ ] **Python Runtime**: Python 3.12 or newer installed (`python --version` >= 3.12).
- [ ] **Container Engine** (Optional for containerized operation): Docker 24.0+ and Docker Compose v2.20+.
- [ ] **Storage System**: Persistent filesystem supporting POSIX file permissions or Windows ACLs with SQLite WAL support.
- [ ] **Network Isolation**: Ensure Offline Receiver targets have network interfaces strictly disabled or firewalled from inbound/outbound internet routing.

---

## 2. Cryptographic Key Ceremony & Generation

SEGEL requires strict role separation across cryptographic keys. **Never reuse a single key for multiple roles.**

Generate isolated Ed25519 keypairs for each designated role:

```bash
# Example generation using Python SEGEL CLI
python -c "
from segel_core.crypto.ed25519 import generate_keypair, export_public_key
import json, pathlib

roles = ['author', 'builder', 'inspector', 'approver_ops', 'approver_sec', 'ledger', 'witness_1', 'receiver_canary_1', 'receiver_canary_2', 'receiver_prod_1']
out = pathlib.Path('keys')
out.mkdir(exist_ok=True, mode=0o700)

for role in roles:
    kp = generate_keypair()
    (out / f'{role}.priv.json').write_text(json.dumps({'key_id': kp.key_id, 'private_key': kp.private_key_b64, 'role': role}))
    (out / f'{role}.pub.json').write_text(json.dumps({'key_id': kp.key_id, 'public_key': export_public_key(kp), 'role': role}))
"
```

- [ ] **Author Key**: Assigned to the release creator / configuration engineer.
- [ ] **Builder Key**: Stored securely on the packaging builder machine (must be different from Author key per SEC-002).
- [ ] **Inspector Signer Key**: Dedicated to the policy inspection engine.
- [ ] **Approver Keys**: Minimum 2 distinct keys for separate organizational groups (e.g., Operations and Security).
- [ ] **Ledger Signer Key**: Restricted to the Transparency Ledger append daemon.
- [ ] **Witness Cosigner Key**: Restricted to the independent Witness verification daemon.
- [ ] **Receiver Keys**: Dedicated key generated for each Receiver node to sign deployment receipts.

---

## 3. Secret Storage & File Permission Lockdown

Private key files must be protected at rest against unauthorized read access:

### On Linux / POSIX:
```bash
chmod 700 /etc/segel/keys
chmod 600 /etc/segel/keys/*.priv.json
chown -R segel:segel /etc/segel
```

### On Windows PowerShell:
```powershell
# Remove inheritance and restrict to current administrator / service account
$acl = Get-Acl "C:\segel\keys"
$acl.SetAccessRuleProtection($true, $false)
$adminRule = New-Object System.Security.AccessControl.FileSystemAccessRule("Administrators", "FullControl", "ContainerInherit,ObjectInherit", "None", "Allow")
$acl.AddAccessRule($adminRule)
Set-Acl -Path "C:\segel\keys" -AclObject $acl
```

- [ ] Private key directories restricted to `0o700` (`rwx------`).
- [ ] Private key files restricted to `0o600` (`rw-------`).
- [ ] Ensure private keys are never committed to git repositories or shared across network mounts.

---

## 4. Trust Root Authoring (`trust_root.json`)

Construct the official Trust Root containing active public keys and role definitions:

```json
{
  "schema_version": "https://segel.dev/schema/trust-root/v1.json",
  "trust_root_version": 1,
  "epoch": 1,
  "created_at": "2026-11-03T00:00:00Z",
  "keys": [
    {
      "key_id": "<BUILDER_KEY_ID>",
      "role": "builder",
      "algorithm": "ed25519",
      "public_key_b64": "<BASE64_PUBLIC_KEY>",
      "status": "active"
    },
    {
      "key_id": "<INSPECTOR_KEY_ID>",
      "role": "inspector_signer",
      "algorithm": "ed25519",
      "public_key_b64": "<BASE64_PUBLIC_KEY>",
      "status": "active"
    },
    {
      "key_id": "<APPROVER_OPS_KEY_ID>",
      "role": "approver",
      "group": "operations",
      "algorithm": "ed25519",
      "public_key_b64": "<BASE64_PUBLIC_KEY>",
      "status": "active"
    },
    {
      "key_id": "<APPROVER_SEC_KEY_ID>",
      "role": "approver",
      "group": "security",
      "algorithm": "ed25519",
      "public_key_b64": "<BASE64_PUBLIC_KEY>",
      "status": "active"
    },
    {
      "key_id": "<LEDGER_KEY_ID>",
      "role": "ledger",
      "algorithm": "ed25519",
      "public_key_b64": "<BASE64_PUBLIC_KEY>",
      "status": "active"
    },
    {
      "key_id": "<WITNESS_KEY_ID>",
      "role": "witness",
      "algorithm": "ed25519",
      "public_key_b64": "<BASE64_PUBLIC_KEY>",
      "status": "active"
    }
  ],
  "roles": [
    {
      "role": "approver",
      "threshold": 2,
      "group_minimums": {
        "operations": 1,
        "security": 1
      }
    }
  ]
}
```

- [ ] All required roles defined with active keys.
- [ ] Approver threshold configured (e.g., 2-of-3).
- [ ] Group minimums defined for Separation of Duties (SoD).
- [ ] Epoch initialized to non-zero positive integer (e.g., `1`).

---

## 5. Verification Policy Authoring (`policy.json`)

Construct the deployment verification policy:

```json
{
  "schema_version": "https://segel.dev/schema/policy/v1.json",
  "policy_version": 1,
  "required_stamps": ["origin", "inspect", "approve", "record"],
  "min_inspect_policy_version": 1,
  "witness_cosignature_count": 1,
  "canary_required_count": 2,
  "allowed_adapters": ["segel-baseline-adapter/v1"],
  "freshness_mode": "strict"
}
```

- [ ] `required_stamps` includes `origin`, `inspect`, `approve`, and `record`.
- [ ] `allowed_adapters` contains strictly approved adapter IDs (`segel-baseline-adapter/v1`).
- [ ] `witness_cosignature_count` set to required quorum (>= 1).
- [ ] `canary_required_count` set to designated canary threshold.
- [ ] `freshness_mode` set to `"strict"` for fail-closed epoch checks.

---

## 6. Directory Structure & Path Provisioning

Provision the required directories with appropriate access controls on each node:

### Release Desk / Build Node:
```
/var/lib/segel/
├── ledger.db              # SQLite transparency ledger database
├── keys/                  # Secure private keys
└── artifacts/             # Staged bundle packages and passports
```

### Receiver Nodes (Canary & General):
```
/opt/segel-target/
├── config/                # Target deployment directory (files set to 0o444)
├── .staging/              # Atomic staging directory
├── .backup/               # Rollback backup cache
├── state/                 # Monotonic sequence & journal tracking
│   └── receiver_state.json
└── trust/
    ├── trust_root.json    # Transferred out-of-band
    └── policy.json        # Transferred out-of-band
```

- [ ] Staging and backup roots reside within or alongside `deploy_root`.
- [ ] Ensure disk quotas and write permissions are properly configured for the `segel` service user.

---

## 7. Network & Port Allocations

Ensure firewalls and reverse proxies are configured for designated ports:

| Service | Port | Binding | Protocol | Inbound Allowed From |
|:---|:---:|:---:|:---:|:---|
| **Release Desk UI** | `8000` | `127.0.0.1` or Internal VPN | HTTP / HTTPS | Authorized admin workstations |
| **Canary Unit 1** | `8001` | Internal Subnet | HTTP / HTTPS | Release Desk / CI dispatch |
| **Canary Unit 2** | `8002` | Internal Subnet | HTTP / HTTPS | Release Desk / CI dispatch |
| **Witness Daemon** | `8003` | Internal Subnet | HTTP / HTTPS | Transparency Ledger service |
| **Ollama AI (Optional)**| `11434`| `127.0.0.1` | HTTP | Inspector service only |
| **Offline General Unit**| None | **Disconnected** | Physical / USB | No network access permitted |

- [ ] Ports verified and firewall rules applied.
- [ ] Public internet access blocked on all control plane ports.

---

## 8. Offline Receiver Provisioning (Air-Gap Procedure)

To provision a truly offline Receiver node:

1. Format a dedicated physical USB drive or write-once optical disc (CD/DVD-R).
2. Copy the following artifacts to the media:
   - `trust_root.json`
   - `policy.json`
   - `receiver.priv.json` (for the specific unit)
   - SEGEL wheel package (`segel-0.1.0-py3-none-any.whl`) and Python dependencies.
3. Physically mount the media on the offline machine.
4. Install SEGEL offline:
   ```bash
   pip install --no-index --find-links=/media/usb/wheels segel
   ```
5. Initialize the offline receiver state directory:
   ```bash
   segel-receiver status --state-dir /opt/segel-target/state
   ```

- [ ] Media verified hash-consistent prior to air-gap transfer.
- [ ] Network cables physically disconnected / wireless interfaces disabled on receiver.

---

## 9. Pre-Flight Verification Checklist

Run these commands prior to declaring the environment ready:

- [ ] **Run Core Self-Test**:
  ```bash
  python -m pytest tests/adversarial/test_adversarial.py
  ```
- [ ] **Verify Approver Threshold Enforcement**:
  Attempt an approval with a single signature when 2 are required; confirm `THRESHOLD_NOT_MET` is raised.
- [ ] **Verify Anti-Rollback Monotonicity**:
  Attempt deploying sequence `1` after sequence `2`; confirm `SEQUENCE_REPLAY` is raised.
- [ ] **Verify Read-Only Enforcement**:
  Check that deployed configuration files have mode `0o444` (`-r--r--r--`).

