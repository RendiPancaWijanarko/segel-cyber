# SPDX-License-Identifier: MIT
"""Unit tests for the Witness component.

Tests checkpoint cosigning, consistency proof verification, and fork rejection.
"""

import base64
import pytest

from ledger.ledger import TransparencyLedger
from witness.witness import Witness, WitnessState
from segel_core.crypto.ed25519 import generate_keypair, verify
from segel_core.errors import CheckpointForkError, ProofInvalidError
from segel_core.schemas.checkpoint import Checkpoint


def test_first_checkpoint_accepted():
    ledger = TransparencyLedger()
    ledger.append("candidate_recorded", {"item": 1})
    cp = ledger.create_checkpoint()

    witness_key = generate_keypair()
    witness = Witness(witness_key)

    cosig_b64 = witness.cosign_checkpoint(cp)
    assert cosig_b64
    assert witness.state.last_checkpoint_size == cp.size
    assert witness.state.last_checkpoint_root_hash == cp.root_hash

    # Verify signature
    raw_sig = base64.b64decode(cosig_b64)
    verify(witness_key.public_key, raw_sig, cp.to_note_text().encode("utf-8"))


def test_same_size_same_root_reaccepted():
    ledger = TransparencyLedger()
    ledger.append("candidate_recorded", {"item": 1})
    cp = ledger.create_checkpoint()

    witness_key = generate_keypair()
    witness = Witness(witness_key)
    sig1 = witness.cosign_checkpoint(cp)
    sig2 = witness.cosign_checkpoint(cp)
    assert sig1 == sig2


def test_same_size_different_root_raises_fork():
    witness_key = generate_keypair()
    witness = Witness(witness_key, state=WitnessState(last_checkpoint_size=1, last_checkpoint_root_hash="a" * 64))

    forged_cp = Checkpoint(origin="segel-ledger-v1", size=1, root_hash="b" * 64)
    with pytest.raises(CheckpointForkError, match="fork detected"):
        witness.cosign_checkpoint(forged_cp)


def test_smaller_size_rejected():
    witness_key = generate_keypair()
    witness = Witness(witness_key, state=WitnessState(last_checkpoint_size=5, last_checkpoint_root_hash="a" * 64))

    smaller_cp = Checkpoint(origin="segel-ledger-v1", size=4, root_hash="b" * 64)
    with pytest.raises(CheckpointForkError, match=r"<\s*last"):
        witness.cosign_checkpoint(smaller_cp)


def test_extending_checkpoint_with_valid_proof():
    ledger = TransparencyLedger()
    ledger.append("candidate_recorded", {"item": 1})
    cp1 = ledger.create_checkpoint()

    witness_key = generate_keypair()
    witness = Witness(witness_key)
    witness.cosign_checkpoint(cp1)

    # Append more entries
    ledger.append("candidate_recorded", {"item": 2})
    ledger.append("candidate_recorded", {"item": 3})
    cp2 = ledger.create_checkpoint()

    proof_hex = ledger.consistency_proof(cp1.size, cp2.size)
    proof_bytes = [bytes.fromhex(h) for h in proof_hex]

    cosig_b64 = witness.cosign_checkpoint(cp2, consistency_proof=proof_bytes)
    assert cosig_b64
    assert witness.state.last_checkpoint_size == 3
    assert witness.state.last_checkpoint_root_hash == cp2.root_hash


def test_extending_checkpoint_without_proof_raises():
    ledger = TransparencyLedger()
    ledger.append("candidate_recorded", {"item": 1})
    cp1 = ledger.create_checkpoint()

    witness = Witness(generate_keypair())
    witness.cosign_checkpoint(cp1)

    ledger.append("candidate_recorded", {"item": 2})
    cp2 = ledger.create_checkpoint()

    with pytest.raises(ProofInvalidError, match="Consistency proof required"):
        witness.cosign_checkpoint(cp2, consistency_proof=None)
