# SPDX-License-Identifier: MIT
"""Receiver — offline passport verification and deployment orchestration.

Per PRD v2.0 §17 and TAS §8.10:
- The Receiver independently verifies a Release Passport.
- Verification MUST work offline (NFR-001).
- The Receiver maintains sealed state with write-then-rename atomicity.
- State includes: trust root, policy, snapshot, highest sequence per release,
  last checkpoint, deployment journal.
- On state corruption, the Receiver enters recovery mode.
- The Receiver generates signed deployment receipts.

The Receiver is the final line of defence — NO EVIDENCE, NO DEPLOYMENT.
"""

from __future__ import annotations

import contextlib
import json
import os
import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from receiver.adapter.baseline import BaselineAdapter, DeploymentState
from receiver.audit import AuditLogger
from segel_core.canonical import canonical_json
from segel_core.crypto.dsse import DSSEEnvelope, create_envelope
from segel_core.crypto.ed25519 import KeyPair, generate_evidence_id
from segel_core.crypto.hashing import sha256_hex
from segel_core.errors import (
    StateCorruptError,
)
from segel_core.schemas.attestation import (
    TEST_PREDICATE_TYPE,
    InTotoStatement,
    InTotoSubject,
    TestPredicate,
)
from segel_core.schemas.binding import BindingBlock, ReleaseSubject
from segel_core.schemas.manifest import Manifest
from segel_core.schemas.passport import ReleasePassport
from segel_core.verification.passport import (
    EligibilityClass,
    PassportVerificationResult,
    verify_passport,
)
from segel_core.verification.trust import TrustContext

_DEPLOY_LOCKS: dict[str, threading.Lock] = {}
_DEPLOY_LOCKS_GUARD = threading.Lock()


def _get_deploy_lock(path: Path) -> threading.Lock:
    key = str(path.resolve())
    with _DEPLOY_LOCKS_GUARD:
        if key not in _DEPLOY_LOCKS:
            _DEPLOY_LOCKS[key] = threading.Lock()
        return _DEPLOY_LOCKS[key]


@dataclass
class ReceiverState:
    """Persisted state of a Receiver unit."""
    unit_id: str
    unit_role: str  # "canary" or "general"
    epoch: int = 1
    highest_sequence: dict[str, int] = field(default_factory=dict)  # release_id -> seq
    last_checkpoint_size: int = 0
    last_checkpoint_root_hash: str = ""
    trust_root_version: int = 1
    policy_version: int = 1
    state_version: int = 0  # Monotonic counter for replay detection
    recovery_mode: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "unit_id": self.unit_id,
            "unit_role": self.unit_role,
            "epoch": self.epoch,
            "highest_sequence": self.highest_sequence,
            "last_checkpoint_size": self.last_checkpoint_size,
            "last_checkpoint_root_hash": self.last_checkpoint_root_hash,
            "trust_root_version": self.trust_root_version,
            "policy_version": self.policy_version,
            "state_version": self.state_version,
            "recovery_mode": self.recovery_mode,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ReceiverState:
        return cls(**data)


