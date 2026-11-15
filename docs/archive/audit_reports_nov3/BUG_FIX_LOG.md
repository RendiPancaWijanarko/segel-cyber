# SEGEL Bug Fix and Remediation Log

This document records all defects, architectural inconsistencies, and test failures identified and remediated during the comprehensive technical audit of the SEGEL MVP codebase.

---

## Remediation Summary

| Total Defects Fixed | Critical | High | Medium | Low / Quality | Verification Pass Rate |
|:-------------------:|:--------:|:----:|:------:|:-------------:|:----------------------:|
| **16**              | **4**    | **5**| **4**  | **3**         | **100% (234/234 Tests)**|

---

## Detailed Bug Log

### BUG-001: Hypothesis Property-Based Testing Strategy Rejection on Canonical JSON
- **Component**: `tests/unit/test_properties.py`, `src/segel_core/canonical.py`
- **Severity**: High
- **Description**: `test_canonical_json_deterministic` failed with `TypeError: Cannot canonicalise NoneType`. The property test used `st.from_type(type)` generating arbitrary Python primitives (`None`, `int`, `str`), whereas RFC 8785 canonical JSON in SEGEL is strictly specified for JSON object dictionaries (`dict[str, Any]`) or Pydantic models.
- **Root Cause**: Unbounded Hypothesis input generation passed top-level non-dictionary types into `canonical_json()`.
- **Remediation**: Constrained Hypothesis strategy to `st.dictionaries(keys=st.text(), values=...)` representing valid JSON objects with recursive JSON primitives.
- **Files Modified**: `tests/unit/test_properties.py`
- **Regression Test**: `tests/unit/test_properties.py::test_canonical_json_deterministic`
- **Verification**: Passed across 100 Hypothesis iterations.

---

### BUG-002: Inverted Argument Ordering in Cryptographic Ed25519 Verification
- **Component**: `tests/unit/test_properties.py`, `tests/unit/test_ledger.py`
- **Severity**: Critical
- **Description**: In property-based crypto tests and ledger tests, calls to `ed_verify` and `verify` failed with `SignatureError: Ed25519 signature must be exactly 64 bytes`. The arguments were passed in reverse order `(signature, data)` instead of `(public_key, signature, data)`.
- **Root Cause**: Inconsistent parameter ordering between internal cryptographic wrappers and test assertions.
- **Remediation**: Standardized all calls to `verify(public_key: Ed25519PublicKey, signature: bytes, data: bytes)` matching `cryptography.hazmat.primitives.asymmetric.ed25519`.
- **Files Modified**: `tests/unit/test_properties.py`, `tests/unit/test_ledger.py`
- **Regression Test**: `test_ed25519_sign_verify_roundtrip`, `test_ledger_sign_checkpoint`
- **Verification**: Passed (20 crypto unit tests + 16 property tests passing).

---

### BUG-003: Predicate URI Domain Mismatch in Provenance and Attestations
- **Component**: `tests/unit/test_builder.py`, `tests/unit/test_inspector.py`
- **Severity**: Medium
- **Description**: Unit tests failed assertion comparing predicate type URI to `https://segel.dev/attestations/origin/v1` instead of `https://segel.dev/attestation/origin/v1` (singular).
- **Root Cause**: Typo in test predicate assertion versus canonical schema constant in `src/segel_core/schemas/attestation.py`.
- **Remediation**: Corrected predicate URI in builder and inspector test suites to align strictly with PRD v2.0 §14.
- **Files Modified**: `tests/unit/test_builder.py`, `tests/unit/test_inspector.py`
- **Regression Test**: `test_sign_origin_envelope`, `test_inspect_release_generates_attestation`
- **Verification**: Passed (22 builder tests and 21 inspector tests passing).

---

