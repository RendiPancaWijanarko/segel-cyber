# SEGEL Cryptographic Key Provisioning & Trust Ceremony Procedure

**Target Milestone**: SEGEL MVP Version 0.1.0-MVP  
**Audience**: Cryptographic Officers, AppSec Engineers, and Trust Custodians  
**Authoritative Reference**: PRD v2.0 §13/§16, TAS §8.10, Security Principles SEC-001–SEC-004  
**Status**: **MANDATORY CEREMONY RUNBOOK**

---

## 1. Scope & Security Principles

This document defines the formal operational procedure for generating, securing, and distributing the **11-key cryptographic hierarchy** for SEGEL.

### Foundational Principles
1. **Separation of Duties (SEC-001, SEC-002, SEC-003)**:
   - The Manifest Author cannot act as Builder.
   - The Manifest Author is strictly excluded from acting as an Approver.
   - The Ledger signer and Witness cosigner must be independent.
2. **Multi-Party Approver Quorum**:
   - Approvals require at least 2 distinct signatures representing at least 1 from `group-0` (Security/QA) and at least 1 from `group-1` (Operations).
3. **No Centralized Key Generation**:
   - For pilot and production environments, each private key must be generated locally on its own designated machine or in an air-gapped ceremony.
4. **Zero-Trust Distribution**:
   - Private keys never leave their respective hosts.
   - Public keys are assembled into a canonical `trust_root.json` and verified via SHA-256 fingerprints before deployment.

---

## 2. The 11-Key Hierarchy & Role Specifications

| # | Role Identifier | Assigned Host / System | Group | Threshold Rule | Purpose |
|---|---|---|:---:|:---:|---|
| 1 | `author` | Developer Workstation | `default` | 1 | Signs release manifest; excluded from approver quorum. |
| 2 | `builder` | CI Build Server | `ci-pipeline` | 1 | Builds release package; signs SLSA-aligned Origin provenance (Stamp 1). |
| 3 | `inspector_signer` | Policy Inspection Node | `sec-engine` | 1 | Signs Inspect attestation with deterministic verdict (Stamp 2). |
| 4 | `approver` (Security) | Security Officer Terminal | `group-0` | 2-of-3 Quorum | Reviews diff & Inspect attestation; signs Approve envelope (Stamp 3). |
| 5 | `approver` (Operations)| Ops Lead Terminal | `group-1` | 2-of-3 Quorum | Operations approval; cross-group threshold enforcement. |
| 6 | `approver` (QA / Lead) | QA Lead Terminal | `group-0` | 2-of-3 Quorum | Alternate quorum member; satisfies 2-of-3 threshold. |
| 7 | `ledger` | Transparency Ledger Host | `transparency` | 1 | Appends to RFC 6962 Merkle tree; signs checkpoints (Stamp 4). |
| 8 | `witness` | Independent Witness Host | `independent` | 1 | Cosigns tree checkpoints (detects ledger split-view / fork attacks). |
| 9 | `receiver` (Canary 1) | Canary Host 1 | `canary-fleet` | 1 | Deploys candidate; signs health test receipt (Stamp 5). |
| 10 | `receiver` (Canary 2) | Canary Host 2 | `canary-fleet` | 1 | Deploys candidate; signs health test receipt (Stamp 5). |
| 11 | `receiver` (General) | Offline General Unit | `prod-fleet` | 1 | Verifies general passport; deploys promoted release; signs receipt. |

---

## 3. Phase 1: Local Key Generation Protocol

On each assigned machine, run the following command to generate that host's specific keypair:

```bash
python -c "
from segel_core.crypto.ed25519 import generate_keypair, export_public_key
from cryptography.hazmat.primitives.serialization import Encoding, PrivateFormat, NoEncryption
import json, pathlib, sys

role = sys.argv[1]
group = sys.argv[2] if len(sys.argv) > 2 else 'default'

out_dir = pathlib.Path('/etc/segel/keys')
out_dir.mkdir(parents=True, exist_ok=True, mode=0o700)

kp = generate_keypair()
priv_bytes = kp.private_key.private_bytes(Encoding.Raw, PrivateFormat.Raw, NoEncryption())
priv_hex = priv_bytes.hex()
pub_b64 = export_public_key(kp.public_key_bytes)

priv_data = {
    'key_id': kp.key_id,
    'algorithm': 'ed25519',
    'role': role,
    'group': group,
    'private_key_hex': priv_hex,
    'public_key_b64': pub_b64
}

pub_data = {
    'key_id': kp.key_id,
    'algorithm': 'ed25519',
    'role': role,
    'group': group,
    'public_key_b64': pub_b64
}

priv_file = out_dir / f'{role}.priv.json'
pub_file = out_dir / f'{role}.pub.json'

priv_file.write_text(json.dumps(priv_data, indent=2), encoding='utf-8')
priv_file.chmod(0o600)

pub_file.write_text(json.dumps(pub_data, indent=2), encoding='utf-8')
pub_file.chmod(0o644)

print(f'[+] Generated {role} key: {kp.key_id}')
" <ROLE_NAME> <GROUP_NAME>
```