class Receiver:
    """Offline Receiver that verifies passports and deploys configurations.

    The Receiver is an autonomous unit that:
    1. Loads trust metadata from its sealed state.
    2. Receives a Release Passport (e.g., via USB, QR, or file).
    3. Independently verifies all five stamps.
    4. Deploys the release using the pinned adapter.
    5. Runs health checks.
    6. Generates a signed deployment receipt.
    7. Updates its sealed state.
    """

    def __init__(
        self,
        state: ReceiverState,
        trust_ctx: TrustContext,
        receiver_key: KeyPair,
        deploy_root: str | Path,
        state_dir: str | Path | None = None,
        audit_dir: str | Path | None = None,
    ) -> None:
        self._state = state
        self._trust_ctx = trust_ctx
        self._key = receiver_key
        self._adapter = BaselineAdapter(deploy_root)
        self._state_dir = Path(state_dir) if state_dir else None
        self._deploy_root = Path(deploy_root)
        self._audit_logger = AuditLogger(audit_dir) if audit_dir is not None else None

    @property
    def unit_id(self) -> str:
        return self._state.unit_id

    @property
    def state(self) -> ReceiverState:
        return self._state

    def verify_and_deploy(
        self,
        passport: ReleasePassport,
        files: dict[str, bytes],
    ) -> tuple[PassportVerificationResult, DSSEEnvelope | None]:
        """Verify a passport and deploy if eligible.

        Args:
            passport: The Release Passport.
            files: Dict of relative_path -> file_contents.

        Returns:
            Tuple of (verification_result, receipt_envelope_or_None).
        """
        if self._state.recovery_mode:
            raise StateCorruptError(
                "Receiver is in recovery mode — cannot deploy until state is restored"
            )

        # Step 1: Verify the passport
        verification = verify_passport(
            passport=passport,
            trust_ctx=self._trust_ctx,
            unit_id=self._state.unit_id,
            unit_role=self._state.unit_role,
            receiver_state=self._state.to_dict(),
        )

        manifest = verification.manifest_data

        if self._audit_logger:
            self._audit_logger.log(
                "verification_completed",
                {
                    "release_id": manifest.release_id if manifest else "unknown",
                    "sequence": manifest.sequence if manifest else 0,
                    "eligibility": verification.eligibility.value,
                    "all_stamps_valid": verification.all_stamps_valid,
                },
            )

        # Step 2: Check eligibility
        if verification.eligibility not in (
            EligibilityClass.ELIGIBLE_CANARY,
            EligibilityClass.ELIGIBLE_GENERAL,
        ):
            return verification, None

        if manifest is None:
            return verification, None

        # Step 3: Deploy using the adapter lifecycle with concurrency mutual exclusion (FR-086, AT-029)
        lock = _get_deploy_lock(self._deploy_root)
        if not lock.acquire(blocking=False):
            verification.eligibility = EligibilityClass.INELIGIBLE
            verification.eligibility_reasons.append("Concurrent deployment in progress on deploy root")
            return verification, None

        lock_path = self._deploy_root / ".deploy.lock"
        fd = None
        try:
            try:
                self._deploy_root.mkdir(parents=True, exist_ok=True)
                fd = os.open(str(lock_path), os.O_CREAT | os.O_EXCL | os.O_RDWR)
            except (FileExistsError, OSError):
                verification.eligibility = EligibilityClass.INELIGIBLE
                verification.eligibility_reasons.append("Concurrent deployment in progress on deploy root")
                return verification, None

            deploy_state = DeploymentState()

            try:
                # 1. Preflight
                self._adapter.preflight(manifest)

                # 2. Snapshot
                deploy_state.pre_state_digest = self._adapter.snapshot()

                # 3. Stage
                deploy_state.staged_files = self._adapter.stage(manifest, files)

                # 5. Backup
                deploy_state.backup_path = self._adapter.backup()

                # 6. Apply
                self._adapter.apply(manifest)

                # 7. Health check
                deploy_state.health_results = self._adapter.health_check(manifest)

                # Evaluate health
                all_healthy = all(hr.passed for hr in deploy_state.health_results)

                if all_healthy:
                    # 8. Commit
                    deploy_state.post_state_digest = self._adapter.commit()
                    deploy_state.overall_result = "healthy"
                    deploy_state.committed = True

                    # 10. Cleanup
                    self._adapter.cleanup()

                    # Update state
                    self._state.highest_sequence[manifest.release_id] = manifest.sequence
                    self._state.state_version += 1
                    self._save_state()
                else:
                    # 9. Rollback
                    self._adapter.rollback()
                    deploy_state.overall_result = "unhealthy"

            except Exception:
                # Rollback on any error
                try:
                    self._adapter.rollback()
                except Exception:
                    # If rollback also fails, enter recovery mode
                    self._state.recovery_mode = True
                    self._save_state()
                deploy_state.overall_result = "error"

            # Step 4: Generate signed deployment receipt
            receipt_envelope = self._create_receipt(
                manifest=manifest,
                deploy_state=deploy_state,
            )

            if self._audit_logger and manifest:
                self._audit_logger.log(
                    "deployment_completed",
                    {
                        "release_id": manifest.release_id,
                        "sequence": manifest.sequence,
                        "overall_result": deploy_state.overall_result,
                        "committed": deploy_state.committed,
                    },
                )

            return verification, receipt_envelope

        finally:
            if fd is not None:
                try:
                    os.close(fd)
                except OSError:
                    pass
                with contextlib.suppress(OSError):
                    lock_path.unlink()
            lock.release()

    def _create_receipt(
        self,
        manifest: Manifest,
        deploy_state: DeploymentState,
    ) -> DSSEEnvelope:
        """Create and sign a deployment receipt."""
        manifest_digest = sha256_hex(canonical_json(manifest))

        binding = BindingBlock(
            stamp="test",
            subject=ReleaseSubject(
                release_id=manifest.release_id,
                sequence=manifest.sequence,
                manifest_sha256=manifest_digest,
            ),
            trust_root_version=self._state.trust_root_version,
            policy_version=self._state.policy_version,
            evidence_id=generate_evidence_id(),
        )

        predicate = TestPredicate(
            binding=binding,
            unit_id=self._state.unit_id,
            unit_role=self._state.unit_role,
            pre_state_digest=deploy_state.pre_state_digest,
            post_state_digest=deploy_state.post_state_digest,
            adapter_identity=self._adapter.adapter_identity,
            health_results=deploy_state.health_results,
            overall_result=deploy_state.overall_result,
            receiver_state_versions={
                "state_version": self._state.state_version,
            },
        )

        subject = InTotoSubject(
            name=f"release/{manifest.release_id}@{manifest.sequence}",
            digest={"sha256": manifest_digest},
        )

        statement = InTotoStatement(
            subject=[subject],
            predicateType=TEST_PREDICATE_TYPE,
            predicate=predicate.model_dump(mode="json"),
        )

        payload = canonical_json(statement.model_dump(by_alias=True, mode="json"))

        return create_envelope(
            payload_type="application/vnd.segel.test+json",
            payload=payload,
            signers=[(self._key.key_id, self._key.private_key)],
        )


    def _save_state(self) -> None:
        """Persist state using write-then-rename atomicity."""
        if self._state_dir is None:
            return
        self._state_dir.mkdir(parents=True, exist_ok=True)
        state_path = self._state_dir / "receiver_state.json"
        tmp_path = self._state_dir / "receiver_state.json.tmp"

        data = json.dumps(self._state.to_dict(), indent=2)
        tmp_path.write_text(data, encoding="utf-8")
        tmp_path.replace(state_path)

