# SEGEL Cryptographic Key Management & Ceremony Guide

**Target Milestone**: SEGEL Version 0.1.0-MVP  
**Classification**: Cryptographic Architecture & Security Operations  
**Author**: Application Security Engineer & Cryptographic Officer  
**Date**: November 3, 2026  

---

## 1. Executive Summary & Security Principles

SEGEL enforces a strict zero-trust operational doctrine: **"No Evidence, No Deployment."** Every transition in the release lifecycle is cryptographically attested using standard **RFC 8032 Ed25519** digital signatures wrapped in **Dead Simple Signing Envelope (DSSE)** attestations with **RFC 8785 Canonical JSON** serialization.

### Fundamental Key Management Principles
1. **Separation of Duties (SEC-001 & SEC-002)**:
   - The **Release Author** key can NEVER participate in the Approver quorum.
   - The **Builder** key identity MUST be distinct from the Release Author key identity.
2. **Untrusted Release Desk**:
   - The Release Desk web dashboard (Zone Z3) NEVER holds private signing keys. All signing takes place in dedicated services, worker nodes, or air-gapped approver workstations.
3. **Restricted Storage (SEC-016 & SEC-026)**:
   - Private key files MUST be restricted to owner-only permissions (`0o600` on POSIX; restricted ACLs on Windows).
   - In production (v2.1+), private keys transition to FIPS 140-2 Level 3 Hardware Security Modules (HSMs) or YubiKey PIV tokens.
4. **Fail-Closed Revocation**:
   - A revoked key ID included in `trust_root.json` or `trust_snapshot.json` triggers immediate, irrevocable rejection of any future attestations from that key ID.

---

## 2. Complete Inventory of Cryptographic Keys

The SEGEL MVP requires **11 distinct Ed25519 keypairs** across 7 operational roles:

| Key Role | Key Identifier Name | Algorithm | Minimum Quorum | Primary Location | Purpose / Responsibility |
|:---|:---|:---:|:---:|:---|:---|
| **Release Author** | `author.priv.json` | Ed25519 | 1 | Developer workstation / CI | Signs the release `manifest.json` (`manifest_envelope`). |
| **Builder Worker** | `builder.priv.json` | Ed25519 | 1 | Isolated build server | Generates deterministic tar.gz bundle & signs Origin provenance. |
| **Inspector Signer**| `inspector.priv.json` | Ed25519 | 1 | Policy inspection host | Extracts capabilities, runs policy engine, signs Inspect attestation. |
| **Security Approver**| `approver_sec.priv.json`| Ed25519 | 2-of-3 | Air-gapped workstation (group-0)| Reviews QR payload, co-authorizes release for canary deployment. |
| **Operations Approver**|`approver_ops.priv.json`| Ed25519 | 2-of-3 | Air-gapped workstation (group-1)| Operations sign-off; satisfies multi-group approval threshold. |
| **QA Approver** | `approver_qa.priv.json` | Ed25519 | 2-of-3 | Air-gapped workstation (group-0)| Secondary security/QA approver for quorum redundancy. |
| **Ledger Signer** | `ledger.priv.json` | Ed25519 | 1 | Transparency ledger host | Signs Merkle checkpoints (`size` + `root_hash`) on entry append. |
| **Witness Cosigner**| `witness.priv.json` | Ed25519 | 1 | Independent witness node | Cosigns checkpoints after verifying consistency proofs; detects forks. |
| **Canary Unit 1** | `canary_1.priv.json` | Ed25519 | 1 | Staging/Canary host 1 | Signs deployment receipt after local preflight and health check. |
| **Canary Unit 2** | `canary_2.priv.json` | Ed25519 | 1 | Staging/Canary host 2 | Signs deployment receipt after local preflight and health check. |
| **General Receiver**| `receiver_general.priv.json`| Ed25519 | 1 | Offline production node | Offline unit; verifies general passport, signs final receipt. |

---

## 3. Key Generation & Formats

### 3.1 Key ID Derivation (SEC-033)
Per PRD v2.0 §13, every key's public identifier is deterministically computed as the lowercase hexadecimal SHA-256 digest of its raw 32-byte Ed25519 public key:
$$\text{key\_id} = \text{SHA-256}(\text{raw\_32\_byte\_public\_key})$$

### 3.2 Private Key Storage Format
Private keys for pilot deployment are stored in structured JSON files with restricted permissions:
```json
{
  "key_id": "bf88fe4a3affbe2a...",
  "algorithm": "ed25519",
  "role": "author",
  "group": "default",
  "private_key_hex": "4a7f...",
  "public_key_b64": "v4j+Sj..."
}
```

### 3.3 Public Key Storage Format (`*.pub.json`)
Public keys contain no secrets and are distributed freely or embedded into `trust_root.json`:
```json
{
  "key_id": "bf88fe4a3affbe2a...",
  "algorithm": "ed25519",
  "role": "author",
  "group": "default",
  "public_key_b64": "v4j+Sj..."
}
```

