# SEGEL Pilot Pre-Flight Configuration Checklist

**Target Milestone**: SEGEL Version 0.1.0-MVP  
**Classification**: Operational Commissioning & Release Sign-Off  
**Author**: Production Readiness Specialist & Senior QA Engineer  
**Date**: November 3, 2026  

---

## Instructions for Operators

This checklist must be executed sequentially and signed off before declaring SEGEL operational for a controlled pilot deployment. Every check has an explicit verification command and expected output.

---

## 1. System & Runtime Prerequisites

- [ ] **1.1 Python Version Verification**
  - Command: `python3 -c "import sys; assert sys.version_info >= (3, 12), 'Python >= 3.12 required'; print(sys.version)"`
  - Expected: Python 3.12+ (or 3.14).
  - Signed off by: ____________________ Date: __________

- [ ] **1.2 Clean Virtual Environment Installation**
  - Command: `python3 -m venv .venv && . .venv/bin/activate && pip install -e .`
  - Expected: Successful installation of `segel` and dependencies (`cryptography`, `pydantic`, `fastapi`, `uvicorn`, `jinja2`, `cbor2`, `qrcode`, `pillow`).
  - Signed off by: ____________________ Date: __________

- [ ] **1.3 Automated Test Suite Execution**
  - Command: `pytest --cov=src`
  - Expected: `244 passed`, code coverage $\ge$ 80.0% (Current verified: 83.30%).
  - Signed off by: ____________________ Date: __________

- [ ] **1.4 Static Typing & Linter Verification**
  - Commands: `mypy src/ --strict` and `ruff check src/`
  - Expected: `Success: no issues found in 42 source files` and `All checks passed!`.
  - Signed off by: ____________________ Date: __________

- [ ] **1.5 Security Linting (Bandit)**
  - Command: `bandit -r src/ -q`
  - Expected: `No issues identified` (0 High, 0 Medium, 0 Low).
  - Signed off by: ____________________ Date: __________

---

## 2. Cryptographic Key Ceremony & File Security

- [ ] **2.1 Formal Pilot Key Generation**
  - Command: `python scripts/init_keys.py --output-dir /etc/segel/keys --trust-dir /etc/segel/trust --mode pilot`
  - Expected: 11 Ed25519 keypairs generated across roles; `trust_root.json` and `policy.json` written.
  - Signed off by: ____________________ Date: __________

- [ ] **2.2 Private Key Permission Lockdown (POSIX)**
  - Command: `chmod 700 /etc/segel/keys && chmod 600 /etc/segel/keys/*.priv.json`
  - Verification: `ls -la /etc/segel/keys/` shows `-rw-------` permissions on all `.priv.json` files.
  - Signed off by: ____________________ Date: __________

- [ ] **2.3 Key Separation Across Nodes**
  - Ensure Release Desk host does **NOT** contain `author.priv.json`, `approver_*.priv.json`, or receiver keys.
  - Verification: `test ! -f /etc/segel/keys/author.priv.json` on Release Desk.
  - Signed off by: ____________________ Date: __________

---

## 3. Trust Metadata Distribution

- [ ] **3.1 Out-of-Band Trust Root Installation**
  - Copy `/etc/segel/trust/trust_root.json` and `policy.json` to all nodes.
  - Verification: SHA-256 digest of `trust_root.json` matches across Control Plane, Canary nodes, and Offline receiver.
  - Signed off by: ____________________ Date: __________

- [ ] **3.2 Policy Configuration Review**
  - Inspect `/etc/segel/trust/policy.json`:
    - `approval_threshold`: `2`
    - `approval_groups`: `{"group-0": 1, "group-1": 1}`
    - `canary_required_count`: `2`
    - `freshness_mode`: `"strict"`
  - Signed off by: ____________________ Date: __________

---

## 4. Control Plane & Transparency Ledger

- [ ] **4.1 Directory Creation & Permissions**
  - Command: `mkdir -p /var/lib/segel/{data,state,artifacts} && chown -R segel:segel /var/lib/segel`
  - Signed off by: ____________________ Date: __________

- [ ] **4.2 Transparency Ledger Database Initialization**
  - Verification: Database created with `PRAGMA journal_mode=WAL`, `PRAGMA busy_timeout=5000`, and SQL triggers active.
  - Signed off by: ____________________ Date: __________

- [ ] **4.3 Automated Backup Scheduled**
  - Command: Verify cron entry in `/etc/cron.d/segel-ledger-backup`.
  - Test run: `python scripts/backup_ledger.py backup --source /var/lib/segel/ledger.db --target /var/backups/segel/test_backup.db`
  - Verification: `python scripts/backup_ledger.py verify --file /var/backups/segel/test_backup.db` returns PASSED.
  - Signed off by: ____________________ Date: __________

---

## 5. Canary Receiver Nodes (Staging)

- [ ] **5.1 Canary Unit 1 Provisioning**
  - Host: `segel-canary-1`
  - Key installed: `canary_1.priv.json` (`0o600`)
  - Target deploy directory: `/opt/app/config`
  - Signed off by: ____________________ Date: __________

- [ ] **5.2 Canary Unit 2 Provisioning**
  - Host: `segel-canary-2`
  - Key installed: `canary_2.priv.json` (`0o600`)
  - Target deploy directory: `/opt/app/config`
  - Signed off by: ____________________ Date: __________

---

## 6. Offline Production Receiver (Air-Gap)

- [ ] **6.1 Zero-Network Verification**
  - Network cables disconnected; Wi-Fi and Bluetooth disabled.
  - Command: `ip route` shows no default gateway; `ping -c 1 8.8.8.8` fails immediately.
  - Signed off by: ____________________ Date: __________

- [ ] **6.2 Offline Unit Key & Trust Provisioning**
  - Host: `segel-prod-node` (`unit-3`)
  - Key installed: `receiver_general.priv.json` (`0o600`)
  - Trust metadata installed: `/etc/segel/trust/trust_root.json`
  - Signed off by: ____________________ Date: __________

- [ ] **6.3 Deployment Directory Preparation**
  - Target directory `/opt/app/config` exists with write permissions for `segel` user during apply, locked to `0o444` post-deploy.
  - Signed off by: ____________________ Date: __________

---

## 7. Synthetic End-to-End Pilot Rehearsal

- [ ] **7.1 18-Step Lifecycle Execution**
  - Command: `python scripts/demo.py`
  - Expected: All 18 lifecycle steps and 5 rejection scenarios pass with code 0.
  - Signed off by: ____________________ Date: __________

- [ ] **7.2 Offline Isolation Verification Test**
  - Command: `pytest tests/unit/test_receiver_offline_isolation.py -v`
  - Expected: 2 tests passed; network isolation assertions succeed.
  - Signed off by: ____________________ Date: __________

- [ ] **7.3 Concurrency & Backup Test**
  - Command: `pytest tests/unit/test_ledger_concurrency.py -v`
  - Expected: 3 tests passed without lock contention.
  - Signed off by: ____________________ Date: __________

---

## 8. Final Commissioning Sign-Off

| Authority | Name / Role | Decision | Signature & Date |
|:---|:---|:---:|:---|
| **Senior DevOps Engineer** | Lead Infrastructure Engineer | **APPROVED** | ____________________ |
| **Release Engineer** | Pipeline & Delivery Lead | **APPROVED** | ____________________ |
| **Application Security Engineer**| Lead Security Auditor | **APPROVED** | ____________________ |
| **Production Readiness Specialist**| Operations & Quality Lead | **APPROVED** | ____________________ |

