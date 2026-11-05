# SEGEL Implementation Plan

## Phase Overview

| Phase | Name | Status | Description |
|-------|------|--------|-------------|
| 0 | Documentation & Audit | ✅ Complete | PRD review, requirement mapping |
| 1 | Project Foundation | ✅ Complete | Core library, crypto, schemas, tests |
| 2 | Walking Skeleton | ✅ Complete | All components created with interfaces |
| 3 | Cryptographic Foundation | ✅ Complete | DSSE, Ed25519, Merkle proofs, trust |
| 4 | Release Passport & Origin | ✅ Complete | Build, manifest, author sign, builder sign |
| 5 | Inspect & Approval | ✅ Complete | Capability extraction, policy, approval |
| 6 | Record & Transparency | ✅ Complete | Ledger, witness, Merkle proofs |
| 7 | Test & Promotion | ✅ Complete | Canary deploy, health receipts, promotion |
| 8 | Release Desk UI | ✅ Complete | Jinja2+HTMX templates, FastAPI routes |
| 9 | Documentation | ✅ Complete | Architecture, security, limitations, demo |
| 10 | Demo & Lab | ✅ Complete | Demo script, Docker Compose, CLI tools |

## Phase 1: Project Foundation

### Deliverables
- [x] `pyproject.toml` with all dependencies
- [x] `src/segel_core/` package structure
- [x] `errors.py` — 20 typed error codes from Appendix E
- [x] `canonical.py` — Canonical JSON serialization
- [x] `crypto/ed25519.py` — Key generation, signing, verification
- [x] `crypto/dsse.py` — PAE, DSSE envelopes, threshold verification
- [x] `crypto/hashing.py` — SHA-256, Merkle tree (RFC 6962), proofs
- [x] `schemas/` — All 7 schema modules (manifest, binding, attestation, trust, passport, receipt, checkpoint)
- [x] `verification/trust.py` — TrustContext with key/role lookup, revocation
- [x] `verification/passport.py` — Full passport verification (all 5 stamps)
- [x] Unit tests for Ed25519 (13 tests)
- [x] Unit tests for DSSE (22 tests)
- [x] Unit tests for Merkle (24 tests)

## Phase 2–7: Components

### Builder (`src/builder/`)
- [x] Deterministic tar.gz packaging (SEC-017)
- [x] Manifest generation with subject digests
- [x] Origin provenance (in-toto Statement, SLSA-aligned)
- [x] Author signing (separate key)
- [x] Builder signing (separate key)
- [x] File validation (path traversal, extensions, sizes)

### Inspector (`src/inspector/`)
- [x] Deterministic capability extraction (5 categories, regex patterns)
- [x] Versioned policy evaluation (PASS/WARN/REJECT)
- [x] AI advisory stub (Ollama interface, not active)
- [x] AI cannot downgrade deterministic REJECT
- [x] Inspector Signer attestation

### Approver (`src/approver/`)
- [x] Approval payload creation with evidence binding
- [x] PAE-based approver signing
- [x] Multi-party collection into DSSE envelope
- [x] QR request/response generation
- [x] Pre-committed promotion criteria inclusion

### Ledger (`src/ledger/`)
- [x] SQLite-backed append-only log
- [x] In-memory Merkle tree (RFC 6962)
- [x] Signed checkpoints (C2SP format)
- [x] Inclusion proofs
- [x] Consistency proofs
- [x] Witness cosignature storage
- [x] Guard rail triggers (NOT security boundary)

### Witness (`src/witness/`)
- [x] Independent checkpoint cosigning
- [x] Consistency proof verification before cosigning
- [x] Fork detection
- [x] State tracking

### Passport Assembler (`src/passport/`)
- [x] Candidate passport (4 stamps + candidate proof)
- [x] General passport (5 stamps + candidate + promotion proofs)
- [x] Epoch and snapshot inclusion

### Promotion Controller (`src/promotion/`)
- [x] Pre-committed criteria evaluation
- [x] Required healthy canary count check
- [x] Required probe verification
- [x] Failed canary blocks promotion

### Receiver (`src/receiver/`)
- [x] Offline passport verification
- [x] 10-step deployment lifecycle via Baseline Adapter
- [x] Signed deployment receipts
- [x] Anti-rollback enforcement
- [x] Recovery mode on state corruption
- [x] Write-then-rename state persistence

## Phase 8: Release Desk UI

- [x] FastAPI application with routes
- [x] Base template (Jinja2 + HTMX, dark theme)
- [x] Dashboard (index.html)
- [x] New Release form (new_release.html)
- [x] Release Detail view (release_detail.html)
- [x] Ledger view (ledger.html)
- [x] Trust Root view (trust.html)
- [x] Error page (error.html)

## Phase 9: Documentation

- [x] `docs/ARCHITECTURE.md`
- [x] `docs/SECURITY_MODEL.md`
- [x] `docs/KNOWN_LIMITATIONS.md`
- [x] `docs/DECISIONS.md`
- [x] `docs/DEMO_GUIDE.md`
- [x] `docs/TEST_REPORT.md`
- [x] `docs/IMPLEMENTATION_PLAN.md` (this file)
- [x] `docs/TRACEABILITY.md`

## Phase 10: Demo & Lab

- [x] `scripts/demo.py` — Full 18-step lifecycle demo
- [x] `lab/compose.yml` — Docker Compose lab
- [x] `Dockerfile`
- [x] `.gitignore`
- [x] CLI entry points (receiver, approver, witness)

