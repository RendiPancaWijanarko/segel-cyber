# SEGEL Environment Setup & Infrastructure Guide

**Target System**: SEGEL MVP Version 0.1.0-MVP  
**Audience**: DevOps Engineers, System Administrators, and Infrastructure Leads  
**Purpose**: Complete, reproducible setup guide for deploying SEGEL across host systems, virtual machines, and containers  

---

## 1. System Requirements & Architecture Overview

SEGEL operates across four logical tiers:
1. **Tier A (Development/Test)**: In-memory or local temporary directory (`lab/data`).
2. **Tier B (Demonstration Lab)**: Containerized multi-service lab (`lab/compose.yml`).
3. **Tier C (Controlled Pilot)**: Distributed nodes with air-gapped network namespaces and verified storage.
4. **Tier D (Enterprise Production)**: Hardware Security Modules (HSM) and multi-witness quorum (v2.1).

### Minimum Hardware Specifications
- **Release Desk & Ledger Host**: 2 vCPU, 4 GB RAM, 20 GB NVMe/SSD storage.
- **Witness Node**: 1 vCPU, 2 GB RAM, 10 GB storage.
- **Canary Receiver Nodes**: 1 vCPU, 1 GB RAM, 5 GB storage.
- **Air-Gapped General Receiver Nodes**: 1 vCPU, 1 GB RAM, 5 GB storage, zero network interfaces.

### Supported Operating Systems
- Debian 12 (Bookworm) / Ubuntu 22.04 LTS / Ubuntu 24.04 LTS (Primary target).
- Windows Server 2022 / Windows 11 64-bit (Supported with PowerShell / ACLs).

---

## 2. Operating System & Python 3.12 Runtime Setup

### 2.1 Debian / Ubuntu Linux Setup
```bash
# 1. Update system packages
sudo apt-get update && sudo apt-get install -y --no-install-recommends \
    python3.12 \
    python3.12-venv \
    python3.12-dev \
    libffi-dev \
    git \
    curl

# 2. Create unprivileged service user
sudo groupadd -r segel
sudo useradd -r -g segel -u 10001 -m -d /home/segel -s /usr/sbin/nologin segel

# 3. Clone repository and set up virtual environment
sudo -u segel bash -c "
git clone <repository_url> /home/segel/segel
cd /home/segel/segel
python3.12 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -e '.[dev]'
"
```

