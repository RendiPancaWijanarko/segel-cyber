# SEGEL Python 3.12 Clean Runtime Verification Report

**Auditor**: Independent DevOps Auditor & Release Readiness Assessor  
**Target Milestone**: SEGEL MVP Version 0.1.0-MVP  
**Execution Date**: November 3, 2026  
**Final Status**: **VERIFIED PASS (PYTHON 3.12.16 CONTAINER & PYTHON 3.14.6 HOST)**

---

## 1. Executive Summary & Verification Objective

The previous operational readiness campaign documented that tests were executed using host Python 3.14.6 while relying on `mypy`'s `--python-version 3.12` target to infer compatibility. 

Per the independent verification mandate:
> "Identify the exact Python interpreter used for the final 244-test execution. Run the complete test suite using Python 3.12, not merely mypy's Python 3.12 compatibility target. Verify dependency installation and compatibility in a clean Python 3.12 environment. Record exact commands, interpreter versions, exit codes, and test results."

This audit built a clean container using [`Dockerfile`](file:///c:/Users/Rendi/OneDrive/ドキュメント/Dokumen Pribadi/KOMPETISI/segel-cyber/Dockerfile) (`python:3.12-slim`), executed a fresh dependency installation, and ran the complete 244-test suite inside an actual **Python 3.12.16** Linux environment.

---

## 2. Interpreter Identification

### 2.1 Host Environment
- **Binary Path**: `C:\Users\Rendi\AppData\Local\Python\pythoncore-3.14-64\python.exe`
- **Reported Version**: `Python 3.14.6 (tags/v3.14.6:c63aec6, Jun 10 2026, 10:26:10) [MSC v.1944 64 bit (AMD64)]`
- **Platform**: `Windows-11-10.0.26300-SP0`

### 2.2 Clean Container Environment
- **Base Image**: `docker.io/library/python:3.12-slim` (Digest `sha256:b18b261e1b4974b4f321451ad5251ded85abb22c2b8b262da527dda1d031ab30`)
- **Binary Path**: `/usr/local/bin/python`
- **Reported Version**: `Python 3.12.16`
- **Platform**: `Linux 6.6.137+ x86_64 (Debian 12 Bookworm slim)`

---

## 3. Dependency Installation & Remediation in Python 3.12

### 3.1 Identified Defect: Missing Test Dependency in Clean Environment
During the initial clean installation of `.[dev]` inside the Python 3.12 container, running `pytest` failed at collection time in `tests/unit/test_release_desk.py`:
```text
RuntimeError: The starlette.testclient module requires the httpx2 package to be installed.
```
**Root Cause**: Starlette 1.10.0 (pulled during fresh installation) strictly enforces the installation of `httpx2` when `fastapi.testclient.TestClient` is imported. On the Windows host workstation, an older Starlette version was cached which only emitted a deprecation warning.
**Remediation**: Added `"httpx2"` and `"httpx>=0.28.0"` to `[project.optional-dependencies] dev` in [`pyproject.toml`](file:///c:/Users/Rendi/OneDrive/ドキュメント/Dokumen Pribadi/KOMPETISI/segel-cyber/pyproject.toml).

---

## 4. Empirical Test Suite Execution in Python 3.12.16

### 4.1 Execution Command
```bash
docker run --rm -u root -v "${PWD}:/workspace" -w /workspace segel:py312 \
    sh -c "pip install -q -e '.[dev]' && pytest --cov=src --cov-report=term-missing"
```

### 4.2 Raw Execution Output
```text
============================= test session starts ==============================
platform linux -- Python 3.12.16, pytest-9.2.0, pluggy-1.7.0
rootdir: /workspace
configfile: pyproject.toml
testpaths: tests
plugins: asyncio-1.4.1.post1, cov-7.1.0, platformdirs-4.14.3, hypothesis-6.170.14, anyio-4.16.0
asyncio: mode=Mode.STRICT, debug=False, asyncio_default_fixture_loop_scope=None, asyncio_default_test_loop_scope=function
collected 244 items

tests/adversarial/test_adversarial.py .........................          [ 10%]
tests/integration/test_lifecycle.py ......                               [ 12%]
tests/unit/crypto/test_dsse.py ......................                    [ 21%]
tests/unit/crypto/test_ed25519.py ....................                   [ 29%]
tests/unit/crypto/test_merkle.py .................................       [ 43%]
tests/unit/test_approver.py ....                                         [ 45%]
tests/unit/test_builder.py ......................                        [ 54%]
tests/unit/test_clis.py ......                                           [ 56%]
tests/unit/test_config.py .....                                          [ 58%]
tests/unit/test_inspector.py .....................                       [ 67%]
tests/unit/test_ledger.py .........................                      [ 77%]
tests/unit/test_ledger_concurrency.py ...                                [ 78%]
tests/unit/test_passport_and_promotion.py .....                          [ 80%]
tests/unit/test_properties.py ................                           [ 87%]
tests/unit/test_receiver.py ................                             [ 93%]
tests/unit/test_receiver_offline_isolation.py ..                         [ 94%]
tests/unit/test_release_desk.py .......                                  [ 97%]
tests/unit/test_witness.py ......                                        [100%]

================================ tests coverage ================================
TOTAL                                      2185    283    498    108    83%
Required test coverage of 80.0% reached. Total coverage: 83.27%
============================= 244 passed in 34.82s =============================
```

### 4.3 Key Metrics Verified Under Python 3.12.16:
- **Total Tests Collected**: 244
- **Passed**: 244 (100%)
- **Failed / Errors**: 0 (0%)
- **Exit Code**: `0`
- **Total Coverage**: **83.27%** (Exceeds project 80.0% threshold)
- **Duration**: 34.82 seconds

---

## 5. Verification Conclusion

The claim that SEGEL is compatible with Python 3.12 is **empirically validated**. All 244 unit, adversarial, integration, property, and operational tests pass inside a clean, reproducible `python:3.12-slim` container.

