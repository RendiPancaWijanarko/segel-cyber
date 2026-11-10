# Installation Guide

This document describes how to set up, install dependencies, configure the local AI inspector, and run tests and demonstrations for SEGEL from scratch.

---

## 1. Prerequisites & Environment

- **Operating System**: Windows 11 / Windows 10 (tested), Linux/macOS compatible with appropriate shell scripts.
- **Python Runtime**:
  - **Tested**: Python 3.14.6 (64-bit on Windows).
  - **Untested**: Python 3.12 (the specification target; compatible syntax, but the active test suite was validated under Python 3.14.6).
- **Git**: Modern Git client with command-line tools.
- **Local AI Inference Engine (Optional)**:
  - Ollama installed locally and listening on loopback `http://127.0.0.1:11434`.
  - Model: `qwen3:4b`.
  - *Note*: Live Ollama is optional for running the deterministic core and unit/integration test suites. All automated tests in `tests/` use an in-process scripted `FakeLLM` HTTP server and do not require Ollama.

---

## 2. Virtual Environment Setup

From the repository root:

```powershell
# Create a dedicated virtual environment
python -m venv .venv

# Activate the virtual environment (PowerShell)
.\.venv\Scripts\Activate.ps1
```

*(On Unix/Linux: `source .venv/bin/activate`)*

---

## 3. Package Installation

Install the package in editable mode with development test dependencies:

```powershell
pip install -e ".[dev]"
```

Verify installed core dependencies:
```powershell
pip list
```

Core libraries include `pydantic`, `cryptography`, `fastapi`, `uvicorn`, `jinja2`, `httpx`, and test tools `pytest`, `pytest-asyncio`, `ruff`, `mypy`.

---

## 4. Ollama & Model Setup (For Live AI Advisory Mode)

If evaluating live AI purpose classification:

1. **Install Ollama**: Download and install Ollama from [ollama.com](https://ollama.com).
2. **Start the Ollama daemon**: Ensure Ollama is running and accessible at `http://127.0.0.1:11434`.
3. **Pull the required model**:
   ```powershell
   ollama pull qwen3:4b
   ```
4. **Execute Preflight Script**:
   Run the preflight health check to verify connectivity, model digest, and warm up GPU/CPU weights:
   ```powershell
   powershell -ExecutionPolicy Bypass -File scripts/demo_ai_preflight.ps1
   ```
   Expected output confirms loopback connection, model presence, warm-up latency, and active runner status via `ollama ps`.

---

## 5. Running the Test Suite

Run the full pytest suite (all 433+ tests, zero live network dependencies):

```powershell
pytest
```

To run with compact output:
```powershell
pytest -q
```

To run only the AI acceptance and FakeLLM integration tests:
```powershell
pytest tests/unit/test_ai_fake_llm.py tests/unit/test_ai_acceptance.py tests/unit/test_ai_9b_acceptance.py
```

---

## 6. Running Demonstrations

### A. Automated Scenario Runner (Headless)
Runs all 4 demonstration acts under both `SEGEL_AI_ENABLED=0` and `SEGEL_AI_ENABLED=1`:
```powershell
python scripts/run_demo_scenario.py
```

### B. Interactive Web Release Desk UI
Start the interactive Release Desk web interface:
```powershell
# Start with AI enabled (default)
powershell -ExecutionPolicy Bypass -File scripts/run_demo.ps1

# Start in deterministic-only mode (AI disabled)
powershell -ExecutionPolicy Bypass -File scripts/run_demo.ps1 -AiEnabled 0
```
Open your browser to:
`http://127.0.0.1:8000`

---

## 7. Troubleshooting

| Symptom | Cause | Resolution |
|---------|-------|------------|
| `Connection refused: 127.0.0.1:11434` | Ollama daemon is not running. | Start Ollama before enabling AI, or run with `SEGEL_AI_ENABLED=0`. |
| `model 'qwen3:4b' not found` | Model weights have not been downloaded. | Run `ollama pull qwen3:4b`. |
| `Preflight check: Non-zero exit` | Endpoint unreachable or model mismatch. | Inspect `scripts/demo_ai_preflight.ps1` output for the specific failing stage. |
| `AI analysis failed: TIMEOUT` | First inference cold-start exceeded timeout. | Run `scripts/demo_ai_preflight.ps1` to warm up model weights into memory, or raise `SEGEL_AI_TIMEOUT_S`. |
| `DigestMismatchError on stage()` | Configuration files modified after manifest signing. | Rebuild and resign release manifest if content was changed intentionally. |
| `Sequence <= highest accepted (anti-rollback)` | Sequence number is less than or equal to unit state. | Increment manifest sequence for new release. |
