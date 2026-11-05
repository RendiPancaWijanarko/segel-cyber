# SEGEL Architecture

> Sistem Edar Gelar Elektronik Lapis-ganda — Secure Configuration & Release Distribution Platform

## Overview

SEGEL implements a **security-core-first modular monolith** architecture. Every release must carry five independently verifiable security stamps before deployment is permitted.

```
                    ┌─────────────────────────────────────────────┐
                    │              SEGEL Architecture              │
                    ├─────────────────────────────────────────────┤
                    │                                             │
 ┌──────────┐       │  ┌─────────┐   ┌──────────┐   ┌─────────┐ │
 │  Author   │──────┼─▶│ Builder │──▶│Inspector │──▶│Approver │ │
 │  Signer   │      │  └────┬────┘   └────┬─────┘   └────┬────┘ │
 └──────────┘       │       │              │              │      │
                    │       ▼              ▼              ▼      │
                    │  ┌─────────────────────────────────────┐   │
                    │  │       Transparency Ledger            │   │
                    │  │    (Merkle log + signed checkpoints) │   │
                    │  └─────────────┬───────────────────────┘   │
                    │                │                            │
                    │       ┌────────┴────────┐                  │
                    │       │    Witness       │                  │
                    │       │  (cosigner)      │                  │
                    │       └─────────────────┘                  │
                    │                                             │
                    │  ┌──────────────────────────────────────┐  │
                    │  │      Passport Assembler              │  │
                    │  │  (candidate & general passports)     │  │
                    │  └────────────────┬─────────────────────┘  │
                    │                   │                         │
                    └───────────────────┼─────────────────────────┘
                                        │
                    ┌───────────────────┼─────────────────────────┐
                    │                   ▼                         │
                    │  ┌────────────────────────────────────┐    │
                    │  │     Promotion Controller           │    │
                    │  │  (canary health → general release) │    │
                    │  └─────────────┬──────────────────────┘    │
                    │                │                            │
                    │     ┌──────────┼──────────┐                │
                    │     ▼          ▼          ▼                │
                    │  ┌──────┐  ┌──────┐  ┌──────┐            │
                    │  │Can-1 │  │Can-2 │  │Unit-3│            │
                    │  │(rcvr)│  │(rcvr)│  │(rcvr)│            │
                    │  └──────┘  └──────┘  └──────┘            │
                    │     Offline Receivers                      │
                    └────────────────────────────────────────────┘
```

## Component Zones

| Zone | Component | Trust Level | Description |
|------|-----------|-------------|-------------|
| Z1 | SEGEL Core | Trusted | Shared crypto, serialization, schemas, verification |
| Z2 | Signing Processes | Isolated | Author, Builder, Inspector, Approver signers |
| Z3 | Release Desk | Untrusted | Web UI orchestrator — never holds private keys |
| Z4 | Policy Engine | Trusted | Deterministic capability extraction + policy rules |
| Z5 | AI Sandbox | Untrusted | Optional Ollama advisory — no keys, no deploy perms |
| Z6 | Transparency Ledger | Trusted | Append-only Merkle log with signed checkpoints |
| Z7 | Witness | Isolated | Independent checkpoint cosigner |
| Z8 | Passport Assembler | Trusted | Bundles all evidence into verifiable passports |
| Z9 | Receiver | Trusted | Offline passport verification + deployment |

## 5-Stamp Pipeline

```
  Origin    →    Inspect    →    Approve    →    Record    →    Test
  ┌────┐        ┌────────┐      ┌────────┐     ┌──────┐      ┌────┐
  │ 🏭 │───────▶│  🔍   │─────▶│  ✅   │────▶│  📜 │─────▶│ 🧪 │
  └────┘        └────────┘      └────────┘     └──────┘      └────┘
  Builder       Inspector       2-of-3         Merkle log    Canary
  signs         extracts        approvers      + witness     deploy
  provenance    capabilities    sign           cosign        + health
```

Each stamp is a DSSE-wrapped in-toto attestation signed by the designated role's Ed25519 key.

## Data Formats & Standards

| Standard | Usage |
|----------|-------|
| Ed25519 (RFC 8032) | All signing operations |
| DSSE | Envelope format for all attestations |
| in-toto Statement v1 | Attestation statement structure |
| SHA-256 | All hashing (content, keys, Merkle nodes) |
| RFC 6962 Merkle Tree | Transparency log leaf/node construction |
| RFC 9162 | Consistency proofs between checkpoints |
| C2SP tlog-checkpoint | Checkpoint format |
| Canonical JSON | Deterministic serialization (sorted keys, no whitespace) |

## Key Identity

Key identity = `SHA-256(raw_32_byte_public_key)` (SEC-033).

This is computed over the raw 32-byte Ed25519 public key bytes, not any encoded form.

## Module Map

```
src/
├── segel_core/              # Z1: Shared trusted library
│   ├── canonical.py         # Canonical JSON serialization
│   ├── errors.py            # 20 typed error codes
│   ├── crypto/
│   │   ├── ed25519.py       # Key generation, signing, verification
│   │   ├── dsse.py          # PAE, envelope creation, verification
│   │   └── hashing.py       # SHA-256, Merkle tree, proofs
│   ├── schemas/
│   │   ├── manifest.py      # Release manifest
│   │   ├── binding.py       # Binding block (evidence → release)
│   │   ├── attestation.py   # All 4 attestation predicates
│   │   ├── trust.py         # TrustRoot, VerificationPolicy, TrustSnapshot
│   │   ├── passport.py      # Release Passport + LedgerProof
│   │   ├── receipt.py       # Deployment receipt
│   │   └── checkpoint.py    # Ledger checkpoint (C2SP format)
│   └── verification/
│       ├── trust.py         # TrustContext — key/role lookup, revocation
│       └── passport.py      # Full passport verification (all 5 stamps)
├── builder/                 # Z2: Deterministic packaging + Origin
├── inspector/               # Z4: Capability extraction + policy
├── approver/                # Z2: Air-gapped multi-party approval
├── ledger/                  # Z6: Transparency log (SQLite + Merkle)
├── witness/                 # Z7: Checkpoint cosigner
├── passport/                # Z8: Passport assembler
├── promotion/               # Canary evaluation + promotion controller
├── receiver/                # Z9: Offline verification + deployment
│   └── adapter/
│       └── baseline.py      # 10-step deployment lifecycle
└── release_desk/            # Z3: FastAPI web application
    └── templates/           # Jinja2 + HTMX templates
```

## Security Boundaries

1. **Release Desk (Z3) NEVER holds private keys** — all signing happens in separate processes.
2. **AI (Z5) has NO signing keys and NO deployment permissions** — advisory only.
3. **Receiver verification works OFFLINE** — uses locally available trust information.
4. **All operations fail closed** — missing evidence blocks the pipeline.
5. **Evidence is cryptographically bound** — every attestation includes a binding block tying it to the release identity (release_id + sequence + manifest_sha256).

