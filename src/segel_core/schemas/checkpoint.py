# SPDX-License-Identifier: MIT
"""Ledger checkpoint schema in C2SP format (PRD v2.0 §16.3).

The transparency ledger is a Merkle log (RFC 6962) that records every
significant event in the release pipeline.  Periodically the ledger
signer produces a **checkpoint** — a signed commitment to the current
log state (size + root hash).

The checkpoint note text follows the `C2SP checkpoint`_ format::

    <origin>
    <decimal size>
    <hex root hash>

Witnesses cosign checkpoints to prevent a split-view attack.

.. _C2SP checkpoint: https://c2sp.org/tlog-checkpoint
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class Checkpoint(BaseModel):
    """Signed checkpoint of the Merkle log.

    The ``to_note_text()`` method renders the checkpoint body in C2SP
    format — this is the exact byte string that gets signed by the
    ledger signer and cosigned by witnesses.
    """

    origin: str = Field(
        default="segel-ledger-v1",
        description="Log origin identifier (C2SP format)",
    )
    size: int = Field(
        ...,
        ge=0,
        description="Number of entries in the Merkle log",
    )
    root_hash: str = Field(
        ...,
        pattern=r"^[0-9a-f]{64}$",
        description="SHA-256 Merkle root hash of the log at this size",
    )

    def to_note_text(self) -> str:
        """Render as C2SP checkpoint note text (the body that gets signed).

        Returns:
            The canonical note text: ``"<origin>\\n<size>\\n<root_hash>\\n"``.
        """
        return f"{self.origin}\n{self.size}\n{self.root_hash}\n"


class SignedCheckpoint(BaseModel):
    """A checkpoint with its signatures.

    The ``ledger_signature`` is produced by the Ledger Signer over the
    ``Checkpoint.to_note_text()`` output.  ``witness_cosignatures`` are
    additional signatures from independent witnesses.
    """

    checkpoint: Checkpoint = Field(
        ...,
        description="The checkpoint data",
    )
    ledger_signature: str = Field(
        default="",
        description="Base64-encoded Ed25519 signature from the ledger signer",
    )
    ledger_key_id: str = Field(
        default="",
        description="Key ID (SHA-256 hex) of the ledger signer",
    )
    witness_cosignatures: list[dict[str, str]] = Field(
        default_factory=list,
        description="List of witness cosignatures: [{key_id, signature}, ...]",
    )
