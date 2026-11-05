# SPDX-License-Identifier: MIT
"""Unit tests for the Transparency Ledger.

Tests append, checkpoints, inclusion proofs, witness cosignatures,
and event type validation.
"""

import pytest

from ledger.ledger import TransparencyLedger, VALID_EVENT_TYPES
from segel_core.crypto.ed25519 import generate_keypair, verify
from segel_core.crypto.hashing import sha256_hex, verify_inclusion, merkle_leaf_hash
from segel_core.canonical import canonical_json
from segel_core.errors import SegelError, ProofInvalidError


class TestLedgerAppend:
    """Test ledger.append()."""

    def test_append_returns_entry(self):
        ledger = TransparencyLedger()
        entry = ledger.append("candidate_recorded", {"test": True})
        assert entry.index == 0
        assert entry.event_type == "candidate_recorded"
        assert len(entry.leaf_hash) == 64
        assert len(entry.data_hex) == 64

    def test_append_increments_index(self):
        ledger = TransparencyLedger()
        e0 = ledger.append("candidate_recorded", {"seq": 0})
        e1 = ledger.append("release_promoted", {"seq": 1})
        e2 = ledger.append("candidate_recorded", {"seq": 2})
        assert e0.index == 0
        assert e1.index == 1
        assert e2.index == 2
        assert ledger.size == 3

    def test_append_invalid_event_type(self):
        ledger = TransparencyLedger()
        with pytest.raises(SegelError, match="Invalid event type"):
            ledger.append("invalid_type", {"data": "test"})

    def test_all_valid_event_types(self):
        ledger = TransparencyLedger()
        for i, event_type in enumerate(VALID_EVENT_TYPES):
            entry = ledger.append(event_type, {"index": i})
            assert entry.event_type == event_type

    def test_leaf_hash_is_merkle_leaf(self):
        ledger = TransparencyLedger()
        data = {"key": "value"}
        entry = ledger.append("candidate_recorded", data)
        expected_leaf = merkle_leaf_hash(canonical_json(data)).hex()
        assert entry.leaf_hash == expected_leaf

    def test_data_is_canonical_json(self):
        ledger = TransparencyLedger()
        data = {"z": 1, "a": 2}
        entry = ledger.append("candidate_recorded", data)
        expected = canonical_json(data)
        assert entry.data == expected


class TestLedgerSize:
    """Test ledger size tracking."""

    def test_empty_ledger(self):
        ledger = TransparencyLedger()
        assert ledger.size == 0

    def test_size_after_appends(self):
        ledger = TransparencyLedger()
        for i in range(5):
            ledger.append("candidate_recorded", {"i": i})
        assert ledger.size == 5


class TestLedgerCheckpoint:
    """Test checkpoint creation and signing."""

    def test_create_checkpoint(self):
        ledger = TransparencyLedger()
        ledger.append("candidate_recorded", {"test": True})
        cp = ledger.create_checkpoint()
        assert cp.size == 1
        assert len(cp.root_hash) == 64
        assert cp.origin == "segel-ledger-v1"

    def test_sign_checkpoint(self):
        ledger = TransparencyLedger()
        ledger.append("candidate_recorded", {"test": True})
        key = generate_keypair()
        signed = ledger.sign_checkpoint(key)
        assert signed.checkpoint.size == 1
        assert signed.ledger_key_id == key.key_id
        assert len(signed.ledger_signature) > 0

    def test_checkpoint_signature_verifiable(self):
        ledger = TransparencyLedger()
        ledger.append("candidate_recorded", {"test": True})
        key = generate_keypair()
        signed = ledger.sign_checkpoint(key)

        import base64
        sig = base64.b64decode(signed.ledger_signature)
        note_text = signed.checkpoint.to_note_text().encode("utf-8")
        # Should not raise
        verify(key.public_key, sig, note_text)

    def test_get_latest_checkpoint(self):
        ledger = TransparencyLedger()
        ledger.append("candidate_recorded", {"test": True})
        key = generate_keypair()
        ledger.sign_checkpoint(key)
        latest = ledger.get_latest_checkpoint()
        assert latest is not None
        assert latest.checkpoint.size == 1

    def test_no_checkpoint_returns_none(self):
        ledger = TransparencyLedger()
        assert ledger.get_latest_checkpoint() is None