---

## 4. Automated Key Generation Tooling

To generate a complete, consistent synthetic or pilot test key hierarchy with associated `trust_root.json` and `policy.json`, run:

```bash
python scripts/init_keys.py --output-dir lab/keys --trust-dir lab/trust --mode synthetic
```

### Script Actions:
1. Calls the OS Cryptographically Secure Pseudorandom Number Generator (CSPRNG via OpenSSL).
2. Generates all 11 role-differentiated keypairs.
3. Automatically sets file permissions to `0o600` on private keys and `0o700` on the key directory.
4. Assembles canonical `trust_root.json` containing all public keys, role definitions, and thresholds.
5. Assembles `policy.json` with `freshness_mode = "strict"` and 2-of-3 approver threshold.

---

## 5. Storage Security & File Permissions

### 5.1 POSIX / Linux Production Hosts
Execute the following commands on every host storing private keys:
```bash
# Restrict key directory
chmod 700 /etc/segel/keys
chown -R segel:segel /etc/segel

# Restrict individual private keys
chmod 600 /etc/segel/keys/*.priv.json

# Public keys and trust metadata remain world-readable
chmod 644 /etc/segel/keys/*.pub.json
chmod 644 /etc/segel/trust/*.json
```

### 5.2 Windows Production Hosts (PowerShell)
Execute the following script to remove inherited permissions and grant exclusive access to the service account and Administrators:
```powershell
$acl = Get-Acl "C:\etc\segel\keys\*.priv.json"
$acl.SetAccessRuleProtection($true, $false)
$adminRule = New-Object System.Security.AccessControl.FileSystemAccessRule("Administrators","FullControl","Allow")
$segelRule = New-Object System.Security.AccessControl.FileSystemAccessRule("SYSTEM","FullControl","Allow")
$acl.AddAccessRule($adminRule)
$acl.AddAccessRule($segelRule)
Set-Acl "C:\etc\segel\keys\*.priv.json" $acl
```

---

## 6. Key Lifecycle Operations

### 6.1 Trust Root Registration (`trust_root.json`)
The trust root binds public keys to roles:
```json
{
  "root_version": 1,
  "keys": [
    {
      "key_id": "bf88fe4a...",
      "public_key_b64": "v4j+S...",
      "role": "author",
      "group": "default",
      "status": "active"
    }
  ],
  "roles": [
    {
      "role": "approver",
      "threshold": 2,
      "group_minimums": {
        "group-0": 1,
        "group-1": 1
      }
    }
  ]
}
```

### 6.2 Key Rotation Procedure
1. Generate the new keypair using `generate_keypair()`.
2. Add the new public key record to `trust_root.json` with `status: "active"`.
3. Increment `root_version` in `trust_root.json`.
4. Distribute the updated `trust_root.json` to all nodes (via out-of-band Trust Update Package for offline units).
5. Deploy the new private key to the designated signing node.
6. Once all nodes have accepted the new trust root version, mark the old key `status: "deprecated"` or `"revoked"`.

### 6.3 Emergency Key Revocation Procedure
1. Create a Trust Update Package containing a new `TrustSnapshot`:
   - Add the compromised `key_id` to `revoked_keys`.
   - Increment `epoch` (e.g., from `1` to `2`).
2. Update `trust_root.json` marking the compromised key as `status: "revoked"`.
3. Distribute the Trust Update Package to all canary and offline receivers.
4. Any attempt to verify a release signed by the revoked key will immediately fail closed with:
   - `KEY_REVOKED`: Key explicitly listed in revocation table.
   - `EPOCH_STALE`: If an attacker attempts to replay an older trust root.

---

## 7. Key Ceremony Runbook (For Controlled Pilot Launch)

> [!IMPORTANT]
> Operational pilot keys must NEVER be generated automatically or stored on development machines. A formal key ceremony must be conducted before pilot commissioning.

### Ceremony Protocol:
1. **Witnesses Present**: Lead Architect, Security Auditor, Operations Lead.
2. **Clean Air-Gapped Machine**: Boot from a live Linux USB (e.g. Ubuntu live CD) with no network interfaces connected.
3. **Execution**:
   ```bash
   python3 scripts/init_keys.py --output-dir /mnt/secure_usb/keys --trust-dir /mnt/secure_usb/trust --mode pilot
   ```
4. **Key Separation**:
   - `author.priv.json` copied to Author CI/station USB only.
   - `approver_*.priv.json` copied to distinct Approver physical USBs.
   - `ledger.priv.json` provisioned directly to Ledger host.
   - `witness.priv.json` provisioned directly to Witness host.
   - All private keys purged from temporary air-gapped memory.
5. **Public Trust Distribution**:
   - `trust_root.json` and `policy.json` published to repository `/etc/segel/trust/` and signed by the ceremony witnesses.

