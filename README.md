# SEGEL — Sistem Edar Gelar Elektronik Lapis-ganda

**Configuration and Release Distribution Platform with Cryptographic Evidence**

> *No Evidence, No Deployment.*

SEGEL ensures that every configuration release deployed to operational units carries independently verifiable security evidence across five stamps:

| Stamp | Question It Answers | Signed By |
|-------|-------------------|-----------|
| 🏭 **Origin** | Where did this release come from, and how was it built? | Builder |
| 🔍 **Inspect** | What does this release change, and does it violate policy? | Inspector |
| ✅ **Approve** | Have the authorised people approved it? | Approvers (2-of-3) |
| 📜 **Record** | Is its history verifiable and tamper-evident? | Ledger + Witness |
| 🧪 **Test** | Did it survive a controlled canary deployment? | Canary Receivers |

## Quick Start

```bash
# Install in development mode
pip install -e ".[dev]"

# Run the full 18-step lifecycle demo
python scripts/demo.py

# Run all tests (234 tests)
python -m pytest tests/ -v

# Start the web UI
uvicorn release_desk.app:app --reload --port 8000
```

## End-to-End Lifecycle

The demo demonstrates the complete release lifecycle:

1. Author creates a configuration release
2. Bundle is validated and manifest is created
3. Author signs the manifest (separate signer)
4. Builder produces Origin provenance (SLSA-aligned)
5. Inspector extracts capabilities and evaluates policy
6. AI advisory (optional, skipped in MVP)
7. Inspector Signer issues Inspect attestation
8. Approvers review payload via QR air-gapped transfer
9. 2-of-3 approval threshold met (author excluded)
10. Ledger records candidate with Merkle proof
11. Candidate deployed to 2 canary units
12. Canary Receivers generate signed health receipts
13. Promotion Controller evaluates pre-committed criteria
14. Ledger records the promotion
15. General Release Passport assembled
16. **Offline** Receiver independently verifies and deploys
17. Receiver generates signed deployment receipt
18. System rejects forged, modified, unauthorised, and replayed releases

## Architecture

Security-core-first modular monolith:

```
src/
├── segel_core/          # Trusted: crypto, schemas, verification
├── builder/             # Deterministic packaging + Origin provenance
├── inspector/           # Capability extraction + policy evaluation
├── approver/            # Air-gapped multi-party approval
├── ledger/              # Append-only Merkle transparency log
├── witness/             # Independent checkpoint cosigner
├── passport/            # Release Passport assembler
├── promotion/           # Canary evaluation + promotion controller
├── receiver/            # Offline verification + deployment adapter
└── release_desk/        # FastAPI web application (untrusted, no keys)
```

## Testing

```
234 tests  ·  0 failures  ·  82.37% coverage

├── 75 × Core Crypto (Ed25519 vectors, DSSE envelopes, Merkle proofs)
├── 82 × Core Components (Builder, Inspector, Ledger, Receiver)
├── 28 × Distribution & Control (Approver, Witness, Passport, Promotion, Web UI, CLIs)
├── 16 × Property-Based (Hypothesis determinism, canonical JSON, Merkle invariants)
├──  6 × Integration (Full 18-step lifecycle + rejection scenarios)
└── 25 × Adversarial (AT-001 to AT-045: forged sigs, tampering,
         missing stamps, replay, self-approval, path traversal,
         executables, AI override, witness forks, failed canaries)
```

## Documentation

| Document | Contents |
|----------|----------|
| [Architecture](docs/ARCHITECTURE.md) | System architecture, component zones, data flow |
| [Security Model](docs/SECURITY_MODEL.md) | Threat model, controls, evidence chain, guarantees |
| [Demo Guide](docs/DEMO_GUIDE.md) | Step-by-step instructions for running the demo |
| [Test Report](docs/TEST_REPORT.md) | All 106 tests with AT-series mapping |
| [Traceability](docs/TRACEABILITY.md) | PRD requirements → code → test mapping |
| [Design Decisions](docs/DECISIONS.md) | 10 technical decisions with rationale |
| [Known Limitations](docs/KNOWN_LIMITATIONS.md) | 14 documented MVP limitations |
| [Implementation Plan](docs/IMPLEMENTATION_PLAN.md) | 10-phase plan with status |
| [Progress](docs/PROGRESS.md) | Current development status |

## Technology Stack

| Technology | Purpose |
|---|---|
| Python 3.12+ | Implementation language |
| Ed25519 (RFC 8032) | All signatures |
| DSSE | Signing envelope format |
| in-toto Statement v1 | Attestation structure |
| SHA-256 / RFC 6962 Merkle | Digests and transparency proofs |
| C2SP tlog-checkpoint | Checkpoint format |
| FastAPI + Jinja2 + HTMX | Release Desk web UI |
| Pydantic v2 | Schema validation |
| SQLite | MVP storage (NOT a security boundary) |
| Ollama | Optional local AI inference (advisory only) |
| Docker Compose | Demonstration lab |
| pytest + Hypothesis | Testing framework |

## Docker Lab

```bash
docker compose -f lab/compose.yml up --build
# Open http://localhost:8000
```

Containers: `release-desk` (web), `canary-1`, `canary-2`, `unit-3` (offline receiver).

## CLI Tools

```bash
segel-receiver verify passport.json --trust-root trust.json --key key.json --deploy-to ./deploy --unit-id unit-3
segel-approver review qr-request.json --key approver-key.json
segel-witness cosign --key witness-key.json --checkpoint checkpoint.json
```

## Security Invariants

- Release Desk **never holds private signing keys**
- AI has **no signing keys and no deployment permissions**
- Receiver verification works **offline**
- All operations **fail closed** — missing evidence blocks the pipeline
- SQLite triggers are **guard rails**, not immutability (tamper evidence from Merkle proofs)
- **No custom cryptographic protocols** — Ed25519, DSSE, RFC 6962, SLSA

## License

MIT

## Disclaimer

SEGEL does not prove software is safe. It provides cryptographically verifiable evidence about origin, inspection, approval, recording, and testing of configuration releases. All demonstration data uses synthetic keys and is not suitable for production use.
