# SEGEL Test Report

## Summary

| Category | Tests | Status |
|----------|-------|--------|
| Unit — Ed25519 Cryptography | 20 | ✅ All pass |
| Unit — DSSE Envelopes | 22 | ✅ All pass |
| Unit — RFC 6962 Merkle Tree | 33 | ✅ All pass |
| Unit — Builder & Packaging | 22 | ✅ All pass |
| Unit — Inspector & Policy | 21 | ✅ All pass |
| Unit — Transparency Ledger | 25 | ✅ All pass |
| Unit — Receiver & Baseline Adapter | 14 | ✅ All pass |
| Unit — Approver & QR Exchange | 4 | ✅ All pass |
| Unit — Witness & Checkpoint Cosigning | 6 | ✅ All pass |
| Unit — Passport & Promotion Controller | 5 | ✅ All pass |
| Unit — Release Desk Web Application | 7 | ✅ All pass |
| Unit — CLI Entry Points | 6 | ✅ All pass |
| Property-Based — Hypothesis Testing | 16 | ✅ All pass |
| Integration — End-to-End Lifecycle | 6 | ✅ All pass |
| Adversarial — Security Attack Matrix | 25 | ✅ All pass |
| **Total** | **232** | **✅ 100% Pass (0 Failures)** |

**Code Coverage**: **82.56%** across the entire `src/` codebase (exceeds the 80.0% requirement).

---

## Unit Tests: Cryptographic Primitives & Core

### Ed25519 (`tests/unit/crypto/test_ed25519.py`) — 20 tests
- RFC 8032 Test Vector 1, 2, and 3 verification.
- Key generation using OS CSPRNG (`os.urandom`).
- Deterministic key identity: `key_id = SHA-256(raw_32_byte_public_key)`.
- Sign and verify round-trip; rejection of wrong key, wrong message, truncated/mutated signatures.
- Public key base64 import/export with strict canonical validation.
- Unencrypted seed import (`import_private_key`) for tooling and encrypted PKCS#8/scrypt import/export for secure storage.

### DSSE Envelopes (`tests/unit/crypto/test_dsse.py`) — 22 tests
- Pre-Authentication Encoding (PAE) against official DSSE specification test vectors.
- Single and multi-signer envelope creation and signature aggregation.
- DSSE payload type enforcement (`application/vnd.segel.*`).
- Verification threshold enforcement with author exclusion (SEC-001).
- Distinct key counting (duplicate signatures from the same key counted only once).
- Rejection of mutated signatures and non-canonical base64 encodings.

### Merkle Tree (`tests/unit/crypto/test_merkle.py`) — 33 tests
- RFC 6962 compliant domain separation (`0x00` leaf prefix, `0x01` internal node prefix).
- Hand-computed test vectors for 1, 2, and 4-leaf trees.
- Inclusion proof generation and verification for trees of sizes 1 through 32.
- Consistency proof generation and verification across various sizes (`m → n`).
- Fork detection: identical sizes with different roots immediately detected.

---

## Unit Tests: Pipeline Components

### Builder (`tests/unit/test_builder.py`) — 22 tests
- Deterministic tar.gz creation with fixed mtime (1700000000), sorted paths, uid/gid 0.
- Manifest generation and SHA-256 digest calculation.
- Origin provenance attestation (`https://segel.dev/attestation/origin/v1`).
- Input validation: rejection of empty packages, path traversal (`../`), absolute paths, null bytes, backslashes, and forbidden executable extensions (`.exe`, `.sh`, `.py`, `.dll`, `.so`).

### Inspector (`tests/unit/test_inspector.py`) — 21 tests
- Deterministic capability extraction (`network_listen`, `file_write`, `external_connect`, `credential_reference`, `privilege_escalation`).
- Policy evaluation engine producing PASS, WARN, and REJECT verdicts.
- Privilege escalation strictly triggering REJECT; credential references triggering WARN.
- Graceful degradation when AI advisory (Ollama) is unavailable, recording `ai_status = "failed"` without blocking deterministic verdicts.

### Transparency Ledger (`tests/unit/test_ledger.py`) — 25 tests
- Append-only Merkle log backed by SQLite with in-memory caching.
- Checkpoint creation and Ledger Signer signing.
- Merkle inclusion proof generation for every recorded event.
- Witness cosignature storage and multi-witness verification.
- Event type validation (`candidate_recorded`, `release_promoted`, etc.).

### Receiver & Baseline Adapter (`tests/unit/test_receiver.py`) — 14 tests
- 10-step deployment lifecycle (preflight, snapshot, stage, backup, apply, health check, commit, rollback, cleanup).
- Digest and size mismatch detection during staging.
- Cross-platform atomic rollback restoring previous configuration even with read-only files.
- Built-in health probes (`file_exists`, `config_valid`).
- Receiver state persistence and recovery mode enforcement (blocking deployment if state corrupted).

### Approver & QR Exchange (`tests/unit/test_approver.py`) — 4 tests
- Approval payload binding Origin and Inspect evidence digests.
- Air-gapped approver signing over DSSE Pre-Authentication Encoding.
- QR request payload compaction and response parsing.
- Multi-party signature collection into DSSE envelope.