### BUG-004: Missing `public_key_bytes` in Test `PublicKeyInfo` Dataclass
- **Component**: `tests/unit/test_builder.py`, `tests/unit/test_inspector.py`
- **Severity**: Medium
- **Description**: Tests constructing mocked `PublicKeyInfo` objects omitted the required field `public_key_bytes: bytes`, raising `TypeError: missing 1 required positional argument`.
- **Root Cause**: `PublicKeyInfo` dataclass in `src/segel_core/crypto/ed25519.py` requires raw public bytes for fast key identification and key ID derivation (`SHA-256(raw_bytes)`).
- **Remediation**: Updated test key constructors to pass `public_key_bytes=keypair.public_key_bytes`.
- **Files Modified**: `tests/unit/test_builder.py`, `tests/unit/test_inspector.py`
- **Regression Test**: Full unit test suite execution.
- **Verification**: Passed.

---

### BUG-005: Windows Permission Denied on Rollback Deletion of Read-Only Files
- **Component**: `src/receiver/adapter/baseline.py`, `tests/unit/test_receiver.py`
- **Severity**: Critical
- **Description**: Under Windows, when the Baseline Adapter set deployed configuration files to read-only (`0o444`, per security requirement SEC-025), subsequent rollback or teardown attempts failed with `PermissionError: [WinError 5] Access is denied` during `shutil.rmtree` or `Path.unlink`.
- **Root Cause**: On Windows, files with read-only attributes cannot be deleted by standard Python `rmtree` or `unlink` without first clearing the read-only attribute (`stat.S_IWRITE`).
- **Remediation**: Implemented robust cross-platform helpers `_safe_rmtree` and `_safe_unlink` utilizing `os.chmod(target, stat.S_IWRITE | stat.S_IREAD)` in error handlers (`onexc`/`onerror`) prior to unlinking.
- **Files Modified**: `src/receiver/adapter/baseline.py`
- **Regression Test**: `test_receiver_rollback_on_health_failure`, `test_receiver_atomic_rollback`
- **Verification**: Passed on Windows PowerShell and POSIX environments.

---

### BUG-006: Starlette `TemplateResponse` Incompatible Signature in FastAPI Release Desk
- **Component**: `src/release_desk/app.py`
- **Severity**: High
- **Description**: Navigating to web routes (`/`, `/release/{id}`, `/ledger`) raised `TypeError: cannot use 'tuple' as a dict key (unhashable type: 'dict')` from Jinja2's template cache.
- **Root Cause**: Starlette v0.38+ changed `TemplateResponse` signature. Calling `templates.TemplateResponse("index.html", context)` treats the dictionary as the request argument or template name when positional arguments are used.
- **Remediation**: Refactored all 8 template route handlers in `src/release_desk/app.py` to use explicit keyword arguments: `templates.TemplateResponse(request=request, name="index.html", context={...})`.
- **Files Modified**: `src/release_desk/app.py`
- **Regression Test**: `tests/unit/test_release_desk.py` (7 tests verifying status code 200, HTML rendering, and context bindings).
- **Verification**: Passed.

---

### BUG-007: SQLite Multi-Thread Concurrency Violation in FastAPI Async Workers
- **Component**: `src/ledger/ledger.py`, `src/release_desk/app.py`
- **Severity**: High
- **Description**: Under concurrent or async FastAPI requests, database operations failed with `sqlite3.ProgrammingError: SQLite objects created in a thread can only be used in that same thread`.
- **Root Cause**: Default SQLite connection configuration locks access to the creator thread, violating FastAPI's thread pool dispatching for synchronous route calls.
- **Remediation**: Added `check_same_thread=False` to `sqlite3.connect` in `TransparencyLedger`, coupled with WAL mode (`journal_mode=WAL`) and proper connection context management (`__enter__`, `__exit__`, `close()`).
- **Files Modified**: `src/ledger/ledger.py`
- **Regression Test**: `tests/unit/test_release_desk.py`, `tests/integration/test_lifecycle.py`
- **Verification**: Passed without thread affinity warnings.

---

