# SEGEL Manual Intervention Checklist for Controlled Pilot

**Auditing Authority**: Technical Implementation Lead & Application Security Engineer  
**Target Milestone**: SEGEL Controlled Pilot Preparation  
**Document Purpose**: Definitive list of human-authorized actions, physical interventions, and operational approvals  
**Status**: **PENDING HUMAN EXECUTION PRIOR TO LIVE PILOT TRAFFIC**

---

## 1. Overview & Scope of Human Intervention

All software implementation, dependency resolution, database initialization, Docker Compose validation, and automated testing tasks have been executed and verified automatically.

However, per security invariants SEC-001 through SEC-004 and the Zero-Trust mandate:
> [!CRITICAL]
> Cryptographic keys, physical network disconnects, human approver quorums, and hardware provisioning cannot and must not be simulated or assumed by an automated agent. The following actions strictly require human intervention.

No secrets, private keys, or passwords should ever be entered into this chat or shared in transcripts. Follow the local procedures detailed below.

---

## 2. Action Item 1: Distributed Cryptographic Key Ceremony

### Exactly What Must Be Done
Execute a distributed key ceremony across separate workstations to generate real pilot private keys. **Never generate all pilot keys on a single workstation.**

### Systems & Files Involved
- **Host Workstations**: Dedicated operational machines for Author, Builder, Inspector, Approver Sec, Approver Ops, Approver QA, Ledger, Witness, Canary 1, Canary 2, and General Receiver.
- **Target File Paths**:
  - Private Key: `/etc/segel/keys/<role>.priv.json` (mode `0o600`)
  - Public Key: `/etc/segel/keys/<role>.pub.json` (mode `0o644`)

### Required Data Format
```json
{
  "key_id": "<64-char hex SHA-256 of public key>",
  "algorithm": "ed25519",
  "role": "<author|builder|inspector_signer|approver|ledger|witness|receiver>",
  "group": "<default|group-0|group-1>",
  "private_key_hex": "<64-char hex raw 32-byte Ed25519 private key>",
  "public_key_b64": "<44-char base64 Ed25519 raw public key>"
}
```

### Step-by-Step Procedure
1. On each designated machine, generate an Ed25519 keypair:
   ```bash
   python -c "
   from segel_core.crypto.ed25519 import generate_keypair, export_public_key
   from cryptography.hazmat.primitives.serialization import Encoding, PrivateFormat, NoEncryption
   import json, pathlib

   kp = generate_keypair()
   priv_hex = kp.private_key.private_bytes(Encoding.Raw, PrivateFormat.Raw, NoEncryption()).hex()
   pub_b64 = export_public_key(kp.public_key_bytes)
   
   pathlib.Path('/etc/segel/keys').mkdir(parents=True, exist_ok=True, mode=0o700)
   pathlib.Path('/etc/segel/keys/<role>.priv.json').write_text(json.dumps({
       'key_id': kp.key_id, 'algorithm': 'ed25519', 'role': '<role>', 'group': '<group>',
       'private_key_hex': priv_hex, 'public_key_b64': pub_b64
   }, indent=2))
   pathlib.Path('/etc/segel/keys/<role>.pub.json').write_text(json.dumps({
       'key_id': kp.key_id, 'algorithm': 'ed25519', 'role': '<role>', 'group': '<group>',
       'public_key_b64': pub_b64
   }, indent=2))
   "
   ```
2. Restrict permissions:
   ```bash
   chmod 600 /etc/segel/keys/*.priv.json
   chmod 644 /etc/segel/keys/*.pub.json
   ```
3. Export only the public key files (`*.pub.json`) to the trust coordinator.

### Verification of Completion
```bash
ls -la /etc/segel/keys/
# Must show -rw------- for *.priv.json and -rw-r--r-- for *.pub.json
```

---

## 3. Action Item 2: Trust Root Compilation & Fingerprint Distribution

### Exactly What Must Be Done
Assemble the 11 public keys into a canonical `trust_root.json` and `policy.json`, compute their SHA-256 digests, and distribute them to all participating hosts via out-of-band verified media.

### Systems & Files Involved
- **Coordinator Workstation**: Machine compiling public keys.
- **All Participating Hosts**: `/etc/segel/trust_root.json` and `/etc/segel/policy.json`.