### Role Command Examples:
- Author: `python ... author default`
- Builder: `python ... builder ci-pipeline`
- Inspector: `python ... inspector_signer sec-engine`
- Security Approver: `python ... approver group-0`
- Operations Approver: `python ... approver group-1`
- QA Approver: `python ... approver group-0`
- Ledger Signer: `python ... ledger transparency`
- Witness Cosigner: `python ... witness independent`
- Canary 1: `python ... receiver canary-fleet`
- Canary 2: `python ... receiver canary-fleet`
- General Unit: `python ... receiver prod-fleet`

---

## 4. Phase 2: Trust Root Assembly & Canonicalization

Once all 11 public key files (`*.pub.json`) have been exported to the trust coordinator:

1. Place public keys in `pub_keys/`:
   ```text
   pub_keys/
   ├── author.pub.json
   ├── builder.pub.json
   ├── inspector.pub.json
   ├── approver_sec.pub.json
   ├── approver_ops.pub.json
   ├── approver_qa.pub.json
   ├── ledger.pub.json
   ├── witness.pub.json
   ├── canary_1.pub.json
   ├── canary_2.pub.json
   └── receiver_general.pub.json
   ```

2. Compile `trust_root.json` and `policy.json`:
   ```bash
   python -c "
   import json, pathlib
   from segel_core.schemas.trust import KeyRecord, RoleThreshold, TrustRoot, VerificationPolicy
   from segel_core.canonical import canonical_json

   key_records = []
   for p in sorted(pathlib.Path('pub_keys').glob('*.pub.json')):
       d = json.loads(p.read_text(encoding='utf-8'))
       key_records.append(KeyRecord(
           key_id=d['key_id'],
           public_key_b64=d['public_key_b64'],
           role=d['role'],
           group=d['group'],
           status='active'
       ))

   roles = [
       RoleThreshold(role='author', threshold=1),
       RoleThreshold(role='builder', threshold=1),
       RoleThreshold(role='inspector_signer', threshold=1),
       RoleThreshold(role='approver', threshold=2, group_minimums={'group-0': 1, 'group-1': 1}),
       RoleThreshold(role='ledger', threshold=1),
       RoleThreshold(role='witness', threshold=1),
       RoleThreshold(role='receiver', threshold=1),
   ]

   trust_root = TrustRoot(root_version=1, keys=key_records, roles=roles)
   policy = VerificationPolicy(
       policy_version=1,
       approval_threshold=2,
       approval_groups={'group-0': 1, 'group-1': 1},
       canary_required_count=2,
       witness_cosignature_count=1,
       freshness_mode='strict'
   )

   pathlib.Path('/etc/segel/trust_root.json').write_bytes(canonical_json(trust_root))
   pathlib.Path('/etc/segel/policy.json').write_bytes(canonical_json(policy))
   print('[+] Trust root and policy successfully compiled.')
   "
   ```

3. Calculate and publish SHA-256 digests:
   ```bash
   sha256sum /etc/segel/trust_root.json
   sha256sum /etc/segel/policy.json
   ```

---

## 5. Phase 3: Out-of-Band Trust Root Distribution

1. Copy `trust_root.json` and `policy.json` to removable media (USB drive).
2. Physically transport to each of the 5+ participating nodes.
3. Install to `/etc/segel/trust_root.json` and `/etc/segel/policy.json`.
4. Verify SHA-256 fingerprint on every node:
   ```bash
   sha256sum /etc/segel/trust_root.json
   ```
   **Acceptance Gate**: The fingerprint must match the ceremony transcript character-for-character. If a fingerprint differs, the node must not participate in the release lifecycle.

---

## 6. Phase 4: Key Revocation & Epoch Advancement Runbook

If a private key is suspected of being compromised during pilot operations:

1. **Update Key Status**: Mark the compromised key's record as `"revoked"` in `trust_root.json`:
   ```json
   {
     "key_id": "<compromised_key_id>",
     "status": "revoked"
   }
   ```
2. **Increment Root Version & Epoch**:
   - Increment `root_version` in `trust_root.json` (e.g. `root_version: 2`).
   - Create updated `TrustSnapshot` with `epoch = epoch + 1`.
3. **Re-canonicalize & Re-hash**:
   - Re-serialize using RFC 8785 Canonical JSON.
   - Compute new SHA-256 digest.
4. **Physical Deployment**:
   - Transport updated `trust_root.json` to all nodes via physical media.
   - Run `segel-receiver status` on all receivers to confirm epoch advancement.
   - Any subsequently presented releases bearing signatures from the revoked key will fail validation (`REVOKED_KEY_ERROR`).