class TestLedgerInclusionProof:
    """Test Merkle inclusion proofs."""

    def test_single_entry_proof(self):
        ledger = TransparencyLedger()
        entry = ledger.append("candidate_recorded", {"test": True})
        proof = ledger.inclusion_proof(0)
        assert proof.entry_index == 0
        assert proof.leaf_hash == entry.leaf_hash
        assert proof.checkpoint_size == 1
        assert len(proof.checkpoint_root_hash) == 64

    def test_proof_verifiable(self):
        ledger = TransparencyLedger()
        data = {"key": "value"}
        entry = ledger.append("candidate_recorded", data)
        proof = ledger.inclusion_proof(0)

        # Verify using the raw data
        verify_inclusion(
            entry.data,
            proof.entry_index,
            proof.checkpoint_size,
            [bytes.fromhex(h) for h in proof.proof],
            bytes.fromhex(proof.checkpoint_root_hash),
        )

    def test_multi_entry_proofs(self):
        ledger = TransparencyLedger()
        entries = []
        for i in range(7):
            e = ledger.append("candidate_recorded", {"i": i})
            entries.append(e)

        for i in range(7):
            proof = ledger.inclusion_proof(i)
            verify_inclusion(
                entries[i].data,
                proof.entry_index,
                proof.checkpoint_size,
                [bytes.fromhex(h) for h in proof.proof],
                bytes.fromhex(proof.checkpoint_root_hash),
            )

    def test_nonexistent_entry(self):
        ledger = TransparencyLedger()
        ledger.append("candidate_recorded", {"test": True})
        with pytest.raises(ProofInvalidError):
            ledger.inclusion_proof(999)


class TestLedgerGetEntry:
    """Test entry retrieval."""

    def test_get_existing_entry(self):
        ledger = TransparencyLedger()
        ledger.append("candidate_recorded", {"test": True})
        entry = ledger.get_entry(0)
        assert entry is not None
        assert entry.index == 0
        assert entry.event_type == "candidate_recorded"

    def test_get_nonexistent_entry(self):
        ledger = TransparencyLedger()
        assert ledger.get_entry(0) is None


class TestLedgerWitnessCosignature:
    """Test witness cosignature storage."""

    def test_add_cosignature(self):
        ledger = TransparencyLedger()
        ledger.append("candidate_recorded", {"test": True})
        key = generate_keypair()
        signed = ledger.sign_checkpoint(key)

        witness_key = generate_keypair()
        ledger.add_witness_cosignature(
            signed.checkpoint.size, witness_key.key_id, "cosig_b64_data",
        )

        latest = ledger.get_latest_checkpoint()
        assert latest is not None
        assert len(latest.witness_cosignatures) == 1
        assert latest.witness_cosignatures[0]["key_id"] == witness_key.key_id

    def test_cosignature_wrong_size(self):
        ledger = TransparencyLedger()
        ledger.append("candidate_recorded", {"test": True})
        key = generate_keypair()
        ledger.sign_checkpoint(key)

        with pytest.raises(ProofInvalidError, match="No checkpoint found"):
            ledger.add_witness_cosignature(999, "keyid", "sig")


class TestLedgerRootHash:
    """Test Merkle root hash."""

    def test_empty_root(self):
        ledger = TransparencyLedger()
        root = ledger.root_hash()
        assert len(root) == 32  # SHA-256

    def test_root_changes_on_append(self):
        ledger = TransparencyLedger()
        root0 = ledger.root_hash_hex()
        ledger.append("candidate_recorded", {"a": 1})
        root1 = ledger.root_hash_hex()
        assert root0 != root1

    def test_deterministic_root(self):
        l1 = TransparencyLedger()
        l2 = TransparencyLedger()
        for i in range(5):
            l1.append("candidate_recorded", {"i": i})
            l2.append("candidate_recorded", {"i": i})
        assert l1.root_hash_hex() == l2.root_hash_hex()


class TestLedgerPersistence:
    """Test SQLite persistence."""

    def test_reload_entries(self, tmp_path):
        db_path = tmp_path / "ledger.db"

        # Create and populate
        l1 = TransparencyLedger(db_path)
        l1.append("candidate_recorded", {"a": 1})
        l1.append("release_promoted", {"b": 2})
        root1 = l1.root_hash_hex()
        l1.close()

        # Reload
        l2 = TransparencyLedger(db_path)
        assert l2.size == 2
        assert l2.root_hash_hex() == root1
        l2.close()

