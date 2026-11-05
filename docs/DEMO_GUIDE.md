# SEGEL MVP Demo Guide

## Quick Start

### Prerequisites

- Python 3.12+ (tested on 3.14.6)
- pip

### Installation

```bash
cd segel-cyber
pip install -e ".[dev]"
```

### Run the Full Demo

The demo script runs the complete 18-step release lifecycle with coloured console output:

```bash
python scripts/demo.py
```

This demonstrates:
1. Release creation and manifest generation
2. Author signing (separate signer)
3. Builder Origin provenance (SLSA-aligned)
4. Inspector capability extraction + policy evaluation
5. AI advisory (skipped in MVP)
6. Inspector Signer attestation
7. Approver review and signing (2-of-3 threshold, QR air-gapped transfer)
8. Ledger recording with Merkle proof
9. Witness cosigning with consistency proof
10. Canary deployment to 2 units with health receipts
11. Promotion Controller evaluation
12. General Release Passport assembly
13. Offline Receiver verification and deployment
14. Signed deployment receipt generation
15. Rejection of forged signatures (AT-001)
16. Rejection of modified content (AT-002)
17. Rejection of missing stamps (AT-003)
18. Rejection of author self-approval (AT-008)
19. Rejection of sequence replay (AT-012)

### Run Tests

```bash
# All tests (106 tests)
python -m pytest tests/ -v

# Unit tests only
python -m pytest tests/unit/ -v

# Integration lifecycle test
python -m pytest tests/integration/ -v

# Adversarial security tests
python -m pytest tests/adversarial/ -v
```

### Start the Web UI

```bash
uvicorn release_desk.app:app --reload --port 8000
```

Then open http://localhost:8000 in your browser.

The Release Desk provides:
- **Dashboard** — Release list, pipeline status, ledger summary
- **New Release** — Create a release and run the full pipeline
- **Ledger** — View Merkle log entries, checkpoints, witness cosignatures
- **Trust Root** — View keys, roles, thresholds, cryptographic standards

### Docker Compose Lab

```bash
docker compose -f lab/compose.yml up --build
```

This starts:
- `release-desk` — Web application on port 8000
- `canary-1`, `canary-2` — Canary receiver units
- `unit-3` — General receiver (network disabled for offline simulation)

## Understanding the Output

### 5-Stamp Pipeline

Every release passes through five stamps:

| Stamp | What It Proves | Signed By |
|-------|---------------|-----------|
| 🏭 **Origin** | Where the release came from, how it was built | Builder |
| 🔍 **Inspect** | What capabilities it has, does it violate policy | Inspector Signer |
| ✅ **Approve** | Authorized people approved it (2-of-3) | Approvers |
| 📜 **Record** | History is verifiable and tamper-evident | Ledger + Witness |
| 🧪 **Test** | It survived canary deployment | Canary Receivers |

### Rejection Scenarios

The demo exercises these attack scenarios:

| Code | Attack | Expected Result |
|------|--------|-----------------|
| AT-001 | Forged signature (rogue key) | 0 valid keys → rejected |
| AT-002 | Modified release content | Digest mismatch → rejected |
| AT-003 | Missing/invalid stamps | INELIGIBLE → blocked |
| AT-008 | Author self-approval | Threshold not met → blocked |
| AT-012 | Sequence replay | Anti-rollback → rejected |

### CLI Tools

```bash
# Offline receiver
segel-receiver verify passport.json --trust-root trust.json --key key.json --deploy-to ./deploy --unit-id unit-3

# Approver device
segel-approver review qr-request.json --key approver-key.json

# Witness
segel-witness cosign --key witness-key.json --checkpoint checkpoint.json
```

## Security Notes

- The MVP demo uses **synthetic keys** generated at startup. These are NOT production keys.
- The Release Desk **never holds private signing keys** (SEC-004).
- All verification works **offline** — the Receiver uses locally available trust information.
- AI advisory is **optional and advisory-only** — it cannot override deterministic verdicts.
- SQLite triggers are **guard rails**, not immutability guarantees (SEC-018).

## Project Structure

```
segel-cyber/
├── src/                     # Source code
│   ├── segel_core/          # Shared crypto, schemas, verification
│   ├── builder/             # Deterministic packaging + Origin
│   ├── inspector/           # Capability extraction + policy
│   ├── approver/            # Air-gapped approval protocol
│   ├── ledger/              # Transparency log (Merkle + SQLite)
│   ├── witness/             # Checkpoint cosigner
│   ├── passport/            # Passport assembler
│   ├── promotion/           # Canary evaluation
│   ├── receiver/            # Offline receiver + deployment adapter
│   └── release_desk/        # FastAPI web application
├── tests/                   # Test suite (106 tests)
│   ├── unit/crypto/         # Ed25519, DSSE, Merkle tests
│   ├── integration/         # Full lifecycle test
│   └── adversarial/         # Security attack tests
├── scripts/demo.py          # End-to-end demo script
├── lab/compose.yml          # Docker Compose lab
├── docs/                    # Documentation
└── pyproject.toml           # Project configuration
```