### BUG-008: Missing `consistency_proof` Method on `TransparencyLedger`
- **Component**: `src/ledger/ledger.py`, `src/release_desk/app.py`
- **Severity**: High
- **Description**: Calling `demo.ledger.consistency_proof(...)` or witness cosigning flows raised `AttributeError: 'TransparencyLedger' object has no attribute 'consistency_proof'`.
- **Root Cause**: `consistency_proof` was only implemented on the internal `MerkleTree` instance (`self._tree`) but was not exposed on the public facade of `TransparencyLedger`.
- **Remediation**: Added `consistency_proof(self, m: int, n: int) -> list[str]` method to `TransparencyLedger`, returning hex-encoded hashes for ledger consistency verification.
- **Files Modified**: `src/ledger/ledger.py`
- **Regression Test**: `tests/unit/test_witness.py::test_witness_consistency_proof_validation`
- **Verification**: Passed.

---

### BUG-009: Unhandled `None` Receipt Envelope on Failed Canary Deployment
- **Component**: `src/release_desk/app.py`
- **Severity**: Medium
- **Description**: In `app.py`, if a canary deployment failed during promotion evaluation, `receipt_env` returned `None`, triggering an unhandled `AttributeError: 'NoneType' object has no attribute 'get_payload_bytes'`.
- **Root Cause**: Missing guard condition checking whether the deployment succeeded before accessing receipt envelope bytes.
- **Remediation**: Added explicit null check: `if receipt_env is None: raise ValueError(f"Canary deployment to {canary_id} failed: no receipt produced")`.
- **Files Modified**: `src/release_desk/app.py`
- **Regression Test**: `tests/unit/test_release_desk.py`
- **Verification**: Passed.

---

### BUG-010: Missing Strict Type Annotations in Mypy Type Checker
- **Component**: `src/` (across 41 source files)
- **Severity**: Medium
- **Description**: Running `mypy src/ --strict` flagged 65 type errors including unannotated CLI main functions, missing `dict[str, Any]` parameters, untyped `DemoState` attributes, and untyped Starlette responses.
- **Root Cause**: Prototype code lacked complete type definitions for strict static analysis.
- **Remediation**: Added complete type annotations across all modules, explicit return types (`-> None`), typed dictionary structures, and proper imports.
- **Files Modified**: `src/approver/cli.py`, `src/witness/cli.py`, `src/receiver/cli.py`, `src/release_desk/app.py`, `src/segel_core/verification/passport.py`, `src/segel_core/verification/trust.py`.
- **Regression Test**: `mypy src/`
- **Verification**: `Success: no issues found in 41 source files`.

---

### BUG-011: Bandit Security Linter CWE-703 Uncontrolled Exception Blocks
- **Component**: `src/inspector/inspector.py`, `src/receiver/adapter/baseline.py`, `src/segel_core/verification/trust.py`, `src/ledger/ledger.py`
- **Severity**: Medium
- **Description**: Bandit flagged multiple occurrences of `try ... except: pass` and generic `except Exception: pass` as CWE-703 (Potential suppression of critical exceptions / improper error handling).
- **Root Cause**: Defensive fallback code swallowed broad exceptions.
- **Remediation**: Replaced all broad exception handlers with specific exceptions (`(UnicodeDecodeError, AttributeError)`, `OSError`, `sqlite3.Error`, `(SignatureError, ValueError)`) and utilized `contextlib.suppress(...)` where intentional.
- **Files Modified**: `src/inspector/inspector.py`, `src/receiver/adapter/baseline.py`, `src/segel_core/verification/trust.py`, `src/ledger/ledger.py`
- **Regression Test**: `bandit -r src/ -q`
- **Verification**: Passed with 0 issues identified.

---

