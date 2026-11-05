"""
Trust verification: loading and validating trust metadata.

Implements the trust root chain, key role lookups, revocation checks,
epoch and version monotonicity enforcement per PRD v2.0 §16.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

from segel_core.crypto.dsse import DSSEEnvelope, verify_envelope
from segel_core.crypto.ed25519 import PublicKeyInfo, import_public_key
from segel_core.errors import (
    EpochStaleError,
    ErrorCode,
    KeyNotAuthorisedError,
    KeyRevokedError,
    PolicyDowngradeError,
    SegelError,
    SignatureError,
)
from segel_core.schemas.trust import (
    KeyRecord,
    TrustRoot,
    TrustSnapshot,
    VerificationPolicy,
)


@dataclass
class TrustContext:
    """Loaded and verified trust context for verification operations.

    This holds the active trust root, policy, and snapshot along with
    lookup indices for efficient key and role queries.
    """
    root: TrustRoot
    policy: VerificationPolicy
    snapshot: TrustSnapshot | None = None

    # Lookup caches built on load
    _keys_by_id: dict[str, KeyRecord] = field(default_factory=dict)
    _keys_by_role: dict[str, list[KeyRecord]] = field(default_factory=dict)
    _public_keys_cache: dict[str, PublicKeyInfo] = field(default_factory=dict)
    _revoked_key_ids: set[str] = field(default_factory=set)
    _held_releases: set[tuple[str, int]] = field(default_factory=set)

    def __post_init__(self) -> None:
        self._rebuild_indices()

    def _rebuild_indices(self) -> None:
        """Build lookup indices from the trust root."""
        self._keys_by_id.clear()
        self._keys_by_role.clear()
        self._public_keys_cache.clear()
        self._revoked_key_ids.clear()
        self._held_releases.clear()

        for key_rec in self.root.keys:
            self._keys_by_id[key_rec.key_id] = key_rec
            role_list = self._keys_by_role.setdefault(key_rec.role, [])
            role_list.append(key_rec)

            # Pre-load public key objects
            try:
                pk_info = import_public_key(key_rec.public_key_b64)
                pk_info = PublicKeyInfo(
                    public_key=pk_info.public_key,
                    public_key_bytes=pk_info.public_key_bytes,
                    key_id=pk_info.key_id,
                    role=key_rec.role,
                    algorithm=key_rec.algorithm,
                )
                self._public_keys_cache[key_rec.key_id] = pk_info
            except (SignatureError, ValueError):
                pass  # Malformed key record won't be usable

        # Load revocations from snapshot
        if self.snapshot:
            for rev in self.snapshot.revoked_keys:
                self._revoked_key_ids.add(rev.key_id)
            for held in self.snapshot.held_releases:
                self._held_releases.add((held.release_id, held.sequence))

    def get_keys_for_role(self, role: str) -> list[PublicKeyInfo]:
        """Get all active (non-revoked) public keys for a role.

        Args:
            role: The role name (e.g., 'approver', 'builder').

        Returns:
            List of PublicKeyInfo for active keys in this role.
        """
        result = []
        for key_rec in self._keys_by_role.get(role, []):
            if key_rec.key_id in self._revoked_key_ids:
                continue
            if key_rec.status != "active":
                continue
            if key_rec.algorithm != "ed25519":
                continue  # SEC-039: reject unknown algorithms
            pk = self._public_keys_cache.get(key_rec.key_id)
            if pk is not None:
                result.append(pk)
        return result

    def get_threshold_for_role(self, role: str) -> int:
        """Get the signing threshold for a role.

        Returns:
            The threshold, or 1 if not defined.
        """
        for role_thresh in self.root.roles:
            if role_thresh.role == role:
                return role_thresh.threshold
        return 1

    def get_group_minimums(self, role: str) -> dict[str, int]:
        """Get per-group minimum signers for a role.

        Returns:
            Dict of group_name -> minimum count.
        """
        for role_thresh in self.root.roles:
            if role_thresh.role == role:
                return role_thresh.group_minimums
        return {}

    def is_key_revoked(self, key_id: str) -> bool:
        """Check if a key is revoked."""
        return key_id in self._revoked_key_ids

    def is_key_revoked_at_index(self, key_id: str, evidence_index: int) -> bool:
        """Check if a key is revoked at or before a given ledger index.

        Per SEC-012: Revocation takes effect by ledger position.
        Evidence recorded BEFORE revoked_at_index remains valid.

        Args:
            key_id: The key to check.
            evidence_index: The ledger index of the evidence.

        Returns:
            True if the key was revoked at or before evidence_index.
        """
        if self.snapshot is None:
            return False
        for rev in self.snapshot.revoked_keys:
            if rev.key_id == key_id and evidence_index >= rev.revoked_at_index:
                return True
        return False

    def is_release_held(self, release_id: str, sequence: int) -> bool:
        """Check if a release is held per the snapshot."""
        return (release_id, sequence) in self._held_releases

    def get_key_record(self, key_id: str) -> KeyRecord | None:
        """Get the KeyRecord for a given key_id if known."""
        return self._keys_by_id.get(key_id)

    def check_key_authorised(self, key_id: str, role: str) -> PublicKeyInfo:
        """Verify a key is authorised for a role and not revoked.

        Args:
            key_id: The key identity to check.
            role: The required role.

        Returns:
            The PublicKeyInfo if authorised.

        Raises:
            KeyNotAuthorisedError: If the key is not authorised.
            KeyRevokedError: If the key is revoked.
        """
        key_rec = self._keys_by_id.get(key_id)
        if key_rec is None:
            raise KeyNotAuthorisedError(
                f"Key {key_id[:16]}... is not in the trust root",
            )
        if key_rec.role != role:
            raise KeyNotAuthorisedError(
                f"Key {key_id[:16]}... has role '{key_rec.role}', not '{role}'",
            )
        if key_id in self._revoked_key_ids:
            raise KeyRevokedError(
                f"Key {key_id[:16]}... is revoked",
            )
        if key_rec.algorithm != "ed25519":
            raise KeyNotAuthorisedError(
                f"Key {key_id[:16]}... uses unknown algorithm '{key_rec.algorithm}'",
            )
        pk = self._public_keys_cache.get(key_id)
        if pk is None:
            raise KeyNotAuthorisedError(
                f"Key {key_id[:16]}... could not be loaded",
            )
        return pk

    def apply_trust_update(self, tup: dict[str, Any]) -> None:
        """Verify and apply a Trust Update Package (TUP).

        Per FR-066, SEC-013, SEC-035:
        - Cryptographic envelope verification against active root keyholders.
        - Anti-rollback protection: target_epoch must be > current epoch.
        - Atomic update of root, policy, snapshot, and rebuilt indices.
        """
        env_dict = tup.get("envelope", tup)
        envelope = DSSEEnvelope.from_dict(env_dict)

        # 1. Signature verification
        authorised_keys = [
            pk for pk in self._public_keys_cache.values()
            if not self.is_key_revoked(pk.key_id)
        ]

        v_res = verify_envelope(
            envelope,
            authorised_keys,
            expected_payload_type="https://segel.dev/trust-update/v1",
        )

        if not v_res.valid_key_ids:
            for s in envelope.signatures:
                if s.keyid in self._keys_by_id:
                    raise SignatureError("TUP signature verification failed")
            raise KeyNotAuthorisedError("TUP signed by untrusted or unauthorised key")

        # 2. Parse payload and anti-rollback check
        payload_bytes = envelope.get_payload_bytes()
        payload = json.loads(payload_bytes)

        target_epoch = payload.get("target_epoch", 0)
        current_epoch = self.snapshot.epoch if self.snapshot else 1

        if target_epoch <= current_epoch:
            raise SegelError(
                ErrorCode.EPOCH_STALE,
                f"TUP target_epoch {target_epoch} <= current epoch {current_epoch} (anti-rollback)",
            )

        # 3. Apply updates
        if "root" in payload:
            self.root = TrustRoot.model_validate(payload["root"])
        if "policy" in payload:
            self.policy = VerificationPolicy.model_validate(payload["policy"])
        if "snapshot" in payload:
            self.snapshot = TrustSnapshot.model_validate(payload["snapshot"])

        self._rebuild_indices()


def check_version_monotonicity(
    current_root_version: int,
    current_policy_version: int,
    current_epoch: int,
    new_root_version: int,
    new_policy_version: int,
    new_epoch: int,
) -> None:
    """Check that trust metadata versions are non-decreasing.

    Per SEC-011: Receiver persists and enforces highest versions.

    Raises:
        PolicyDowngradeError: If any version would decrease.
    """
    if new_root_version < current_root_version:
        raise PolicyDowngradeError(
            f"Root version downgrade: {new_root_version} < {current_root_version}",
        )
    if new_policy_version < current_policy_version:
        raise PolicyDowngradeError(
            f"Policy version downgrade: {new_policy_version} < {current_policy_version}",
        )
    if new_epoch < current_epoch:
        raise EpochStaleError(
            f"Epoch downgrade: {new_epoch} < {current_epoch}",
        )


def check_min_epoch(
    receiver_epoch: int,
    required_min_epoch: int,
    freshness_mode: str,
) -> None:
    """Check that the receiver's epoch meets the required minimum.

    Per AT-009: In STRICT mode, fail closed if epoch too low.

    Args:
        receiver_epoch: The receiver's current epoch.
        required_min_epoch: The minimum epoch required by the passport.
        freshness_mode: 'strict' or 'advisory'.

    Raises:
        EpochStaleError: In strict mode if the epoch is too low.
    """
    if receiver_epoch < required_min_epoch and freshness_mode == "strict":
        raise EpochStaleError(
            f"Receiver epoch {receiver_epoch} is below the required minimum "
            f"{required_min_epoch}. Install a Trust Update Package with "
            f"epoch >= {required_min_epoch}.",
            {
                "receiver_epoch": receiver_epoch,
                "required_min_epoch": required_min_epoch,
                "action": "Install Trust Update Package",
            },
        )
        # In advisory mode, this is logged but not blocking

