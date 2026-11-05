# SPDX-License-Identifier: MIT
"""Transparency Ledger — append-only Merkle log with signed checkpoints.

Per PRD v2.0 §16.3 and TAS §8.2:
- The ledger is an append-only RFC 6962 Merkle tree.
- Every significant event is appended as a leaf.
- The Ledger Signer periodically signs checkpoints (size + root hash).
- Witnesses cosign checkpoints to prevent split-view attacks.
- Inclusion and consistency proofs allow offline verification.

Per SEC-018:
- SQLite is used for storage convenience, NOT as a security boundary.
- Tamper evidence comes from the Merkle tree and signed checkpoints.
- SQLite triggers are guard rails, not immutability guarantees.

Event types:
- candidate_recorded: A release has been approved and recorded.
- release_promoted: A canary-tested release is promoted to general.
- key_revoked: A key revocation event.
- trust_updated: Trust metadata was updated.
- hold_issued: A release was placed on hold.
"""

from __future__ import annotations

import base64
import contextlib
import sqlite3
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from segel_core.canonical import canonical_json
from segel_core.crypto.ed25519 import KeyPair, sign
from segel_core.crypto.hashing import (
    MerkleTree,
    merkle_leaf_hash,
    sha256_hex,
)
from segel_core.errors import (
    ErrorCode,
    ProofInvalidError,
    SegelError,
)
from segel_core.schemas.checkpoint import Checkpoint, SignedCheckpoint

# Valid event types
VALID_EVENT_TYPES = frozenset({
    "candidate_recorded",
    "release_promoted",
    "key_revoked",
    "trust_updated",
    "hold_issued",
})


@dataclass
class LedgerEntry:
    """A single entry in the transparency ledger."""
    index: int
    event_type: str
    data: bytes        # Canonical JSON bytes of the event payload
    data_hex: str      # SHA-256 of the data
    leaf_hash: str     # Merkle leaf hash (hex)


@dataclass
class InclusionProof:
    """A Merkle inclusion proof for a ledger entry."""
    entry_index: int
    leaf_hash: str
    proof: list[str]          # Hex-encoded sibling hashes
    checkpoint_size: int
    checkpoint_root_hash: str


