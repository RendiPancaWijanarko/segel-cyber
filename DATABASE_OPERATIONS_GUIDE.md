# SEGEL Database Operations & Storage Readiness Guide

**Target Milestone**: SEGEL Version 0.1.0-MVP  
**Classification**: Database Architecture & Storage Operations  
**Author**: Production Readiness Specialist & Senior DevOps Engineer  
**Date**: November 3, 2026  

---

## 1. Storage Architecture Overview

Per **PRD v2.0 §16.3** and **TAS §8.2**, the SEGEL Transparency Ledger operates as an append-only **RFC 6962 Merkle log** backed by **SQLite 3**.

### Security Boundary Clarification (SEC-018)
> [!IMPORTANT]
> SQLite is utilized strictly as a structured storage engine and convenience layer, **NOT** as the cryptographic security boundary.
> 
> Tamper evidence and auditability are guaranteed by:
> 1. In-memory and persisted **RFC 6962 Merkle Tree** leaf and internal hashes.
> 2. Periodically signed **Ledger Checkpoints** (`size` + `root_hash`).
> 3. Cosignatures by independent **Witness Daemons** (`CHECKPOINT_FORK` detection).
> 
> Application-level SQL triggers prevent unintended accidental deletion or update, but cryptographic verification makes unauthorized direct modification of the raw `.db` file immediately detectable.

---

## 2. Database Schema & Guard Rails

