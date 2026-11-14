# SEGEL End-to-End Demonstration & Execution Guide

**Sistem Edar Gelar Elektronik Lapis-ganda (SEGEL)**  
*Platform Distribusi dan Verifikasi Rilis Konfigurasi Berpaspor Kriptografis Multi-Pihak untuk Satuan Operasional TNI AD*  
**Dokumen Acuan**: PRD v2.0, TAS §8, MDB §9, `AGENTS.md`

---

## 1. Prerequisites & System Requirements

### 1.1 Hardware Requirements
- **Processor**: x86_64 or ARM64 (AVX2 support recommended for inference).
- **RAM**: Minimum 8 GB (16 GB recommended when running Ollama with `qwen3:4b`).
- **Disk Space**: 10 GB free space (includes repository, Python venv, and model weights).

### 1.2 Operating System & Software Dependencies
- **Operating System**: Windows 11 / Windows Server 2022 (tested on Windows 11 Build 26100) or Linux (Ubuntu 22.04+).
- **Python**: Python 3.12+ (verified and tested on **Python 3.14.6**).
- **PowerShell**: PowerShell 5.1+ (Windows built-in) or PowerShell Core 7+.
- **Git**: Git 2.40+.
- **Ollama (Optional for AI Advisory)**: Ollama v0.3.0+ running on local loopback `http://127.0.0.1:11434` with model `qwen3:4b` pulled.
  *(Note: SEGEL functions completely offline without Ollama; deterministic policy verification never depends on the model).*

---

## 2. Environment Setup

### 2.1 Workspace & Virtual Environment
Open PowerShell in the project root directory:

```powershell
# Pastikan terminal berada di direktori root proyek segel-cyber:
# (Jika prompt terminal Anda sudah menampilkan folder segel-cyber, lewati baris cd)
# cd "segel-cyber"

# Verify Python version
python --version
# Expected: Python 3.14.6 or 3.12+

# Activate or create the virtual environment
if (-not (Test-Path ".venv")) {
    python -m venv .venv
}
.\.venv\Scripts\Activate.ps1

# Install editable package with dev dependencies
pip install -e ".[dev]"
```

### 2.2 Environment Variables Configuration
SEGEL operates on strict fail-closed configuration principles per PRD v2.0 §16. Configuration is managed via environment variables or a `.env` file in the project root:

```bash
# Operational Mode: 'demo', 'pilot', or 'production'
SEGEL_MODE=demo

# Logging & Network
SEGEL_LOG_LEVEL=info
SEGEL_HOST=127.0.0.1
SEGEL_PORT=8000

# Storage Directories (Relative paths)
SEGEL_DATA_DIR=lab/data
SEGEL_STATE_DIR=lab/data/state
SEGEL_KEYS_DIR=lab/keys
SEGEL_DEPLOY_ROOT=lab/staging

# Unit Identity
SEGEL_UNIT_ID=canary-1
SEGEL_UNIT_ROLE=canary

# AI Inspector Subsystem (Loopback-only)
SEGEL_AI_ENABLED=1
SEGEL_AI_ENDPOINT=http://127.0.0.1:11434
SEGEL_AI_MODEL=qwen3:4b
SEGEL_AI_TIMEOUT_S=30.0
```

---

## 3. Application Startup Sequence

### 3.1 Step 1: AI Inspector Preflight Check (Optional)
If demonstrating Act 3 (AI Advisory), verify the local Ollama daemon and warm up model weights:

```powershell
powershell -File scripts/demo_ai_preflight.ps1
```

**Expected Result**:
- Loopback connectivity confirmed (`http://127.0.0.1:11434`).
- Model `qwen3:4b` verified with SHA-256 digest.
- Warm-up latency reported (< 2500 ms) and loaded in memory (`keep_alive 30m`).

### 3.2 Step 2: Launch the Release Desk Web Service
Launch the FastAPI Release Desk service using the automated startup script:

```powershell
# Jalankan dengan AI diaktifkan (Ollama loopback)
powershell -ExecutionPolicy Bypass -File scripts/run_demo.ps1 -AiEnabled 1

# Atau jalankan langsung via Python virtual environment (dengan flag --app-dir src)
.\.venv\Scripts\python.exe -m uvicorn release_desk.app:app --app-dir src --host 127.0.0.1 --port 8000 --reload
```

**Console Output**:
```
INFO: Starting SEGEL Release Desk in mode 'demo' on 127.0.0.1:8000
INFO: Storage configuration: data_dir=lab\data, state_dir=lab\data\state, keys_dir=lab\keys
INFO: Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
```

Buka peramban ke alamat: **`http://127.0.0.1:8000`**.

---

## 4. Initial Configuration & Security Posture

At application startup in `demo` mode, `DemoState` initializes an autonomous sovereign testbed:
1. **Trust Root v1**:
   - 7 authority key pairs generated: 1 Author, 1 Builder, 1 Inspector Signer, 2 Approvers (`group-0`, `group-1`), 1 Ledger Signer, 1 Witness.
   - Thresholds: Author (1), Builder (1), Inspector (1), Approvers (2-of-3 threshold with group separation `group-0: 1, group-1: 1`), Ledger (1), Witness (1).