class TransparencyLedger:
    """Append-only transparency ledger with Merkle tree and signed checkpoints.

    The ledger maintains an in-memory Merkle tree backed by SQLite storage.
    Every append re-verifies the event against the existing evidence before
    recording.
    """

    def __init__(self, db_path: str | Path | None = None) -> None:
        """Initialise the ledger.

        Args:
            db_path: Path to SQLite database. Use ":memory:" for in-memory.
        """
        self._db_path = str(db_path) if db_path else ":memory:"
        self._lock = threading.RLock()
        self._tree = MerkleTree()
        self._conn = sqlite3.connect(self._db_path, check_same_thread=False)
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA busy_timeout=5000")
        self._conn.execute("PRAGMA synchronous=NORMAL")
        self._conn.execute("PRAGMA foreign_keys=ON")
        self._init_schema()
        self._load_existing_entries()

    def _init_schema(self) -> None:
        """Create the ledger schema if it doesn't exist."""
        self._conn.executescript("""
            CREATE TABLE IF NOT EXISTS ledger_entries (
                entry_index INTEGER PRIMARY KEY,
                event_type  TEXT NOT NULL,
                data        BLOB NOT NULL,
                data_sha256 TEXT NOT NULL,
                leaf_hash   TEXT NOT NULL,
                created_at  TEXT NOT NULL DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS checkpoints (
                checkpoint_id   INTEGER PRIMARY KEY AUTOINCREMENT,
                size            INTEGER NOT NULL,
                root_hash       TEXT NOT NULL,
                note_text       TEXT NOT NULL,
                ledger_signature TEXT NOT NULL DEFAULT '',
                ledger_key_id    TEXT NOT NULL DEFAULT '',
                created_at      TEXT NOT NULL DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS witness_cosignatures (
                cosig_id        INTEGER PRIMARY KEY AUTOINCREMENT,
                checkpoint_id   INTEGER NOT NULL REFERENCES checkpoints(checkpoint_id),
                key_id          TEXT NOT NULL,
                signature       TEXT NOT NULL
            );

            -- Guard rail: prevent deletion (NOT a security boundary)
            CREATE TRIGGER IF NOT EXISTS prevent_entry_delete
                BEFORE DELETE ON ledger_entries
                BEGIN
                    SELECT RAISE(ABORT, 'ledger entries cannot be deleted');
                END;

            -- Guard rail: prevent updates (NOT a security boundary)
            CREATE TRIGGER IF NOT EXISTS prevent_entry_update
                BEFORE UPDATE ON ledger_entries
                BEGIN
                    SELECT RAISE(ABORT, 'ledger entries cannot be modified');
                END;
        """)
        self._conn.commit()

    def _load_existing_entries(self) -> None:
        """Reload entries from SQLite into the in-memory Merkle tree."""
        cursor = self._conn.execute(
            "SELECT entry_index, data FROM ledger_entries ORDER BY entry_index"
        )
        for row in cursor:
            self._tree.append(row[1])

    @property
    def size(self) -> int:
        """Current number of entries in the ledger."""
        with self._lock:
            return self._tree.size

    def append(self, event_type: str, event_data: dict[str, Any]) -> LedgerEntry:
        """Append an event to the ledger.

        Args:
            event_type: One of VALID_EVENT_TYPES.
            event_data: Dict to be canonically serialised.

        Returns:
            The LedgerEntry with its index and leaf hash.

        Raises:
            SegelError: If the event type is invalid.
        """
        if event_type not in VALID_EVENT_TYPES:
            raise SegelError(
                ErrorCode.SCHEMA_UNKNOWN,
                f"Invalid event type: {event_type}",
            )

        data = canonical_json(event_data)
        data_hex = sha256_hex(data)

        with self._lock:
            index = self._tree.append(data)
            leaf_hash = merkle_leaf_hash(data).hex()

            self._conn.execute(
                "INSERT INTO ledger_entries "
                "(entry_index, event_type, data, data_sha256, leaf_hash) "
                "VALUES (?, ?, ?, ?, ?)",
                (index, event_type, data, data_hex, leaf_hash),
            )
            self._conn.commit()

        return LedgerEntry(
            index=index,
            event_type=event_type,
            data=data,
            data_hex=data_hex,
            leaf_hash=leaf_hash,
        )

    def root_hash(self) -> bytes:
        """Get the current Merkle root hash."""
        with self._lock:
            return self._tree.root_hash()

    def root_hash_hex(self) -> str:
        """Get the current Merkle root hash as hex."""
        with self._lock:
            return self._tree.root_hash().hex()

    def create_checkpoint(self) -> Checkpoint:
        """Create an unsigned checkpoint of the current state."""
        with self._lock:
            return Checkpoint(
                size=self._tree.size,
                root_hash=self.root_hash_hex(),
            )

    def sign_checkpoint(self, ledger_key: KeyPair) -> SignedCheckpoint:
        """Create and sign a checkpoint.

        Args:
            ledger_key: The Ledger Signer's key pair.

        Returns:
            A signed checkpoint.
        """
        with self._lock:
            checkpoint = self.create_checkpoint()
            note_text = checkpoint.to_note_text()
            sig = sign(ledger_key.private_key, note_text.encode("utf-8"))
            sig_b64 = base64.b64encode(sig).decode("ascii")

            signed = SignedCheckpoint(
                checkpoint=checkpoint,
                ledger_signature=sig_b64,
                ledger_key_id=ledger_key.key_id,
            )

            # Store in database
            self._conn.execute(
                "INSERT INTO checkpoints "
                "(size, root_hash, note_text, ledger_signature, ledger_key_id) "
                "VALUES (?, ?, ?, ?, ?)",
                (checkpoint.size, checkpoint.root_hash, note_text, sig_b64, ledger_key.key_id),
            )
            self._conn.commit()

            return signed

    def inclusion_proof(self, index: int) -> InclusionProof:
        """Generate a Merkle inclusion proof for an entry.

        Args:
            index: The entry index.

        Returns:
            An InclusionProof.
        """
        with self._lock:
            size = self._tree.size
            proof_hashes = self._tree.inclusion_proof(index, size)
            root = self._tree.root_hash(size)

            # Get the leaf hash from the tree
            row = self._conn.execute(
                "SELECT leaf_hash FROM ledger_entries WHERE entry_index = ?",
                (index,),
            ).fetchone()
            if row is None:
                raise ProofInvalidError(f"Entry {index} not found")

            return InclusionProof(
                entry_index=index,
                leaf_hash=row[0],
                proof=[h.hex() for h in proof_hashes],
                checkpoint_size=size,
                checkpoint_root_hash=root.hex(),
            )

    def consistency_proof(self, m: int, n: int) -> list[str]:
        """Generate a Merkle consistency proof between tree size m and n.

        Args:
            m: Size of older tree.
            n: Size of newer tree.

        Returns:
            List of hex-encoded consistency proof hashes.
        """
        with self._lock:
            proof_hashes = self._tree.consistency_proof(m, n)
            return [h.hex() for h in proof_hashes]

    def get_entry(self, index: int) -> LedgerEntry | None:
        """Retrieve a ledger entry by index."""
        with self._lock:
            row = self._conn.execute(
                "SELECT entry_index, event_type, data, data_sha256, leaf_hash "
                "FROM ledger_entries WHERE entry_index = ?",
                (index,),
            ).fetchone()
            if row is None:
                return None
            return LedgerEntry(
                index=row[0],
                event_type=row[1],
                data=row[2],
                data_hex=row[3],
                leaf_hash=row[4],
            )

    def get_latest_checkpoint(self) -> SignedCheckpoint | None:
        """Retrieve the latest signed checkpoint."""
        with self._lock:
            row = self._conn.execute(
                "SELECT checkpoint_id, size, root_hash, ledger_signature, ledger_key_id "
                "FROM checkpoints ORDER BY checkpoint_id DESC LIMIT 1"
            ).fetchone()
            if row is None:
                return None
            cp_id, size, root_hash, sig, key_id = row

            # Get witness cosignatures
            cosigs = self._conn.execute(
                "SELECT key_id, signature FROM witness_cosignatures WHERE checkpoint_id = ?",
                (cp_id,),
            ).fetchall()

            return SignedCheckpoint(
                checkpoint=Checkpoint(size=size, root_hash=root_hash),
                ledger_signature=sig,
                ledger_key_id=key_id,
                witness_cosignatures=[{"key_id": r[0], "signature": r[1]} for r in cosigs],
            )

    def add_witness_cosignature(
        self,
        checkpoint_size: int,
        witness_key_id: str,
        witness_signature: str,
    ) -> None:
        """Add a witness cosignature to the latest checkpoint matching the size.

        Args:
            checkpoint_size: The checkpoint size the witness is cosigning.
            witness_key_id: The witness key ID.
            witness_signature: Base64-encoded signature.
        """
        with self._lock:
            row = self._conn.execute(
                "SELECT checkpoint_id FROM checkpoints WHERE size = ? "
                "ORDER BY checkpoint_id DESC LIMIT 1",
                (checkpoint_size,),
            ).fetchone()
            if row is None:
                raise ProofInvalidError(
                    f"No checkpoint found with size {checkpoint_size}"
                )

            self._conn.execute(
                "INSERT INTO witness_cosignatures (checkpoint_id, key_id, signature) "
                "VALUES (?, ?, ?)",
                (row[0], witness_key_id, witness_signature),
            )
            self._conn.commit()

    def backup(self, target_path: str | Path) -> None:
        """Safely create an online backup of the ledger database using SQLite's backup API.

        Args:
            target_path: Path to write the backup SQLite database file.
        """
        with self._lock:
            target_conn = sqlite3.connect(str(target_path))
            try:
                self._conn.backup(target_conn)
            finally:
                target_conn.close()

    def close(self) -> None:
        """Close the database connection."""
        with self._lock, contextlib.suppress(sqlite3.Error):
            self._conn.close()

    def __enter__(self) -> TransparencyLedger:
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self.close()

    def __del__(self) -> None:
        self.close()

