# SEGEL Security Model

## Founding Principle

**NO EVIDENCE, NO DEPLOYMENT.**

Every release must carry five independently verifiable security stamps. A Receiver must independently verify all evidence using locally available trust information and must be capable of operating offline.

## Threat Model

SEGEL assumes:

1. **Network compromise is possible.** Distribution channels may be tampered with.
2. **Individual actors may be compromised.** No single role can unilaterally deploy.
3. **The Release Desk is untrusted.** It orchestrates but cannot sign or bypass checks.
4. **AI is untrusted.** It provides advisory information only — no signing, no deploy permissions.
5. **Storage is not a trust boundary.** SQLite triggers are guard rails, not immutability guarantees (SEC-018). Tamper evidence comes from Merkle proofs and signed checkpoints.

## Security Controls

### Cryptographic Controls

| Control | Requirement | Implementation |
|---------|-------------|----------------|
| SEC-001 | Author must not approve own release | `verify_threshold` excludes author key_id |
| SEC-004 | Release Desk must not hold private keys | Signing in separate processes; keys never loaded by app.py |
| SEC-013 | AI must not hold signing keys | AI advisory is a pure function with no key access |
| SEC-017 | Deterministic packaging | Fixed mtime, uid/gid, sorted paths in tar.gz |
| SEC-018 | No SQLite-based immutability claims | Merkle tree + signed checkpoints provide tamper evidence |
| SEC-023 | Path validation | Reject traversal, absolute paths, null bytes, forbidden extensions |
| SEC-025 | No executable deployment | `.exe`, `.dll`, `.sh`, `.py`, etc. are forbidden |
| SEC-031 | RFC 6962 Merkle tree | `leaf = SHA-256(0x00 ∥ data)`, `node = SHA-256(0x01 ∥ left ∥ right)` |
| SEC-033 | Key identity | `key_id = SHA-256(raw_32_byte_public_key)` |
| SEC-037 | CSPRNG for key generation | Uses OS CSPRNG via `cryptography` library |

### Access Controls

| Control | Enforcement |
|---------|-------------|
| Author ≠ Approver | Author key_id excluded from approval threshold count |
| Approval threshold | 2-of-3 approvers from at least 2 groups required |
| Sequence monotonicity | Receiver rejects `seq ≤ highest_sequence[release_id]` |
| Epoch enforcement | Passport `min_epoch` must be ≤ receiver's current epoch |
| Witness independence | Witness has separate key; verifies consistency proofs |

### Fail-Closed Behaviour

All security-critical operations fail closed:

- **Invalid signature** → envelope verification returns 0 valid keys → deployment blocked
- **Modified content** → SHA-256 digest mismatch → `DigestMismatchError` → deployment aborted
- **Missing stamps** → passport verification marks stamp as INVALID → INELIGIBLE
- **Threshold not met** → `ThresholdNotMetError` → pipeline halted
- **Consistency proof failure** → `ProofInvalidError` → witness refuses to cosign
- **Fork detected** → `CheckpointForkError` → witness alerts operator
- **State corruption** → `StateCorruptError` → receiver enters recovery mode
- **AI failure** → `ai_status = "failed"` recorded; deterministic verdict unchanged

### Security Invariants & Limitations

Integrity and authenticity guarantees in SEGEL are cryptographic invariants enforced by offline deterministic verification (RFC 8032 Ed25519 DSSE envelopes, RFC 6962 SHA-256 Merkle inclusion proofs, and Pre-Authentication Encoding bindings). These invariants hold strictly within the defined threat model and are verified by the 310-test automated suite. They do not constitute unconditional system guarantees against out-of-scope hardware faults or host environment compromise.

### What SEGEL Does NOT Guarantee

1. **SEGEL does not prove software is safe.** It proves that specific evidence exists and has not been tampered with.
2. **Offline revocation has a freshness limit.** A receiver operating offline cannot learn about key revocations that occurred after its last trust update.
3. **The deterministic policy engine is pattern-based.** It detects *known capability signatures*, not all possible behaviours.
4. **AI advisory is probabilistic.** AI findings are informational; they cannot downgrade a deterministic REJECT but may miss issues.

## Evidence Chain

Every attestation carries a **binding block** that cryptographically ties it to the release:

```json
{
  "stamp": "origin",
  "subject": {
    "release_id": "BASELINE-UNIT-42",
    "sequence": 1,
    "manifest_sha256": "abc123..."
  },
  "trust_root_version": 1,
  "policy_version": 1,
  "evidence_id": "uuid-v4"
}
```

The binding block ensures that evidence cannot be transplanted between releases.

## Verification Pipeline

When a Receiver receives a Release Passport, it performs these checks:

1. **Schema validation** — passport structure matches expected schema version
2. **Manifest verification** — valid DSSE envelope, author key in trust root
3. **Origin verification** — valid DSSE envelope, builder key in trust root, binding match
4. **Inspect verification** — valid DSSE envelope, inspector key in trust root, binding match
5. **Approve verification** — valid DSSE envelope, threshold met with author excluded, binding match
6. **Record verification** — Merkle inclusion proof valid against signed checkpoint
7. **Test verification** (general only) — canary receipts present and signed
8. **Anti-rollback** — sequence > highest_sequence for this release_id
9. **Epoch check** — passport min_epoch ≤ receiver epoch
10. **Eligibility classification** — ELIGIBLE_CANARY, ELIGIBLE_GENERAL, or INELIGIBLE

## Trust Metadata

```
TrustRoot (v1)
├── keys: [{key_id, public_key_b64, role, group, status}]
├── roles: [{role, threshold, group_minimums}]
└── root_version: monotonically increasing

VerificationPolicy (v1)
├── required_stamps: [origin, inspect, approve, record, test]
├── approval_threshold: 2
├── approval_groups: {group-0: 1, group-1: 1}
├── canary_required_count: 2
└── witness_cosignature_count: 1

TrustSnapshot
└── epoch: monotonically increasing
```

Trust metadata is distributed out-of-band to receivers. Version monotonicity is enforced — a receiver will not accept trust metadata with a lower version than what it already has.