The database schema is initialized automatically by [`TransparencyLedger._init_schema()`](file:///c:/Users/Rendi/OneDrive/ドキュメント/Dokumen Pribadi/KOMPETISI/segel-cyber/src/ledger/ledger.py#L99-L143):

### 2.1 Tables
```sql
CREATE TABLE IF NOT EXISTS ledger_entries (
    entry_index INTEGER PRIMARY KEY,
    event_type  TEXT NOT NULL,
    data        BLOB NOT NULL,
    data_sha256 TEXT NOT NULL,
    leaf_hash   TEXT NOT NULL,
    created_at  TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS checkpoints (
    checkpoint_id    INTEGER PRIMARY KEY AUTOINCREMENT,
    size             INTEGER NOT NULL,
    root_hash        TEXT NOT NULL,
    note_text        TEXT NOT NULL,
    ledger_signature TEXT NOT NULL DEFAULT '',
    ledger_key_id    TEXT NOT NULL DEFAULT '',
    created_at       TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS witness_cosignatures (
    cosig_id      INTEGER PRIMARY KEY AUTOINCREMENT,
    checkpoint_id INTEGER NOT NULL REFERENCES checkpoints(checkpoint_id),
    key_id        TEXT NOT NULL,
    signature     TEXT NOT NULL
);
```

### 2.2 SQL Guard Rails (Triggers)
```sql
CREATE TRIGGER IF NOT EXISTS prevent_entry_delete
    BEFORE DELETE ON ledger_entries
    BEGIN
        SELECT RAISE(ABORT, 'ledger entries cannot be deleted');
    END;

CREATE TRIGGER IF NOT EXISTS prevent_entry_update
    BEFORE UPDATE ON ledger_entries
    BEGIN
        SELECT RAISE(ABORT, 'ledger entries cannot be modified');
    END;
```

---

## 3. Concurrency & Performance Tuning

To support high-throughput concurrent access and prevent database locking errors under multi-threaded FastAPI / Uvicorn execution, [`TransparencyLedger`](file:///c:/Users/Rendi/OneDrive/ドキュメント/Dokumen Pribadi/KOMPETISI/segel-cyber/src/ledger/ledger.py) initializes SQLite with the following operational pragmas and mutex locking:

1. **Write-Ahead Logging (WAL Mode)**:
   ```sql
   PRAGMA journal_mode=WAL;
   ```
   Enables simultaneous concurrent readers and one writer without blocking.
2. **Busy Timeout**:
   ```sql
   PRAGMA busy_timeout=5000;
   ```
   Locks wait up to 5,000 milliseconds for transactions to complete before raising `OperationalError`.
3. **Synchronous Normal**:
   ```sql
   PRAGMA synchronous=NORMAL;
   ```
   Optimal trade-off for WAL mode; ensures durable database transactions with minimal disk fsync overhead.
4. **Foreign Key Enforcement**:
   ```sql
   PRAGMA foreign_keys=ON;
   ```
   Enforces relational integrity between checkpoints and witness cosignatures.
5. **Thread-Safe Mutex Locking (`threading.RLock`)**:
   All database operations and in-memory Merkle tree state modifications are wrapped in re-entrant lock acquisitions (`with self._lock:`). Verified by concurrency tests in [`tests/unit/test_ledger_concurrency.py`](file:///c:/Users/Rendi/OneDrive/ドキュメント/Dokumen Pribadi/KOMPETISI/segel-cyber/tests/unit/test_ledger_concurrency.py) across 6–8 simultaneous threads without data races.

---

## 4. Online Backup Operations

Database backups MUST NEVER be taken using standard OS file copying (`cp` or `copy`) while the database is actively being written, as this can capture a torn page state between the `.db` and `.db-wal` files.

### 4.1 Automated Online Backup CLI
Use the dedicated script [`scripts/backup_ledger.py`](file:///c:/Users/Rendi/OneDrive/ドキュメント/Dokumen Pribadi/KOMPETISI/segel-cyber/scripts/backup_ledger.py):

```bash
python scripts/backup_ledger.py backup \
    --source /var/lib/segel/ledger.db \
    --target /var/backups/segel/ledger_backup_$(date +%Y%m%d_%H%M%S).db
```

### 4.2 How Online Backup Works
1. Acquires the internal ledger mutex.
2. Invokes the official SQLite Online Backup API: `self._conn.backup(target_conn)`.
3. Flushes all WAL pages into the target database file atomically.
4. Closes the target connection and automatically runs an integrity verification.

---

## 5. Backup Verification & Consistency Check

To verify the cryptographic and structural integrity of a backup without modifying it:

```bash
python scripts/backup_ledger.py verify --file /var/backups/segel/ledger_backup.db
```

### Expected Output:
```
[*] Verifying cryptographic integrity of: /var/backups/segel/ledger_backup.db
    - Total Ledger Entries: 42
    - Current Merkle Root:  a8f3b49c...
    - Latest Checkpoint Size: 42
    - Checkpoint Root Hash:   a8f3b49c...
    - Ledger Signature Present: True
    - Witness Cosignatures:   1
[+] Integrity check PASSED: Checkpoint matches reconstructed Merkle root.
[+] Backup database verified successfully.
```

---

## 6. Disaster Recovery & Database Restoration

If the live ledger database becomes corrupted, disk-exhausted, or damaged:

### Step 1: Stop Writing Services
```bash
systemctl stop segel-release-desk
```

### Step 2: Quarantine Damaged Database
```bash
mv /var/lib/segel/ledger.db /var/lib/segel/ledger.db.corrupt_$(date +%s)
mv /var/lib/segel/ledger.db-wal /var/lib/segel/ledger.db-wal.corrupt_$(date +%s) 2>/dev/null || true
mv /var/lib/segel/ledger.db-shm /var/lib/segel/ledger.db-shm.corrupt_$(date +%s) 2>/dev/null || true
```

### Step 3: Restore Verified Backup
```bash
cp /var/backups/segel/ledger_backup_latest.db /var/lib/segel/ledger.db
chmod 600 /var/lib/segel/ledger.db
chown segel:segel /var/lib/segel/ledger.db
```

### Step 4: Verify Merkle Integrity
```bash
python scripts/backup_ledger.py verify --file /var/lib/segel/ledger.db
```

### Step 5: Restart Services
```bash
systemctl start segel-release-desk
```

---

## 7. Storage Capacity & Disk-Space Planning

- **Entry Size**: Canonical JSON event records average 250–600 bytes.
- **Index & Hash Storage**: SHA-256 hashes require 32 bytes raw (64 bytes hex).
- **Growth Estimate**:
  - 1,000 releases $\approx$ 1.5 MB database file.
  - 100,000 releases $\approx$ 150 MB database file.
- **Recommendation**: Provision at least 10 GB persistent SSD storage for `/var/lib/segel` with 20% minimum free space alert threshold.