2. **Verification Policy v1**:
   - Monotonic sequence enforcement (anti-rollback).
   - `canary_required_count = 2` (requires healthy health receipts from 2 canary nodes before promotion).
   - `require_warn_acknowledgement = True` (approvers must explicitly sign `acknowledgement_digest` for any `WARN` finding).
3. **Transparency Ledger**:
   - Append-only SQLite Merkle tree (RFC 6962). Initial size = 0 entries; root hash = empty.

---

## 5. Chronological Demonstration Walkthrough (6-Minute Scenario)

### Act 1: Cold Start & Sovereign Verification (30 Seconds)
1. **Navigate to Dashboard (`http://127.0.0.1:8000`)**:
   - Observe the clean, zero-hallucination dashboard:
     - **Task Statistics**: `0` (Siap Gelar).
     - **Stempel Sah Kripto**: `0` (clean histogram).
     - **Satuan Tergelar**: `0 Unit | 0 Paspor`.
     - **Konsensus Kuorum**: `0%` (Menunggu Pengajuan Rilis).
     - **Uji Paspor Selesai**: `0 Lolos` (0 active dots).
     - **Buku Besar Transparansi**: `0 Entri Tercatat` (Akar Kepercayaan 7 Kunci Epoch 1).
2. **Inspect Akar Kepercayaan (`/trust`)**:
   - Click "Akar Kepercayaan" or navigate to `/trust`.
   - Review the 7 authority keys, their roles, and threshold policies.

---

### Act 2: The Golden Path — Clean Configuration Release (2 Minutes)
1. **Create Release (`/release/new`)**:
   - Click **"Rilis Baru"**.
   - Input values:
     - **Release ID**: `BASELINE-UNIT-42`
     - **Sequence**: `1`
     - **Purpose**: `Initial network configuration baseline for Unit 42 tactical post`
     - **Canary Targets**: `canary-1,canary-2`
     - **General Scope**: `canary-1,canary-2,unit-3`
   - Click **"Jalankan Alur Rilis 5-Stempel"**.
2. **Examine Release Detail (`/release/0`)**:
   - **Stamp 1 (Origin)**: Builder provenance envelope signed with Ed25519 DSSE.
   - **Stamp 2 (Inspect)**: Deterministic policy verdict = **PASS** (0 findings).
   - **Stamp 3 (Approve)**: 2-of-2 consensus satisfied (`approver-0` and `approver-1`).
   - **Stamp 4 (Record)**: Appended as Leaf #0 in the Merkle Tree; Checkpoint signed.
   - **Stamp 5 (Test)**: Status = `pending` (awaiting canary deployment).
3. **Deploy to Canary**:
   - Click **"Gelar ke Unit Canary"** (posts to `/release/0/deploy-canary`).
   - Simulates deployment to `canary-1` and `canary-2`.
   - Both units verify the Candidate Passport, execute health probes (`file_exists`, `config_valid`), and return signed health receipts.
   - Stamp 5 lights up green (**VALID**).
