# SEGEL Requirements Traceability Matrix

This document maps PRD v2.0 requirements to their implementation and test coverage.

## P0 Requirements — Release Lifecycle

| Requirement | PRD Section | Component | Implementation | Test |
|-------------|------------|-----------|----------------|------|
| Release creation | §6.0 Step 1 | Builder | `build_release_package()` | `test_full_lifecycle` Step 1–2 |
| Manifest generation | §6.0 Step 2 | Builder | `Manifest` + `SubjectDigest` | `test_full_lifecycle` Step 2 |
| Author signs manifest | §6.0 Step 3 | Builder | `sign_manifest()` | `test_full_lifecycle` Step 3 |
| Builder Origin provenance | §6.0 Step 4, §7.3 | Builder | `sign_origin()`, `OriginPredicate` | `test_full_lifecycle` Step 4 |
| Deterministic capability extraction | §6.0 Step 5, §7.5 | Inspector | `extract_capabilities()` | `test_full_lifecycle` Step 5 |
| AI advisory | §6.0 Step 6 | Inspector | `_run_ai_advisory()` (stub) | `test_full_lifecycle` Step 6 |
| Inspector attestation | §6.0 Step 7 | Inspector | `sign_inspect()` | `test_full_lifecycle` Step 7 |
| Approver review | §6.0 Step 8, §7.7 | Approver | `create_approval_payload()` | `test_full_lifecycle` Step 8 |
| Approval threshold | §6.0 Step 9 | Approver | `collect_approvals()`, `verify_threshold()` | `test_full_lifecycle` Step 9 |
| Ledger recording | §6.0 Step 10, §16.3 | Ledger | `TransparencyLedger.append()` | `test_full_lifecycle` Step 10 |
| Canary deployment | §6.0 Step 11 | Receiver | `Receiver.verify_and_deploy()` | `test_full_lifecycle` Steps 11–12 |
| Health receipts | §6.0 Step 12 | Receiver | `Receiver._create_receipt()` | `test_full_lifecycle` Step 12 |
| Promotion evaluation | §6.0 Step 13, §7.9 | Promotion | `evaluate_promotion()` | `test_full_lifecycle` Step 13 |
| Promotion recording | §6.0 Step 14 | Ledger | `TransparencyLedger.append()` | `test_full_lifecycle` Step 14 |
| General passport | §6.0 Step 15, §7.10 | Passport | `build_general_passport()` | `test_full_lifecycle` Step 15 |
| Offline verification | §6.0 Step 16, §17, NFR-001 | Receiver | `verify_passport()` | `test_full_lifecycle` Step 16 |
| Deployment receipt | §6.0 Step 17 | Receiver | `_create_receipt()` | `test_full_lifecycle` Step 17 |
| Rejection scenarios | §6.0 Step 18 | Multiple | See adversarial tests | AT-001 through AT-045 |

## Security Controls

| Control | PRD Ref | Component | Implementation | Test |
|---------|---------|-----------|----------------|------|
| SEC-001: Author ≠ Approver | §7.7 | Core/DSSE | `verify_threshold(excluded_key_ids)` | AT-008, `test_rejection_author_approves_own_release` |
| SEC-004: No keys in Release Desk | §7.2 | Release Desk | Signing in separate processes | Architectural (no key param in app.py routes) |
| SEC-013: AI no keys/deploy | §7.5 | Inspector | AI function has no key access | AT-015, AT-016 |
| SEC-017: Deterministic packaging | §7.3 | Builder | Fixed mtime, uid, gid, sorted paths | Builder unit behavior |
| SEC-018: No SQLite immutability | §16.3 | Ledger | Merkle tree + signed checkpoints | Merkle tests |
| SEC-023: Path validation | §7.3 | Builder/Adapter | `_validate_path()`, `BaselineAdapter.stage()` | AT-026, AT-027, AT-030 |
| SEC-025: No executables | §7.3 | Builder | `FORBIDDEN_EXTENSIONS` check | AT-028 |
| SEC-031: RFC 6962 Merkle | §16.3 | Core/Hashing | `merkle_leaf_hash()`, `MerkleTree` | 24 Merkle tests |
| SEC-033: Key identity | §8.1 | Core/Ed25519 | `SHA-256(raw_pub_key_bytes)` | `test_key_id_is_sha256` |
| SEC-037: CSPRNG | §8.1 | Core/Ed25519 | `Ed25519PrivateKey.generate()` | Key generation tests |

## Adversarial Test Coverage

| AT Code | Attack Description | PRD Ref | Test File | Status |
|---------|-------------------|---------|-----------|--------|
| AT-001 | Invalid signature | SEC-001 | `test_adversarial.py` | ✅ |
| AT-002 | Modified content | SEC-023 | `test_adversarial.py` | ✅ |
| AT-003 | Missing stamps | PH-4 | `test_adversarial.py` | ✅ |
| AT-004 | Sequence replay | §17 | `test_adversarial.py` | ✅ |
| AT-005 | Below approval threshold | §7.7 | `test_adversarial.py` | ✅ |
| AT-006 | Duplicate approver key | §7.7 | `test_adversarial.py` | ✅ |
| AT-008 | Author self-approval | SEC-001 | `test_adversarial.py` | ✅ |
| AT-009 | Epoch too low | §17 | `test_adversarial.py` | ✅ |
| AT-015 | AI override REJECT | SEC-013 | `test_adversarial.py` | ✅ |
| AT-016 | AI failure recording | SEC-013 | `test_adversarial.py` | ✅ |
| AT-019 | Unknown capability | §7.5 | `test_adversarial.py` | ✅ |
| AT-023 | Witness fork detection | §16.3 | `test_adversarial.py` | ✅ |
| AT-024 | Failed canary blocks promotion | §7.9 | `test_adversarial.py` | ✅ |
| AT-026 | Path traversal | SEC-023 | `test_adversarial.py` | ✅ |
| AT-027 | Absolute path | SEC-023 | `test_adversarial.py` | ✅ |
| AT-028 | Executable extension | SEC-025 | `test_adversarial.py` | ✅ |
| AT-029 | Empty release | PH-4 | `test_adversarial.py` | ✅ |
| AT-030 | Null byte in filename | SEC-023 | `test_adversarial.py` | ✅ |
| AT-045 | Held release | §16.3 | `test_adversarial.py` | ✅ |

## Stamp-to-Component Mapping

| Stamp | Attestation Type | Payload Type | Signer Role | Verifier |
|-------|-----------------|--------------|-------------|----------|
| Origin | `OriginPredicate` | `application/vnd.segel.origin+json` | `builder` | `passport.py` |
| Inspect | `InspectPredicate` | `application/vnd.segel.inspect+json` | `inspector_signer` | `passport.py` |
| Approve | `ApprovePredicate` | `application/vnd.segel.approve+json` | `approver` (threshold) | `passport.py` |
| Record | Ledger checkpoint + Merkle proof | (ledger entry) | `ledger` + `witness` | `passport.py` |
| Test | `TestPredicate` | `application/vnd.segel.test+json` | `receiver` | `passport.py` |