### Step-by-Step Procedure
1. Place all 11 public key files into a staging directory `pub_keys/`.
2. Compile canonical trust root:
   ```bash
   python -c "
   from segel_core.schemas.trust import KeyRecord, RoleThreshold, TrustRoot, VerificationPolicy
   from segel_core.canonical import canonical_json
   import json, pathlib

   keys = []
   for p in pathlib.Path('pub_keys').glob('*.pub.json'):
       d = json.loads(p.read_text())
       keys.append(KeyRecord(key_id=d['key_id'], public_key_b64=d['public_key_b64'], role=d['role'], group=d['group']))

   roles = [
       RoleThreshold(role='author', threshold=1),
       RoleThreshold(role='builder', threshold=1),
       RoleThreshold(role='inspector_signer', threshold=1),
       RoleThreshold(role='approver', threshold=2, group_minimums={'group-0': 1, 'group-1': 1}),
       RoleThreshold(role='ledger', threshold=1),
       RoleThreshold(role='witness', threshold=1),
       RoleThreshold(role='receiver', threshold=1),
   ]
   root = TrustRoot(root_version=1, keys=keys, roles=roles)
   policy = VerificationPolicy(policy_version=1, approval_threshold=2, approval_groups={'group-0': 1, 'group-1': 1}, canary_required_count=2, witness_cosignature_count=1)

   pathlib.Path('/etc/segel/trust_root.json').write_bytes(canonical_json(root))
   pathlib.Path('/etc/segel/policy.json').write_bytes(canonical_json(policy))
   "
   ```
3. Compute official SHA-256 digests and print them on paper or a physically verified signing transcript:
   ```bash
   sha256sum /etc/segel/trust_root.json
   sha256sum /etc/segel/policy.json
   ```
4. Copy `trust_root.json` and `policy.json` to every host (`/etc/segel/`).

### Verification of Completion
On each host, run:
```bash
sha256sum /etc/segel/trust_root.json /etc/segel/policy.json
# Ensure hash values match the printed ceremony transcript exactly.
```

---

## 4. Action Item 3: Hardware & Network Topology Verification

### Exactly What Must Be Done
Allocate and provision at least 5 distinct physical or virtual machines conforming to the pilot topology:

| Host Identifier | Assigned Role | Network Posture |
|---|---|---|
| `host-release-desk` | Release Desk & Transparency Ledger | Connected (Internal Management LAN) |
| `host-witness` | Independent Checkpoint Witness | Connected (Internal Management LAN) |
| `host-canary-1` | Canary Receiver Unit 1 | Air-gapped / Local Network Only |
| `host-canary-2` | Canary Receiver Unit 2 | Air-gapped / Local Network Only |
| `host-unit-3` | General Receiver (Production Staging) | **Strictly Air-gapped (Zero Network)** |

### Step-by-Step Procedure
1. On `host-unit-3`, physically unplug ethernet cables or disable the network interface:
   ```bash
   sudo ip link set eth0 down
   ```
2. Verify routing table is completely empty:
   ```bash
   ip route
   # Output must be completely blank.
   ```
3. Attempt external ping:
   ```bash
   ping -c 1 8.8.8.8
   # Must fail: Network is unreachable.
   ```

---

## 5. Action Item 4: Air-Gapped Physical Removable Media

### Exactly What Must Be Done
Prepare dedicated, formatted USB flash drives for physical transfer of candidate releases, passports, and signed receipts.

### Requirements & Specifications
- Format: ext4 or FAT32.
- Hardware: USB flash drives with a physical write-protect hardware switch are strongly recommended for air-gap data ingestion.
- Labeling: Clearly label drives:
  - `USB-STAGE-01`: Candidate releases & candidate passports.
  - `USB-RECEIPT-01`: Canary signed receipts returning to Release Desk.
  - `USB-PROD-01`: General release packages & general passports.

### Verification of Completion
```bash
lsblk
# Verify correct mount permissions and filesystem consistency.
```

---

## 6. Action Item 5: Human Role & Quorum Assignment

### Exactly What Must Be Done
Formally designate the operational personnel fulfilling the Segregation of Duties (SEC-001/SEC-002/SEC-003):

| Operational Role | Assigned Individual | Organization / Group | Assigned Key ID |
|---|---|---|---|
| **Manifest Author** | Configuration Engineer | Release Team | |
| **Builder Operator** | CI/CD Engineer | Infrastructure | |
| **Security Approver** | AppSec Lead | Security (`group-0`) | |
| **Operations Approver**| Ops Lead | SRE (`group-1`) | |
| **QA Approver** | QA Lead | Quality Assurance (`group-0`) | |
| **Witness Operator** | Independent Auditor | Trust Operations | |

### Verification Rule
Confirm that the Manifest Author's name and Key ID do not match any of the designated Approvers.

---

## 7. Action Item 6: Optional AI Advisory Service (Ollama)

### Exactly What Must Be Done
If natural-language security analysis of configuration diffs is desired during the pilot, configure access to an Ollama server running `llama3:8b`:
1. Start Ollama on the designated host: `ollama run llama3:8b`.
2. Update `.env` on `host-release-desk`:
   ```env
   OLLAMA_HOST=http://127.0.0.1:11434
   OLLAMA_MODEL=llama3:8b
   ```
3. If Ollama is not deployed, leave the default setting; the deterministic policy inspector will automatically run in standalone mode with `ai_status: skipped`.

---

## 8. Pilot Authorization Sign-Off

Upon completion of Action Items 1 through 5, the Lead Auditor and Operations Lead must sign below to authorize pilot release traffic:

- **Security Lead Approval**: ___________________________ Date: ____________
- **Operations Lead Approval**: _________________________ Date: ____________
- **Release Authority**: ________________________________ Date: ____________

