# SEGEL Environment Configuration Reference

**Target Milestone**: SEGEL Version 0.1.0-MVP  
**Classification**: Configuration Governance & Operations Reference  
**Author**: Senior DevOps Engineer & Application Security Engineer  
**Date**: November 3, 2026  

---

## 1. Configuration Overview

SEGEL services and utilities read operational parameters from system environment variables (or a local `.env` file loaded at startup).

The configuration architecture is implemented in [`src/segel_core/config.py`](file:///c:/Users/Rendi/OneDrive/ドキュメント/Dokumen Pribadi/KOMPETISI/segel-cyber/src/segel_core/config.py) and verified by unit tests in [`tests/unit/test_config.py`](file:///c:/Users/Rendi/OneDrive/ドキュメント/Dokumen Pribadi/KOMPETISI/segel-cyber/tests/unit/test_config.py).

### Core Security Rules
1. **Zero Private Keys in Environment Variables**: Private keys are NEVER passed as environment variables or command-line arguments. They are read strictly from restricted filesystem paths (`0o600`).
2. **Fail-Closed Validation**: If an invalid environment variable is supplied (e.g. unknown `SEGEL_MODE`, invalid port, or malformed role), the service immediately terminates during startup with a descriptive error message.
3. **No Secret Exposure in Logs**: Configuration dump functions filter and sanitize all paths and identifiers.

---

## 2. Environment Variables Inventory

The following table documents every environment variable recognized by SEGEL:

| Variable Name | Type | Default Value | Allowed Values | Applicable Modes | Description |
|:---|:---:|:---:|:---:|:---:|:---|
| **`SEGEL_MODE`** | `string` | `demo` | `demo`, `pilot`, `production` | All | Operational mode posture. In `demo` mode, synthetic in-memory keys and ledger are permitted. In `pilot` and `production`, external trust root and persistent storage are mandatory. |
| **`SEGEL_LOG_LEVEL`** | `string` | `info` | `debug`, `info`, `warning`, `error`, `critical` | All | Logging verbosity for ASGI application, ledger events, and receiver execution. |
| **`SEGEL_HOST`** | `string` | `0.0.0.0` | IP address or hostname | Release Desk | Network interface IP address for Release Desk web dashboard binding. |
| **`SEGEL_PORT`** | `integer` | `8000` | `1` – `65535` | Release Desk | TCP port for Release Desk web dashboard binding. |
| **`SEGEL_DATA_DIR`** | `path` | `/var/lib/segel` | Valid directory path | Pilot, Prod | Root directory for persistent data, SQLite ledger databases, and release staging. |
| **`SEGEL_STATE_DIR`** | `path` | `/var/lib/segel/state` | Valid directory path | Receiver | Directory for persisting receiver monotonic sequence state (`receiver_state.json`) and journal. |
| **`SEGEL_KEYS_DIR`** | `path` | `/etc/segel/keys` | Valid directory path | Pilot, Prod | Directory holding local node private (`*.priv.json`) and public (`*.pub.json`) keys. |
| **`SEGEL_DEPLOY_ROOT`**| `path` | `/opt/app/config` | Valid directory path | Receiver | Target directory where verified releases are applied by the deployment adapter. |
| **`SEGEL_UNIT_ID`** | `string` | `unit-local` | Alphanumeric identifier | Receiver | Unique node identifier (e.g., `canary-1`, `canary-2`, `unit-3`, `edge-node-42`). |
| **`SEGEL_UNIT_ROLE`** | `string` | `general` | `canary`, `general` | Receiver | Node deployment role. Canary units can accept candidate passports; general units require general passports. |
| **`OLLAMA_HOST`** | `url` | `http://127.0.0.1:11434`| Valid HTTP URL | Release Desk (Optional) | Endpoint for optional AI advisory analysis. If unreachable, AI evaluation is gracefully skipped without blocking. |
| **`OLLAMA_MODEL`** | `string` | `llama3:8b` | Valid Ollama model name | Release Desk (Optional) | LLM model tag requested for non-authoritative configuration analysis. |

---

## 3. Template Configuration File (`.env.example`)

A clean template is maintained in the root directory: [`.env.example`](file:///c:/Users/Rendi/OneDrive/ドキュメント/Dokumen Pribadi/KOMPETISI/segel-cyber/.env.example).

```dotenv
# SEGEL Environment Configuration Template
# Copy this file to .env and adjust values for your environment.

# Operational Mode: 'demo', 'pilot', or 'production'
SEGEL_MODE=pilot

# Logging verbosity: 'debug', 'info', 'warning', 'error'
SEGEL_LOG_LEVEL=info

# Release Desk Web Dashboard Binding
SEGEL_HOST=0.0.0.0
SEGEL_PORT=8000

# File Storage Paths
SEGEL_DATA_DIR=/var/lib/segel
SEGEL_STATE_DIR=/var/lib/segel/state
SEGEL_KEYS_DIR=/etc/segel/keys
SEGEL_DEPLOY_ROOT=/opt/app/config

# Receiver Identity Settings
SEGEL_UNIT_ID=canary-1
SEGEL_UNIT_ROLE=canary

# Optional AI Advisory Engine (Ollama)
OLLAMA_HOST=http://127.0.0.1:11434
OLLAMA_MODEL=llama3:8b
```

---

## 4. Startup Validation & Error Handling

When [`load_config()`](file:///c:/Users/Rendi/OneDrive/ドキュメント/Dokumen Pribadi/KOMPETISI/segel-cyber/src/segel_core/config.py#L42) executes during service startup:
1. **Mode Checking**: If `SEGEL_MODE` is not in `{"demo", "pilot", "production"}`, raises `ValueError: Invalid SEGEL_MODE '...'`.
2. **Port Range Checking**: If `SEGEL_PORT` is non-integer or outside `1-65535`, raises `ValueError: Invalid SEGEL_PORT '...'`.
3. **Role Validation**: If `SEGEL_UNIT_ROLE` is not in `{"canary", "general"}`, raises `ValueError: Invalid SEGEL_UNIT_ROLE '...'`.
4. **Directory Validation**: Calling `config.validate_directories()` in non-demo mode verifies that `data_dir`, `state_dir`, and `deploy_root` exist or creates them automatically with parents.

---

## 5. Configuration Profiles by Environment Tier

### Profile 1: Local Development / Demonstration (Tier A / B)
- `SEGEL_MODE=demo`
- `SEGEL_DATA_DIR` and `SEGEL_KEYS_DIR` can remain defaults; ephemeral in-memory state is utilized.
- No external services required.

### Profile 2: Staging / Controlled Pilot (Tier C)
- `SEGEL_MODE=pilot`
- `SEGEL_DATA_DIR=/var/lib/segel`
- `SEGEL_KEYS_DIR=/etc/segel/keys`
- Dedicated environment files created per host:
  - **Release Desk Node**: `SEGEL_PORT=8000`, `SEGEL_LOG_LEVEL=info`
  - **Canary Node 1**: `SEGEL_UNIT_ID=canary-1`, `SEGEL_UNIT_ROLE=canary`, `SEGEL_DEPLOY_ROOT=/opt/app/config`
  - **Canary Node 2**: `SEGEL_UNIT_ID=canary-2`, `SEGEL_UNIT_ROLE=canary`, `SEGEL_DEPLOY_ROOT=/opt/app/config`
  - **Offline General Unit**: `SEGEL_UNIT_ID=unit-3`, `SEGEL_UNIT_ROLE=general`, `SEGEL_DEPLOY_ROOT=/opt/app/config`