### Witness & Checkpoint Verification (`tests/unit/test_witness.py`) — 6 tests
- Independent checkpoint verification ensuring monotone tree extension.
- Cosigning first checkpoint without proof; verifying consistency proof for extending checkpoints.
- Rejection of split-view forks (same size, different root) and smaller tree sizes.

### Passport Assembler & Promotion Controller (`tests/unit/test_passport_and_promotion.py`) — 5 tests
- Candidate passport assembly for canary distribution.
- General passport assembly including canary health receipts and promotion proofs.
- Promotion criteria evaluation checking minimum healthy canary counts and mandatory health probes.

### Release Desk Web Application (`tests/unit/test_release_desk.py`) — 7 tests
- FastAPI endpoint testing using `TestClient`:
  - `GET /` dashboard displaying release list and ledger metrics.
  - `GET /trust` displaying trust root keys, roles, and current epoch.
  - `GET /ledger` displaying Merkle log entries and signed checkpoints.
  - `POST /release/create` triggering the full pipeline.
  - `POST /release/{idx}/deploy-canary` deploying to simulated canaries.
  - `POST /release/{idx}/promote` verifying promotion criteria and promoting to general release.
  - `POST /reset` resetting in-memory demo state.

### CLI Entry Points (`tests/unit/test_clis.py`) — 6 tests
- `segel-approver`: `--help` flag and `review --auto-approve` flow.
- `segel-witness`: `--help` flag, `cosign` checkpoint flow, and `status` query.
- `segel-receiver`: `--help` flag and `status` state query.

---

## Property-Based Tests (`tests/unit/test_properties.py`) — 16 tests

Using **Hypothesis**:
- Canonical JSON determinism, whitespace absence, key sorting, and parseability.
- SHA-256 properties: fixed length, deterministic output, probabilistic collision resistance.
- Merkle leaf/node domain separation, order dependency, and inclusion proof validity across arbitrary byte sequences.
- Ed25519 signature round-trip and non-malleability across arbitrary message lengths.

---

## Integration Tests (`tests/integration/test_lifecycle.py`) — 6 tests

| Test | Description | Steps Covered |
|------|-------------|---------------|
| `test_full_lifecycle` | Complete 18-step lifecycle from creation to offline verification | Steps 1–17 |
| `test_rejection_invalid_signature` | Forged signature rejected (rogue key not in trust root) | Step 18a / AT-001 |
| `test_rejection_modified_bundle` | Single bit flip in release file detected and rejected | Step 18b / AT-002 |
| `test_rejection_missing_stamps` | Missing approval/record stamps block deployment | Step 18c / AT-003 |
| `test_rejection_author_approves_own_release` | Author self-approval rejected; threshold not met | Step 18d / AT-008 |
| `test_rejection_sequence_replay` | Lower sequence number rejected by anti-rollback state | Step 18e / AT-012 |

---

## Adversarial Tests (`tests/adversarial/test_adversarial.py`) — 25 tests

| AT Code | Attack Vector | Expected Outcome |
|---------|---------------|------------------|
| AT-001 | Invalid / forged signature | Rejected — 0 valid keys recognized |
| AT-002 | Modified release content | Rejected — digest mismatch during staging |
| AT-003 | Missing stamps (Origin/Inspect/Approve/Record/Test) | Rejected — INELIGIBLE |
| AT-004 | Sequence replay (anti-rollback attack) | Rejected — sequence replay blocked |
| AT-005 | Single approver below threshold | Rejected — threshold not met |
| AT-006 | Duplicate approver key in envelope | Counts once — threshold not met |
| AT-008 | Author self-approval | Author excluded — threshold not met |
| AT-009 | Epoch enforcement (strict vs advisory) | Strict blocks; advisory warns |
| AT-015 | AI override of deterministic REJECT | REJECT cannot be downgraded by AI |
| AT-016 | Credential reference detection | Triggers WARN with explicit findings |
| AT-019 | AI failure during inspection | `ai_status = "failed"` recorded, deterministic verdict preserved |
| AT-023 | Witness fork detection | `CheckpointForkError` raised on split-view |
| AT-024 | Failed canary blocks promotion | Promotion denied when canary unhealthy |
| AT-026 | Path traversal in deployment archive | `PackageMalformedError` raised |
| AT-027 | Absolute path in deployment archive | `PackageMalformedError` raised |
| AT-028 | Executable file extension in configuration | `PackageMalformedError` raised |
| AT-029 | Empty release package | `PackageMalformedError` raised |
| AT-030 | Null byte in filename | `PackageMalformedError` raised |
| AT-045 | Held release enforcement | Release on hold blocks deployment |

---

## Running the Test Suite

```bash
# Run all tests
python -m pytest tests/ -v

# Run with test coverage
python -m pytest tests/ --cov=src --cov-report=term-missing

# Run property-based tests only
python -m pytest tests/unit/test_properties.py -v

# Run integration & adversarial tests only
python -m pytest tests/integration/ tests/adversarial/ -v
```
