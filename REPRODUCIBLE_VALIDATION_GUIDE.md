# SEGEL Reproducible Validation & Verification Guide

This guide contains the exact commands, tool parameters, and execution procedures required to independently reproduce every audit result, test run, security scan, and performance benchmark reported for the SEGEL MVP.

---

## 1. Environment Setup & Dependency Verification

### 1.1 Prerequisites
- Python 3.12, 3.13, or 3.14 (64-bit)
- Git and standard terminal shell (PowerShell or Bash)
- Optional: Docker 24.0+ and Docker Compose v2.20+

### 1.2 Virtual Environment Installation
```bash
# Create and activate virtual environment
python -m venv .venv

# On Linux/macOS:
source .venv/bin/activate

# On Windows PowerShell:
.venv\Scripts\Activate.ps1

# Upgrade pip and install SEGEL with development and AI dependencies
pip install --upgrade pip
pip install -e ".[dev,ai]"
```

### 1.3 Verify Installed Package Versions
```bash
python -c "
import importlib.metadata
pkgs = ['pytest', 'pytest-cov', 'pytest-asyncio', 'hypothesis', 'mypy', 'bandit', 'ruff', 'cryptography', 'pydantic', 'fastapi']
for p in pkgs:
    print(f'{p}: {importlib.metadata.version(p)}')
"
```

---

## 2. Automated Test Suite Execution

### 2.1 Complete Test Suite with Coverage
Run all 234 unit, integration, property, and adversarial tests:
```bash
pytest --cov=src --cov-report=term-missing -v
```
**Expected Output**:
- `collected 234 items`
- `234 passed`
- `Total coverage: 82.37%` (or $\ge$ 82.0%)
- Exit code: `0`

### 2.2 Adversarial Security Tests Only (AT-001 through AT-045)
```bash
pytest tests/adversarial/test_adversarial.py -v
```
**Expected Output**:
- `25 passed in ~1.5s`

### 2.3 Hypothesis Property-Based Invariant Tests
```bash
pytest tests/unit/test_properties.py -v
```
**Expected Output**:
- `16 passed` (verifies RFC 8785 canonical JSON, Ed25519 bit-flips, and Merkle tree invariants across 100 iterations per test)

---

## 3. Static Code Analysis & Security Scans

### 3.1 Mypy Strict Mode Type Checking
Verify complete type safety across all 41 source files:
```bash
mypy src/ --strict
```
**Expected Output**:
```
Success: no issues found in 41 source files
```
Exit code: `0`

### 3.2 Bandit Application Security Linter
Scan all source code for common vulnerability patterns (CWE-703, injections, insecure temporary files):
```bash
bandit -r src/ -v
```
**Expected Output**:
```
Total lines of code: ~5150
Total issues: 0 (0 High, 0 Medium, 0 Low)
```
Exit code: `0`

### 3.3 Ruff Code Style & Linting Check
Check PEP 8 formatting, import sorting, and flake8 rules:
```bash
ruff check src/
```
**Expected Output**:
```
All checks passed!
```
Exit code: `0`

---

## 4. End-to-End Release Lifecycle Reproduction

Execute the full 18-step synthetic lifecycle and 5 adversarial rejection scenarios:
```bash
python scripts/demo.py
```
**Expected Output Highlights**:
```
[ 1] Author creates a configuration release
[ 2] Bundle validated and manifest created
[ 3] Author signs the manifest
[ 4] Builder produces Origin provenance -> STAMP 1: ORIGIN ✔
[ 5] Inspector: capability extraction + policy evaluation (PASS)
[ 6] AI advisory analysis (skipped/optional)
[ 7] Inspector Signer issues Inspect attestation -> STAMP 2: INSPECT ✔
[ 8] Approvers review payload via QR transfer
[ 9] Approval threshold fulfilled (2-of-3, author excluded) -> STAMP 3: APPROVE ✔
[10] Ledger records candidate release -> STAMP 4: RECORD ✔
[11] Candidate deployed to 2 designated canary units (healthy)
[12] Canary Receivers generate signed health receipts -> STAMP 5: TEST ✔
[13] Promotion Controller evaluates pre-committed criteria (Promoted: True)
[14] Ledger records promotion
[15] General Release Passport assembled
[16] Offline Receiver independently verifies and deploys
[17] Receiver generates signed deployment receipt
[18] Rejection Scenarios:
     - Forged signature rejected ✔
     - Modified content detected ✔
     - Missing stamps prevent deployment ✔
     - Author self-approval blocked ✔
     - Sequence replay / anti-rollback enforced ✔
DEMO COMPLETE — ALL 18 STEPS PASSED (Exit code: 0)
```

---

## 5. Performance & Latency Benchmark Reproduction

Execute the repeatable microbenchmark harness measuring throughput, mean latency, median, and percentiles (P90, P95, P99):
```bash
python scripts/reproduce_benchmarks.py
```
**Expected Output**:
- **Ed25519 Key Generation**: $> 15,000$ ops/sec (Mean latency $< 0.08$ ms)
- **Ed25519 Signing**: $> 20,000$ ops/sec (Mean latency $< 0.05$ ms)
- **Ed25519 Verification**: $> 7,000$ ops/sec (Mean latency $< 0.15$ ms)
- **Transparency Ledger Append**: $> 1,500$ entries/sec (Mean latency $< 0.70$ ms)
- **Deterministic Bundle Build**: $> 800$ bundles/sec (Mean latency $< 1.5$ ms)
- **Candidate Passport Verify**: $> 900$ passports/sec (Mean latency $< 1.2$ ms)
- **General Passport Verify**: $> 800$ passports/sec (Mean latency $< 1.3$ ms)

---

## 6. Docker Compose Lab Reproduction

To verify container isolation and simulated air-gap networking:
```bash
# 1. Build and start all 4 services
docker compose -f lab/compose.yml up --build -d

# 2. Check running status
docker compose -f lab/compose.yml ps

# 3. Verify Release Desk health check
curl -I http://localhost:8000/

# 4. Verify offline unit isolation (network_mode: none)
docker inspect segel-unit-3 --format '{{.HostConfig.NetworkMode}}'
# Expected output: none

# 5. Tear down containers and volumes
docker compose -f lab/compose.yml down -v
```

---

## 7. Command-Line Interface (CLI) Verification

### 7.1 Offline Receiver CLI
```bash
segel-receiver --help
# Displays usage for 'verify', 'status', and 'recover'
```

### 7.2 Air-Gapped Approver CLI
```bash
segel-approver --help
# Displays usage for 'request', 'inspect', and 'sign'
```

### 7.3 Independent Witness CLI
```bash
segel-witness --help
# Displays usage for 'cosign' and 'status'
```

