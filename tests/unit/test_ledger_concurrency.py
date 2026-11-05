# SPDX-License-Identifier: MIT
"""Concurrency and backup/restore tests for TransparencyLedger."""

from __future__ import annotations

import concurrent.futures
from pathlib import Path

from ledger.ledger import TransparencyLedger
from segel_core.crypto.ed25519 import generate_keypair
from segel_core.crypto.hashing import verify_inclusion_from_hash


def test_concurrent_ledger_appends(tmp_path: Path) -> None:
    """Verify that multiple concurrent threads can append to the ledger without data races."""
    db_file = tmp_path / "concurrent_ledger.db"
    ledger = TransparencyLedger(db_file)

    num_threads = 6
    appends_per_thread = 25
    total_appends = num_threads * appends_per_thread

    def worker(thread_id: int) -> list[int]:
        indexes = []
        for i in range(appends_per_thread):
            event_data = {
                "event_type": "candidate_recorded",
                "release_id": f"RELEASE-{thread_id}-{i}",
                "sequence": i + 1,
                "manifest_sha256": "0" * 64,
            }
            entry = ledger.append("candidate_recorded", event_data)
            indexes.append(entry.index)
        return indexes

    with concurrent.futures.ThreadPoolExecutor(max_workers=num_threads) as executor:
        futures = [executor.submit(worker, t) for t in range(num_threads)]
        all_indexes: list[int] = []
        for f in concurrent.futures.as_completed(futures):
            all_indexes.extend(f.result())

    # All indexes should be unique and cover 0 to total_appends - 1
    assert len(all_indexes) == total_appends
    assert sorted(all_indexes) == list(range(total_appends))
    assert ledger.size == total_appends

    original_root = ledger.root_hash()
    ledger.close()

    # Reopen database and verify Merkle tree rebuild matches perfectly
    reloaded_ledger = TransparencyLedger(db_file)
    assert reloaded_ledger.size == total_appends
    assert reloaded_ledger.root_hash() == original_root

    # Verify inclusion proof on a random entry
    proof = reloaded_ledger.inclusion_proof(42)
    verify_inclusion_from_hash(
        leaf_hash=bytes.fromhex(proof.leaf_hash),
        index=42,
        size=total_appends,
        proof=[bytes.fromhex(h) for h in proof.proof],
        expected_root=bytes.fromhex(proof.checkpoint_root_hash),
    )
    reloaded_ledger.close()


def test_concurrent_reads_and_writes(tmp_path: Path) -> None:
    """Verify concurrent readers and writers operate without locking collisions."""
    db_file = tmp_path / "rw_ledger.db"
    ledger = TransparencyLedger(db_file)

    # Seed initial entries
    for i in range(10):
        ledger.append("candidate_recorded", {"release_id": f"INIT-{i}", "sequence": 1})

    writer_count = 4
    reader_count = 4
    iterations = 20

    def writer_task(tid: int) -> None:
        for i in range(iterations):
            ledger.append(
                "candidate_recorded",
                {"release_id": f"W-{tid}-{i}", "sequence": i + 1},
            )

    def reader_task() -> None:
        for _ in range(iterations * 2):
            s = ledger.size
            if s > 0:
                _ = ledger.root_hash()
                _ = ledger.get_entry(0)

    with concurrent.futures.ThreadPoolExecutor(max_workers=writer_count + reader_count) as ex:
        writer_futs = [ex.submit(writer_task, i) for i in range(writer_count)]
        reader_futs = [ex.submit(reader_task) for _ in range(reader_count)]

        for f in concurrent.futures.as_completed(writer_futs + reader_futs):
            f.result()

    expected_size = 10 + (writer_count * iterations)
    assert ledger.size == expected_size
    ledger.close()


def test_ledger_online_backup_and_recovery(tmp_path: Path) -> None:
    """Verify online backup and state recovery of the TransparencyLedger."""
    db_file = tmp_path / "live_ledger.db"
    backup_file = tmp_path / "backup_ledger.db"
    ledger = TransparencyLedger(db_file)
    ledger_key = generate_keypair()

    for i in range(20):
        ledger.append(
            "candidate_recorded",
            {"release_id": f"REL-{i}", "sequence": 1, "manifest_sha256": "f" * 64},
        )

    signed_cp = ledger.sign_checkpoint(ledger_key)
    live_root = ledger.root_hash()
    live_size = ledger.size

    # Perform online backup
    ledger.backup(backup_file)

    # Add more entries to live ledger to prove backup represents snapshot
    ledger.append("candidate_recorded", {"release_id": "POST-BACKUP", "sequence": 2})
    assert ledger.size == live_size + 1
    ledger.close()

    # Verify backup database can be loaded as independent ledger
    restored = TransparencyLedger(backup_file)
    assert restored.size == live_size
    assert restored.root_hash() == live_root

    # Verify checkpoint is intact in restored database
    cp = restored.get_latest_checkpoint()
    assert cp is not None
    assert cp.checkpoint.size == signed_cp.checkpoint.size
    assert cp.checkpoint.root_hash == signed_cp.checkpoint.root_hash
    assert cp.ledger_signature == signed_cp.ledger_signature

    restored.close()