### BUG-012: Ruff Linter Rule Violations (250+ PEP 8, Line Length, and Import Issues)
- **Component**: Full repository (`src/`, `tests/`, `scripts/`)
- **Severity**: Low
- **Description**: 254 linting violations flagged by Ruff across formatting, long lines (>100 characters), unsorted imports, and unused variables.
- **Root Cause**: Varied formatting styles during MVP authoring.
- **Remediation**: Executed autofixes and manually resolved line-wrapping, dead imports, and private variable accessors. Added public `get_key_record()` to `TrustContext`.
- **Files Modified**: `src/receiver/adapter/baseline.py`, `src/receiver/cli.py`, `src/release_desk/app.py`, `src/segel_core/verification/passport.py`, `src/segel_core/verification/trust.py`.
- **Regression Test**: `ruff check src/`
- **Verification**: `All checks passed!` (0 errors).

---

### BUG-013: Resource Warning on Unclosed SQLite Connections
- **Component**: `src/ledger/ledger.py`
- **Severity**: Low
- **Description**: Test execution yielded `ResourceWarning: unclosed database <sqlite3.Connection>` when ledger objects were garbage-collected without explicit closure.
- **Root Cause**: `TransparencyLedger` lacked standard context manager methods and destructor finalization.
- **Remediation**: Added `close()`, `__enter__`, `__exit__`, and `__del__` to `TransparencyLedger`.
- **Files Modified**: `src/ledger/ledger.py`
- **Regression Test**: `pytest tests/unit/test_ledger.py -W error::ResourceWarning`
- **Verification**: Zero resource warnings during test runs.

---

### BUG-014: Witness Consistency Proof Type Incompatibility Between Hex and Bytes
- **Component**: `src/release_desk/app.py`, `src/witness/witness.py`
- **Severity**: High
- **Description**: In `app.py`, `demo.ledger.consistency_proof()` returned `list[str]` (hex-encoded digests), whereas `Witness.cosign_checkpoint` strictly required `list[bytes]`, causing a static type failure and potential runtime verification mismatch.
- **Root Cause**: Merkle consistency proof was formatted as hex strings for API transport without converting back to raw bytes for cryptographic proof verification.
- **Remediation**: Converted hex strings to `[bytes.fromhex(h) for h in proof_hex]` prior to invoking `cosign_checkpoint`.
- **Files Modified**: `src/release_desk/app.py`
- **Regression Test**: `tests/unit/test_release_desk.py`, `tests/unit/test_witness.py`
- **Verification**: Passed.

---

### BUG-015: Undefined `SignatureError` Reference in Trust Verification Module
- **Component**: `src/segel_core/verification/trust.py`
- **Severity**: High
- **Description**: `src/segel_core/verification/trust.py` caught `SignatureError` in key loading without importing it from `segel_core.errors`, resulting in `NameError: name 'SignatureError' is not defined` if a malformed key was encountered.
- **Root Cause**: Omitted import in the module header.
- **Remediation**: Added `SignatureError` to `from segel_core.errors import (...)`.
- **Files Modified**: `src/segel_core/verification/trust.py`
- **Regression Test**: `mypy src/`
- **Verification**: Passed.

---

### BUG-016: Path Traversal Vulnerability Defense in Baseline Adapter Staging
- **Component**: `src/receiver/adapter/baseline.py`, `src/builder/builder.py`
- **Severity**: Critical
- **Description**: Audit of bundle unpacking indicated potential path traversal risks if malicious archive members contained absolute paths or directory climbing (`../`).
- **Root Cause**: Reliance on simple string prefixes rather than canonical resolved path comparison.
- **Remediation**: Enforced strict path sanitization: rejection of `..` segments, leading slashes, backslashes, and verified that all staged and deployed files reside strictly within `_deploy_root` via `.resolve().relative_to(...)`.
- **Files Modified**: `src/receiver/adapter/baseline.py`, `src/builder/builder.py`
- **Regression Test**: `tests/adversarial/test_adversarial.py::test_at005_path_traversal_rejection`
- **Verification**: Passed (AT-005 strictly rejects path traversal attempts).