4. **Promote to General Fleet**:
   - Click **"Promosikan ke Seluruh Satuan"** (posts to `/release/0/promote`).
   - Promotion Controller evaluates receipts (2 healthy units).
   - Transparency Ledger records `release_promoted` event (Leaf #1).
   - External Witness cosigns the new Checkpoint.
   - General Release Passport is assembled for offline distribution.
5. **Return to Dashboard**:
   - Telemetry dynamically updates:
     - **Task Statistics**: `1` (100% OK, Promoted).
     - **Stempel Sah Kripto**: `9` (5 release stamps + 2 canary receipts + 1 witness cosignature + 2 ledger entries).
     - **Satuan Tergelar**: `3 Unit | 1 Paspor` (`canary-1, canary-2, unit-3`).
     - **Uji Paspor Selesai**: `4 Lolos` (2 units x 2 probes; dots illuminate).
     - **Buku Besar**: `2 Entri Tercatat` (`candidate_recorded`, `release_promoted`).

---

### Act 3: Deterministic Policy Rejection — Fail Closed (1 Minute)
1. **Submit Unauthorized Configuration**:
   - Click **"Rilis Baru"**.
   - Purpose: `Emergency update`
   - In production or automated test harness, candidate introduces `PRULE-004` violation (`privilege: root`).
2. **Observe Fail-Closed Behavior**:
   - Inspector evaluates deterministic rules: elevated privileges trigger immediate **REJECT**.
   - Ledger candidate evidence verifier blocks entry (`ErrorCode.INSPECT_REJECTED`).
   - Approver CLI refuses to sign unverified releases.
   - Pipeline halts immediately with zero state change.

---

### Act 4: Ambiguous Intent & AI Advisory Panel (1.5 Minutes)
1. **Submit `DEV-14` Corpus Release**:
   - Click **"Rilis Baru"**.
   - **Release ID**: `DEV-14-SYNC`
   - **Sequence**: `2`
   - **Purpose**: `Synchronize communication parameters for branch office gateway node`
2. **Observe AI Advisory Panel**:
   - Deterministic keyword classifier (B1) abstains on the general purpose text.
   - With `SEGEL_AI_ENABLED=1`, local model `qwen3:4b` executes in an isolated sandbox subprocess.
   - Model classifies purpose as **`L6` (Vague / Unclassified)** with advisory reason: *"Purpose describes broad synchronization without specifying single class L1-L5."*
   - Merge logic raises inspect verdict to **`WARN`**.
   - Release Desk displays the dedicated **AI Advisory** panel:
     - Clear advisory banner: *"Analisis AI bersifat konsultatif. AI tidak memegang kunci dan tidak dapat menolak rilis secara sepihak."*
     - Predicted class: `L6 (Vague / Unclassified)`
     - Short reason text displayed safely escaped.
     - Approvers are required to submit `acknowledgement_digest` before promotion is permitted.
3. **Honest Architectural Statement**:
   - State clearly to evaluators: *"While the AI flagged DEV-14, a deterministic vague-by-default rule (B1b) flags this exact release without an LLM. The AI's measured value is fewer false alarms rather than unique detection."*

---

### Act 5: Cryptographic Defense & Tamper Evidence (1 Minute)
Demonstrate offline cryptographic rejection using the automated test suite or CLI:
1. **Content Tampering (AT-002)**: Flip 1 byte in the manifest payload -> Receiver verifies PAE digest -> **REJECTED** (`ErrorCode.SIGNATURE_INVALID`).
2. **Sequence Replay (AT-012)**: Replay `sequence=1` when receiver is at `sequence=2` -> **REJECTED** (`ErrorCode.SEQUENCE_REPLAY`).
3. **Author Self-Approval (AT-008)**: Author signs approval payload -> Receiver filters author key (SEC-001) -> Threshold not met -> **BLOCKED** (`ErrorCode.THRESHOLD_NOT_MET`).

---

## 6. Automated Non-Interactive Demonstration Runner

To execute the entire 6-minute scenario non-interactively with structured console output:

```powershell
python scripts/run_demo_scenario.py
```

**Expected Script Summary**:
```
[PREFLIGHT] Ollama warm-up request completed in 1.42s
[ACT 1] Clean release BASELINE-UNIT-42 created, inspected, approved, recorded, canary-tested, and promoted.
[ACT 2] Malicious release rejected by PRULE-004 fail-closed policy gate.
[ACT 3] DEV-14 evaluated: AI OFF -> SKIPPED; AI ON -> WARN (Class L6).
[ACT 4] Cryptographic tampering and sequence replay successfully blocked.
ALL DEMO SCENARIOS PASSED.
```

---

## 7. Verification and Validation Checklist

| Checkpoint | Method / URL | Expected State |
| :--- | :--- | :--- |
| **Service Health** | `GET /healthz` | `HTTP 200`, `status: "healthy"`, `service: "segel-release-desk"` |
| **Trust Root** | `GET /trust` | 7 authority keys, root version 1, epoch 1 |
| **Ledger Consistency** | `GET /ledger` | Sequential Merkle entries, valid SHA-256 leaf hashes |
| **Clean Reset** | `POST /reset` | `{"status": "reset"}`, releases cleared, ledger reset |
| **Full Test Suite** | `pytest` | **436 passed, 0 failed** in ~45 seconds |
| **Static Code Quality** | `ruff check .` | **All checks passed!** |
| **Type Safety** | `mypy src` | **Success: no issues found in 53 source files** |

---

## 8. Troubleshooting & Recovery

### 8.1 Port 8000 Already in Use
If port 8000 is occupied:
```powershell
# Check listening process
Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue | Select-Object OwningProcess

# Or launch Release Desk on an alternate port
powershell -ExecutionPolicy Bypass -File scripts/run_demo.ps1 -Port 8080
# Or: .\.venv\Scripts\python.exe -m uvicorn release_desk.app:app --app-dir src --host 127.0.0.1 --port 8080
```

### 8.2 Ollama Inference Unreachable / Model Missing
If Ollama is offline or `qwen3:4b` is not installed:
- SEGEL degrades gracefully: `ai_status` is marked as `failed` or `skipped`.
- A warning banner appears on the Release Detail page: *"AI inspection service is unavailable. Release verification proceeded with deterministic rules."*
- Deterministic security verification continues completely uninterrupted.

### 8.3 Resetting Demo State
To restore the demonstration environment to a pristine zero-state at any time:
- Click the **"Reset"** button on the Release Desk dashboard table header, or
- Send `POST /reset` via curl or PowerShell:
  ```powershell
  Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/reset
  ```

---

## 9. Application Shutdown

To cleanly terminate the demonstration environment:
1. In the terminal running Uvicorn / Release Desk, press `Ctrl + C`.
2. The lifespan handler executes:
   - `demo.ledger.close()` releases SQLite connection locks cleanly.
   - Temporary file descriptors are flushed.
3. If Ollama was loaded, it unloads automatically after the 30-minute keep-alive window expires, or unload manually via:
   ```bash
   ollama stop qwen3:4b
   ```