### 2.2 Docker Container Setup
The repository includes a production-ready, non-root [`Dockerfile`](file:///c:/Users/Rendi/OneDrive/ドキュメント/Dokumen Pribadi/KOMPETISI/segel-cyber/Dockerfile) based on `python:3.12-slim`:
```bash
# Build the image
docker build -t segel:0.1.0 .

# Verify Python version inside container
docker run --rm segel:0.1.0 python --version
# Expected: Python 3.12.x
```

---

## 3. Directory Structure & Permission Lockdown

SEGEL enforces strict directory and file permissions to maintain separation of duties:

```bash
# 1. Configuration & Key Store
sudo mkdir -p /etc/segel/keys
sudo chmod 700 /etc/segel/keys
sudo chown -R segel:segel /etc/segel

# 2. Data & Ledger Directory
sudo mkdir -p /var/lib/segel/state
sudo chmod 700 /var/lib/segel
sudo chown -R segel:segel /var/lib/segel

# 3. Target Deployment Root (where release files will be written)
sudo mkdir -p /opt/app/config
sudo chmod 755 /opt/app/config
sudo chown segel:segel /opt/app/config

# 4. Hot Backup Archive
sudo mkdir -p /var/backups/segel
sudo chmod 700 /var/backups/segel
sudo chown -R segel:segel /var/backups/segel
```

---

## 4. Environment Variables Configuration

Copy `.env.example` to `.env` in the working directory:

```bash
cp .env.example .env
```

### Complete Environment Variable Reference Table

| Variable Name | Default Value | Pilot Recommended | Description |
|---|---|---|---|
| `SEGEL_MODE` | `demo` | `pilot` | Operating posture: `demo`, `pilot`, or `production`. |
| `SEGEL_LOG_LEVEL` | `info` | `info` | Logging verbosity: `debug`, `info`, `warning`, `error`. |
| `SEGEL_HOST` | `0.0.0.0` | `127.0.0.1` | Release Desk web dashboard bind IP. |
| `SEGEL_PORT` | `8000` | `8000` | Release Desk web dashboard listening port. |
| `SEGEL_DATA_DIR` | `/var/lib/segel` | `/var/lib/segel` | Persistent root storage for SQLite WAL ledger. |
| `SEGEL_STATE_DIR` | `/var/lib/segel/state` | `/var/lib/segel/state` | Persistent storage for Receiver sequence & journals. |
| `SEGEL_KEYS_DIR` | `/etc/segel/keys` | `/etc/segel/keys` | Storage directory for local role private/public keys. |
| `SEGEL_DEPLOY_ROOT`| `/opt/app/config` | `/opt/app/config` | Baseline deployment target root. |
| `SEGEL_UNIT_ID` | `unit-local` | `<hostname>` | Unique node identifier (e.g. `canary-1`, `unit-3`). |
| `SEGEL_UNIT_ROLE` | `general` | `canary` or `general` | Receiver operational tier. |
| `OLLAMA_HOST` | `http://127.0.0.1:11434` | (Optional) | Endpoint for LLM advisory analysis. |
| `OLLAMA_MODEL` | `llama3:8b` | `llama3:8b` | Ollama model tag. |

---

## 5. System Service Configuration (systemd)

To run SEGEL as managed, resilient background services on Linux hosts, deploy the following unit files:

### 5.1 Release Desk Service (`/etc/systemd/system/segel-release-desk.service`)
```ini
[Unit]
Description=SEGEL Release Desk Control Plane & Transparency Ledger
After=network.target

[Service]
Type=simple
User=segel
Group=segel
WorkingDirectory=/home/segel/segel
EnvironmentFile=/home/segel/segel/.env
ExecStart=/home/segel/segel/.venv/bin/uvicorn release_desk.app:app --host 0.0.0.0 --port 8000 --workers 1
Restart=always
RestartSec=5
LimitNOFILE=65536

# Hardening
ProtectSystem=full
ProtectHome=read-only
ReadWritePaths=/var/lib/segel /var/backups/segel

[Install]
WantedBy=multi-user.target
```

> [!IMPORTANT]
> The Release Desk service must always specify `--workers 1` because the Transparency Ledger enforces Single-Writer consistency for its in-memory RFC 6962 tree.

### 5.2 Witness Daemon Service (`/etc/systemd/system/segel-witness.service`)
```ini
[Unit]
Description=SEGEL Independent Ledger Witness Daemon
After=network.target

[Service]
Type=simple
User=segel
Group=segel
WorkingDirectory=/home/segel/segel
EnvironmentFile=/home/segel/segel/.env
ExecStart=/home/segel/segel/.venv/bin/segel-witness serve --key /etc/segel/keys/witness.priv.json --port 8080
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

### 5.3 Automated Hot Backup Timer (`/etc/systemd/system/segel-backup.timer`)
```ini
[Unit]
Description=Run SEGEL Ledger Hot Backup Daily

[Timer]
OnCalendar=*-*-* 02:00:00
Persistent=true

[Install]
WantedBy=timers.target
```

Corresponding Service (`/etc/systemd/system/segel-backup.service`):
```ini
[Unit]
Description=SEGEL Ledger Online Hot Backup

[Service]
Type=oneshot
User=segel
WorkingDirectory=/home/segel/segel
ExecStart=/home/segel/segel/.venv/bin/python scripts/backup_ledger.py backup --source /var/lib/segel/ledger.db --target /var/backups/segel/ledger_%Y%m%d_%H%M%S.db
```

---

## 6. Synthetic Demonstration Lab (Docker Compose)

For local multi-node demonstration and testing without dedicated physical machines, run the verified Docker Compose lab:

```bash
# 1. Validate compose configuration
docker compose -f lab/compose.yml config

# 2. Start all services in the background
docker compose -f lab/compose.yml up -d --build

# 3. Check status
docker compose -f lab/compose.yml ps
```

The lab topology boots:
- `segel-release-desk` on port `8000`.
- `segel-canary-1` and `segel-canary-2` simulating online canary receivers.
- `segel-unit-3` running with `network_mode: none` simulating an air-gapped receiver.

---

## 7. Verification & Health Monitoring

Verify service status:

```bash
# 1. Query Release Desk diagnostic endpoint
curl -s http://localhost:8000/healthz | jq .
# Expected output:
# {
#   "status": "healthy",
#   "service": "segel-release-desk",
#   "mode": "demo",
#   "ledger_size": 0,
#   "epoch": 1
# }

# 2. Check Receiver CLI status
segel-receiver status --state-dir /var/lib/segel/state

# 3. Verify SQLite WAL mode on live ledger
sqlite3 /var/lib/segel/ledger.db "PRAGMA journal_mode;"
# Expected output: wal
```

