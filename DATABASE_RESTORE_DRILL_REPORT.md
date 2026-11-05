# SEGEL Database Concurrency & Disaster Recovery Drill Report

**Auditor**: Independent Application Security Engineer & DevOps Auditor  
**Target Milestone**: SEGEL MVP Version 0.1.0-MVP  
**Execution Date**: November 3, 2026  
**Final Status**: **VERIFIED PASS (THREAD-SAFE SINGLE-WRITER & RECOVERABLE)**

---

## 1. Executive Summary & Verification Objective

The previous audit introduced `threading.RLock()`, `PRAGMA busy_timeout = 5000`, and `TransparencyLedger.backup()` to address SQLite WAL concurrency.

This independent audit conducted adversarial and stress testing to answer two questions:
1. **Does thread-level locking guarantee multi-process concurrency safety?**
2. **Can a live ledger database be backed up online, restored to a fresh location, verified cryptographically, and successfully resume write operations?**

### Key Findings
1. **Thread-Level Safety (Verified PASS)**: 8 concurrent threads executing 400 simultaneous appends within a single process executed with zero deadlocks, zero lock contention failures, and strictly consecutive indices `0` through `399`.
2. **Multi-Process Architecture Boundary (Critical Insight)**: `threading.RLock()` protects threads within the same process address space only. Because `TransparencyLedger` maintains an in-memory **RFC 6962 Merkle Tree** (`self._tree`), concurrent active-active writes from multiple independent OS processes to the same SQLite file trigger SQLite primary key collisions (`UNIQUE constraint failed: ledger_entries.entry_index`). Therefore, **the Transparency Ledger is architecturally a Single-Writer Service**.
3. **Disaster Recovery & Restore Viability (Verified PASS)**: A live database with 440 entries was backed up hot, restored to an independent filesystem path, verified against its signed checkpoint Merkle root, and resumed appending with index `440` and size `441`.

---

## 2. Multi-Threaded In-Process Concurrency Verification

### 2.1 Execution Details
- **Harness**: [`scripts/verify_concurrency_and_restore_drill.py`](file:///c:/Users/Rendi/OneDrive/ドキュメント/Dokumen Pribadi/KOMPETISI/segel-cyber/scripts/verify_concurrency_and_restore_drill.py)
- **Worker Configuration**: 8 worker threads (`concurrent.futures.ThreadPoolExecutor`)
- **Operations**: 50 appends per thread = 400 total simultaneous writes
- **SQLite Pragmas**: `journal_mode=WAL`, `busy_timeout=5000`, `synchronous=NORMAL`, `foreign_keys=ON`

### 2.2 Execution Results
```text
--- 1. Multi-Threaded In-Process Concurrency Test ---
    [OK] Successfully executed 400 concurrent appends across 8 threads.
    [OK] Verified strictly consecutive indices 0..399 without race conditions.
    [OK] Checkpoint signed for size=400, root=cb7fa14e8710fab5...
```
- **Total Unique Indices**: 400
- **Sequence Gaps / Duplicates**: 0
- **Lock Contention Failures**: 0

---

## 3. Multi-Process Concurrency Boundary Analysis

### 3.1 Multi-Process Experiment
To verify whether thread-level locking extends across processes, two independent OS processes (`multiprocessing.Process`) were spawned simultaneously against a shared SQLite file `multiprocess_ledger.db`.

### 3.2 Observed Behavior
1. Process 1 and Process 2 initialize independent `TransparencyLedger` instances with their own in-memory `MerkleTree`.
2. When Process 1 and Process 2 concurrently call `ledger.append()`:
   - Both processes consult their local in-memory tree, determine next index is `0`.
   - SQLite file locking serializes the physical writes.
   - The first process commits entry `0`.
   - The second process attempts to execute `INSERT INTO ledger_entries (entry_index, ...) VALUES (0, ...)`.
   - SQLite raises:
     ```text
     sqlite3.IntegrityError: UNIQUE constraint failed: ledger_entries.entry_index
     ```

### 3.3 Architectural Conclusion & Deployment Invariant
> [!CAUTION]
> `threading.RLock()` does **NOT** provide multi-process safety.
> 
> The Transparency Ledger MUST be deployed as a **Single-Writer Service** (either in-process with the Release Desk or as a dedicated single-instance daemon). Active-active multi-worker setups (such as `uvicorn --workers 4`) attempting direct concurrent writes to the same `ledger.db` file will fail closed on SQLite integrity constraints.

---

## 4. Live Disaster Recovery & Database Restore Drill

### 4.1 Step-by-Step Drill Execution
The drill executed the complete disaster recovery lifecycle:
1. **Live Ledger Population**: 440 releases appended; Checkpoint signed for size `440`, root `a79b12f5b14cf920...`.
2. **Online Hot Backup**: `TransparencyLedger.backup(backup_path)` executed non-blocking via the SQLite Online Backup API.
3. **Live Mutation**: 10 additional releases appended to the live database (size `450`), demonstrating that the backup represents a consistent point-in-time snapshot.
4. **Disaster Recovery (Restore)**: Backup file restored to a completely fresh directory `restored_ledger.db`.
5. **Restored Integrity Verification**:
   - Total Entries in Restored DB: `440` (matches pre-backup size exactly).
   - Merkle Tree Recalculation: `a79b12f5b14cf920...` (matches pre-backup root).
   - Latest Checkpoint Integrity: Validated matching size `440` and root.
   - RFC 6962 Inclusion Proof: Validated on entry `#25` against checkpoint root.
6. **Post-Restore Resumption**:
   - New entry appended to restored database: assigned index `440`, size `441`.
   - New checkpoint signed and validated for size `441`.

### 4.2 Raw Drill Log
```text
--- 3. Database Online Backup, Disaster Recovery & Restore Drill ---
    [OK] Live ledger populated with 440 entries. Root: a79b12f5b14cf920...
    [OK] Online backup written to: C:\Users\...\backup_ledger.db
    [OK] Live ledger mutated to 450 entries (backup represents point-in-time snapshot).
    [OK] Restored backup file to: C:\Users\...\restored_ledger.db
    [OK] Restored ledger integrity verified. Checkpoint matches Merkle root: a79b12f5b14cf920...
    [OK] RFC 6962 inclusion proof verified on restored entry #25.
    [OK] Post-restore append successful: new entry index=440, size=441.
```

---

## 5. Verification Verdict

- **Gate G2 (Database & Data Integrity)**: **`PASS (WITH DOCUMENTED SINGLE-WRITER CONSTRAINT)`**
- Multi-threaded safety within the single-writer instance is 100% verified.
- Online hot backup and point-in-time disaster recovery are empirically validated.
- Operational constraint formally documented: **Single-Writer Ledger Topology Mandatory**.

