# SEGEL Backup & Disaster Recovery Guide

**Target Milestone**: SEGEL Version 0.1.0-MVP  
**Classification**: Business Continuity & Disaster Recovery (BCDR)  
**Author**: Production Readiness Specialist & Senior DevOps Engineer  
**Date**: November 3, 2026  

---

## 1. Backup Scope & Asset Classification

The SEGEL platform maintains five critical state assets requiring structured backup and recovery protocols:

| Asset Name | Primary Path | State Mutability | Recovery Point Objective (RPO) | Recovery Time Objective (RTO) | Backup Technique |
|:---|:---|:---:|:---:|:---:|:---|
| **Transparency Ledger** | `/var/lib/segel/ledger.db` | High (Append-only) | $\le$ 1 hour | $\le$ 15 minutes | Online SQLite backup via [`scripts/backup_ledger.py`](file:///c:/Users/Rendi/OneDrive/ドキュメント/Dokumen Pribadi/KOMPETISI/segel-cyber/scripts/backup_ledger.py) |
| **Receiver Sealed State**| `/var/lib/segel/state/receiver_state.json` | Moderate (per release) | 0 (Reconstructible)| $\le$ 5 minutes | Write-then-rename atomic journal |
| **Cryptographic Keys** | `/etc/segel/keys/*.priv.json` | Low (Key ceremony) | 0 (Static until rotation) | $\le$ 1 hour | Encrypted cold storage (USB / PGP) |
| **Trust Root & Policy**| `/etc/segel/trust/*.json` | Low (Epoch updates) | 0 (Version controlled) | $\le$ 5 minutes | Git repository & out-of-band archive |
| **Target Deployed Config**| `/opt/app/config/` | High (on deploy) | 0 (Backed up by adapter)| $\le$ 2 minutes | Automated pre-deploy snapshot / backup |

---

## 2. Transparency Ledger Backup Procedures

### 2.1 Automated Scheduled Online Backup
Configure a cron job on the Control Plane node (`/etc/cron.d/segel-ledger-backup`):
```cron
# Run online ledger backup every hour at minute 15
15 * * * * segel /var/lib/segel/venv/bin/python /var/lib/segel/scripts/backup_ledger.py backup --source /var/lib/segel/ledger.db --target /var/backups/segel/ledger_$(date +\%Y\%m\%d_\%H00).db >> /var/log/segel/backup.log 2>&1
```

### 2.2 Retention Policy
- Hourly backups retained for 48 hours.
- Daily backups retained for 30 days.
- Weekly backups retained for 1 year.
Automated retention cleanup script:
```bash
find /var/backups/segel/ -name "ledger_*.db" -mtime +30 -delete
```

---

## 3. Cryptographic Key Cold Storage

Private keys MUST NEVER be backed up unencrypted or stored on network-attached storage (NAS).

### Cold Storage Ceremony Protocol:
1. Export private keys encrypted using AES-256-GCM or OpenPGP with a multi-person passphrase.
2. Write encrypted keys to two separate, air-gapped USB hardware-encrypted drives (Drive A and Drive B).
3. Deposit Drive A in a primary physical security safe; deposit Drive B in a separate off-site geographic facility.

---

## 4. Disaster Recovery & Reconstruction Procedures

### 4.1 Scenario A: Ledger Node Total Hardware Loss
When provisioning a new Control Plane host after complete failure:

1. **Deploy Base System**: Install OS, Python 3.12, and SEGEL package per [`PILOT_DEPLOYMENT_GUIDE.md`](file:///c:/Users/Rendi/OneDrive/ドキュメント/Dokumen Pribadi/KOMPETISI/segel-cyber/PILOT_DEPLOYMENT_GUIDE.md).
2. **Restore Ledger Database**:
   ```bash
   cp /mnt/bcdr/ledger_backup_latest.db /var/lib/segel/ledger.db
   chown segel:segel /var/lib/segel/ledger.db
   chmod 600 /var/lib/segel/ledger.db
   ```
3. **Verify Merkle Tree & Checkpoint**:
   ```bash
   python scripts/backup_ledger.py verify --file /var/lib/segel/ledger.db
   ```
4. **Restore Ledger Private Key**:
   Retrieve `ledger.priv.json` from cold storage and place in `/etc/segel/keys/` (`chmod 600`).
5. **Start Service**:
   ```bash
   systemctl start segel-release-desk
   ```
6. **Witness Synchronization**:
   The Witness node checks the restored checkpoint against its last cosigned size. If consistent, normal release processing resumes.

---

### 4.2 Scenario B: Receiver Crash or Mid-Deployment Failure
If a power failure or process abort occurs while files are being copied to `/opt/app/config`:

1. The Receiver's atomic write-then-rename journal detects an uncommitted deployment state.
2. The Receiver automatically sets `recovery_mode: true` to fail closed and block further deployments.
3. The operator executes:
   ```bash
   segel-receiver recover --state-dir /var/lib/segel/state --deploy-to /opt/app/config
   ```
4. The adapter restores the pre-deployment snapshot from `.backup/`, deletes incomplete `.staging/` files, verifies filesystem integrity, and clears `recovery_mode: false`.

---

## 5. Verification & Drill Exercises

Every 30 days during controlled pilot operations, the operations team must execute a simulated disaster recovery drill:
1. Spin up a temporary sandbox VM.
2. Restore the latest automated ledger backup.
3. Verify that `python scripts/backup_ledger.py verify` exits with code 0.
4. Verify that the reloaded Merkle root matches the live witness daemon's last cosigned root hash.
5. Record the drill result in the monthly audit log.

