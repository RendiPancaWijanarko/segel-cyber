# SEGEL Controlled Pilot Deployment Guide

**Target Milestone**: SEGEL Version 0.1.0-MVP  
**Classification**: Infrastructure Architecture & Deployment Engineering  
**Author**: Senior DevOps Engineer & Release Engineer  
**Date**: November 3, 2026  

---

## 1. Pilot Topology Architecture

The SEGEL Controlled Pilot topology enforces strict security boundary isolation across four distinct tiers:

```
┌────────────────────────────────────────────────────────────────────────┐
│ ZONE Z1: AUTHOR & APPROVER TERMINALS (Air-Gapped / Workstations)       │
│                                                                        │
│  [Author Station]               [Approver Quorum (2-of-3)]             │
│   • author.priv.json             • approver_sec.priv.json (group-0)    │
│   • signs manifest               • approver_ops.priv.json (group-1)    │
│                                  • QR Code / Compact Transfer          │
└───────────────────┬───────────────────────────┬────────────────────────┘
                    │ (Release Metadata)         │ (Signed Approvals)
                    ▼                           ▼
┌────────────────────────────────────────────────────────────────────────┐
│ ZONE Z3: CONTROL PLANE (Online Release Desk & Transparency Ledger)     │
│                                                                        │
│  [Release Desk Web UI] <───> [Transparency Ledger] <──> [Witness Node] │
│   • Port 8000                 • SQLite WAL Mode          • Port 8003   │
│   • UNTRUSTED: NO KEYS!       • Merkle Tree Engine       • Cosigner    │
│   • Orchestrates pipeline     • ledger.priv.json         • witness key │
└───────────────────┬────────────────────────────────────────────────────┘
                    │ (Candidate Passport)
                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│ ZONE Z2: CANARY RECEIVERS (Connected Staging Nodes)                    │
│                                                                        │
│  [Canary Node 1]                       [Canary Node 2]                 │
│   • Port 8001                           • Port 8002                    │
│   • canary_1.priv.json                  • canary_2.priv.json           │
│   • Deploys candidate release           • Deploys candidate release    │
│   • Health check: file_exists, config   • Health check: file_exists    │
│   • Emits signed Canary Receipt         • Emits signed Canary Receipt  │
└───────────────────┬────────────────────────────────────────────────────┘
                    │ (2 Valid Signed Receipts)
                    ▼
          [Promotion Controller] ──> Emits General Release Passport
                    │
                    ▼ (Physical Removable Media / USB / Optical Transfer)
┌────────────────────────────────────────────────────────────────────────┐
│ ZONE Z0: OFFLINE PRODUCTION RECEIVER (Network Disabled)                │
│                                                                        │
│  [Offline General Receiver - unit-3]                                   │
│   • ZERO NETWORK INTERFACE (network_mode: none)                        │
│   • receiver_general.priv.json                                         │
│   • Independently verifies all 5 stamps offline                        │
│   • Anti-rollback sequence check                                       │
│   • Applies configuration with read-only permissions (0o444)           │
│   • Emits final signed Deployment Receipt                              │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Infrastructure & Port Specifications

| Service Node | Hostname / IP | Port Binding | Network Isolation Posture | Required Keys |
|:---|:---|:---:|:---|:---|
| **Release Desk** | `segel-control-plane` | `8000/TCP` | Internal LAN / Web Access | **NONE** (Untrusted orchestrator) |
| **Transparency Ledger**| `segel-control-plane` | Local / In-process | Controlled storage | `ledger.priv.json` |
| **Witness Daemon** | `segel-witness-node` | `8003/TCP` | Restricted peer network | `witness.priv.json` |
| **Canary Unit 1** | `segel-canary-1` | `8001/TCP` (or CLI) | Staging network | `canary_1.priv.json` |
| **Canary Unit 2** | `segel-canary-2` | `8002/TCP` (or CLI) | Staging network | `canary_2.priv.json` |
| **Offline General Unit**| `segel-prod-node` | **NONE** | **100% AIR-GAPPED** (`network_mode: none`) | `receiver_general.priv.json` |

---

## 3. Option A: Containerized Lab Deployment (Docker Compose)

For testing and demonstrating the multi-container pilot environment:

### Prerequisites:
- Docker Engine 24.0+
- Docker Compose v2.20+

### Execution:
```bash
# 1. Build and start containers in background
docker compose -f lab/compose.yml up --build -d

