# SPDX-License-Identifier: MIT
"""Witness — independent checkpoint cosigning.

Per PRD v2.0 §16.3 and TAS §8.6:
- The Witness runs as a separate process with its own signing identity.
- It stores the last verified checkpoint.
- It cosigns ONLY checkpoints that extend the previous one.
- It verifies the consistency proof before cosigning.
- It MUST NOT cosign a checkpoint with a smaller or non-extending tree.
"""

from __future__ import annotations

import base64
from dataclasses import dataclass

from segel_core.crypto.ed25519 import KeyPair, sign
from segel_core.crypto.hashing import verify_consistency
from segel_core.errors import CheckpointForkError, ProofInvalidError
from segel_core.schemas.checkpoint import Checkpoint


@dataclass
class WitnessState:
    """Persisted state of the witness."""
    last_checkpoint_size: int = 0
    last_checkpoint_root_hash: str = ""


class Witness:
    """Independent checkpoint cosigner.

    The Witness verifies that each new checkpoint extends the previous
    one (via consistency proof) before cosigning it.
    """

    def __init__(
        self,
        witness_key: KeyPair,
        state: WitnessState | None = None,
    ) -> None:
        self._key = witness_key
        self._state = state or WitnessState()

    @property
    def key_id(self) -> str:
        return self._key.key_id

    @property
    def state(self) -> WitnessState:
        return self._state

    def cosign_checkpoint(
        self,
        checkpoint: Checkpoint,
        consistency_proof: list[bytes] | None = None,
    ) -> str:
        """Cosign a checkpoint after verifying it extends the previous one.

        Args:
            checkpoint: The new checkpoint to cosign.
            consistency_proof: Merkle consistency proof from old to new tree.

        Returns:
            Base64-encoded cosignature.

        Raises:
            CheckpointForkError: If the checkpoint doesn't extend the previous.
            ProofInvalidError: If the consistency proof is invalid.
        """
        # First checkpoint — accept without proof
        if self._state.last_checkpoint_size == 0:
            return self._sign_and_update(checkpoint)

        # Same size — must have same root
        if checkpoint.size == self._state.last_checkpoint_size:
            if checkpoint.root_hash != self._state.last_checkpoint_root_hash:
                raise CheckpointForkError(
                    "Checkpoint has same size but different root — fork detected",
                    {
                        "witness_root": self._state.last_checkpoint_root_hash,
                        "new_root": checkpoint.root_hash,
                    },
                )
            return self._sign_and_update(checkpoint)

        # New checkpoint must be larger
        if checkpoint.size < self._state.last_checkpoint_size:
            raise CheckpointForkError(
                f"Checkpoint size {checkpoint.size} < last {self._state.last_checkpoint_size}",
            )

        # Verify consistency proof
        if consistency_proof is None:
            raise ProofInvalidError(
                "Consistency proof required for extending checkpoint"
            )

        old_root = bytes.fromhex(self._state.last_checkpoint_root_hash)
        new_root = bytes.fromhex(checkpoint.root_hash)

        verify_consistency(
            self._state.last_checkpoint_size,
            checkpoint.size,
            old_root,
            new_root,
            consistency_proof,
        )

        return self._sign_and_update(checkpoint)

    def _sign_and_update(self, checkpoint: Checkpoint) -> str:
        """Sign the checkpoint and update state."""
        note_text = checkpoint.to_note_text()
        sig = sign(self._key.private_key, note_text.encode("utf-8"))
        sig_b64 = base64.b64encode(sig).decode("ascii")

        self._state.last_checkpoint_size = checkpoint.size
        self._state.last_checkpoint_root_hash = checkpoint.root_hash

        return sig_b64