# 2. Verify running services
docker compose -f lab/compose.yml ps
```

### Verification:
1. Open web browser to `http://localhost:8000`.
2. Inspect the dashboard:
   - Check that `segel-release-desk` responds with HTTP 200.
   - Note that `segel-unit-3` runs in an isolated network namespace (`network_mode: none`).

### Teardown:
```bash
docker compose -f lab/compose.yml down -v
```

---

## 4. Option B: Bare-Metal / Virtual Machine Deployment

For staging and real-world pilot server deployments:

### 4.1 System Prerequisites
- Operating System: Ubuntu 22.04 LTS / Debian 12 / RHEL 9 / Windows Server 2022.
- Python: Version 3.12 (or 3.14).
- Storage: Minimum 10 GB persistent SSD storage per node.

### 4.2 Installation on Control Plane Node
```bash
# Create service account
sudo groupadd -r segel && sudo useradd -r -g segel -m -d /var/lib/segel segel

# Create standard directory layout
sudo mkdir -p /var/lib/segel/{data,state,artifacts}
sudo mkdir -p /etc/segel/{keys,trust}

# Create virtual environment and install SEGEL
sudo -u segel python3 -m venv /var/lib/segel/venv
sudo -u segel /var/lib/segel/venv/bin/pip install --upgrade pip
sudo -u segel /var/lib/segel/venv/bin/pip install segel

# Set directory permissions
sudo chmod 700 /etc/segel/keys
sudo chmod 755 /etc/segel/trust
sudo chown -R segel:segel /var/lib/segel /etc/segel
```

### 4.3 Key & Trust Provisioning
Execute the key ceremony on a secure station (per [`KEY_MANAGEMENT_GUIDE.md`](file:///c:/Users/Rendi/OneDrive/ドキュメント/Dokumen Pribadi/KOMPETISI/segel-cyber/KEY_MANAGEMENT_GUIDE.md)):
1. Copy `trust_root.json` and `policy.json` to `/etc/segel/trust/` on all nodes.
2. Copy `ledger.priv.json` to `/etc/segel/keys/` on the Control Plane node (`chmod 600`).
3. Copy `witness.priv.json` to `/etc/segel/keys/` on the Witness node (`chmod 600`).
4. Copy `canary_*.priv.json` to `/etc/segel/keys/` on Canary nodes (`chmod 600`).
5. Copy `receiver_general.priv.json` to `/etc/segel/keys/` on the Offline node (`chmod 600`).

### 4.4 Systemd Service Unit for Release Desk
Create `/etc/systemd/system/segel-release-desk.service`:
```ini
[Unit]
Description=SEGEL Release Desk Control Plane
After=network.target

[Service]
Type=simple
User=segel
Group=segel
WorkingDirectory=/var/lib/segel
EnvironmentFile=/etc/segel/release_desk.env
ExecStart=/var/lib/segel/venv/bin/uvicorn release_desk.app:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=5s
ProtectSystem=strict
ReadWritePaths=/var/lib/segel

[Install]
WantedBy=multi-user.target
```

Enable and start the service:
```bash
sudo systemctl daemon-reload
sudo systemctl enable --now segel-release-desk
sudo systemctl status segel-release-desk
```

---

## 5. Offline Node Provisioning (Air-Gapped Unit)

### 5.1 Physical Setup
1. Disconnect all network interfaces (Ethernet, Wi-Fi, Bluetooth).
2. Verify isolation:
   ```bash
   ping -c 1 8.8.8.8 || echo "Zero network confirmed"
   ```

### 5.2 Offline Software Installation
Transfer pre-downloaded Python wheels on encrypted USB media:
```bash
pip install --no-index --find-links=/media/usb/wheels segel
```

### 5.3 Offline Verification & Deployment Command
When a general release bundle and passport are delivered via removable media:
```bash
segel-receiver verify /media/usb/release-42.passport.json \
    --bundle /media/usb/release-42.bundle.tar.gz \
    --trust-root /etc/segel/trust/trust_root.json \
    --policy /etc/segel/trust/policy.json \
    --key /etc/segel/keys/receiver_general.priv.json \
    --unit-id unit-3 \
    --unit-role general \
    --deploy-to /opt/app/config \
    --state-dir /var/lib/segel/state
```

### 5.4 Verification Output
- Verified all 5 stamps: Origin, Inspect, Approve, Record, Test.
- Files deployed to `/opt/app/config` with read-only permissions (`0o444`).
- Signed deployment receipt generated: `/var/lib/segel/state/receipts/release-42.receipt.json`.
- Removable media unmounted and receipts returned to Release Desk for audit closure.

