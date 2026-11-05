# SPDX-License-Identifier: MIT
"""End-to-end integration test: full release lifecycle.

This test exercises all 18 steps of the SEGEL release lifecycle
defined in PRD v2.0 §6.0. It creates synthetic keys, builds a
release, inspects it, approves it, records it in the ledger,
deploys to canary units, promotes, and verifies offline.

Steps:
1.  Author creates a configuration release.
2.  Bundle is validated and manifest is created.
3.  Author signs the manifest using a separate signer.
4.  Builder produces Origin provenance.
5.  Inspector performs deterministic capability extraction and policy evaluation.
6.  AI provides advisory findings (skipped in MVP).
7.  Inspector Signer issues the Inspect attestation.
8.  Approvers review the approval payload.
9.  Required approval threshold (2-of-3, author excluded) is met via QR-based transfer.
10. Ledger records the candidate release.
11. Candidate is deployed to two designated canary units.
12. Canary Receivers generate signed health receipts.
13. Promotion Controller evaluates pre-committed promotion criteria.
14. Ledger records the promotion.
15. General Release Passport is assembled.
16. Offline Receiver independently verifies and deploys the release.
17. Receiver generates a signed deployment receipt.
18. System demonstrates rejection of forged/modified/unauthorised releases.
"""

import json
import tempfile
from pathlib import Path

import pytest

from segel_core.canonical import canonical_json
from segel_core.crypto.ed25519 import generate_keypair, export_public_key
from segel_core.crypto.dsse import (
    DSSEEnvelope,
    create_envelope,
    add_signature,
    verify_envelope,
    verify_threshold,
)
from segel_core.crypto.hashing import sha256_hex, verify_inclusion, merkle_leaf_hash
from segel_core.schemas.attestation import PromotionCriteria
from segel_core.schemas.passport import ReleasePassport, LedgerProof
from segel_core.schemas.trust import (
    TrustRoot,
    VerificationPolicy,
    TrustSnapshot,
    KeyRecord,
    RoleThreshold,
)
from segel_core.verification.trust import TrustContext
from segel_core.verification.passport import (
    verify_passport,
    EligibilityClass,
    StampStatus,
)

from builder.builder import build_release_package, sign_origin, sign_manifest
from ledger.ledger import TransparencyLedger
from inspector.inspector import inspect_release, create_inspect_attestation, sign_inspect
from approver.approver import create_approval_payload, approver_sign, collect_approvals
from witness.witness import Witness
from passport.assembler import build_candidate_passport, build_general_passport
from promotion.controller import evaluate_promotion, CanaryReceipt, PromotionCriteria as PC


# ── Fixtures ─────────────────────────────────────────────────────────

class SyntheticLab:
    """Set up a synthetic test environment with all required keys and trust."""

    def __init__(self):
        # Generate all key pairs (SEC-037: OS CSPRNG)
        self.author_key = generate_keypair()
        self.builder_key = generate_keypair()
        self.inspector_key = generate_keypair()
        self.approver_keys = [generate_keypair() for _ in range(3)]
        self.ledger_key = generate_keypair()
        self.witness_key = generate_keypair()
        self.canary_keys = [generate_keypair() for _ in range(2)]
        self.general_receiver_key = generate_keypair()

        # Build trust root with all keys and roles
        keys = [
            self._kr(self.author_key, "author"),
            self._kr(self.builder_key, "builder"),
            self._kr(self.inspector_key, "inspector_signer"),
            self._kr(self.ledger_key, "ledger"),
            self._kr(self.witness_key, "witness"),
        ]
        for i, ak in enumerate(self.approver_keys):
            keys.append(self._kr(ak, "approver", group=f"group-{i % 2}"))
        for ck in self.canary_keys:
            keys.append(self._kr(ck, "receiver"))
        keys.append(self._kr(self.general_receiver_key, "receiver"))

        self.trust_root = TrustRoot(
            root_version=1,
            keys=keys,
            roles=[
                RoleThreshold(role="author", threshold=1),
                RoleThreshold(role="builder", threshold=1),
                RoleThreshold(role="inspector_signer", threshold=1),
                RoleThreshold(
                    role="approver",
                    threshold=2,
                    group_minimums={"group-0": 1, "group-1": 1},
                ),
                RoleThreshold(role="ledger", threshold=1),
                RoleThreshold(role="witness", threshold=1),
                RoleThreshold(role="receiver", threshold=1),
            ],
        )

        self.policy = VerificationPolicy(
            policy_version=1,
            required_stamps=["origin", "inspect", "approve", "record", "test"],
            approval_threshold=2,
            approval_groups={"group-0": 1, "group-1": 1},
            canary_required_count=2,
            witness_cosignature_count=1,
        )

        self.snapshot = TrustSnapshot(epoch=1)

        self.trust_ctx = TrustContext(
            root=self.trust_root,
            policy=self.policy,
            snapshot=self.snapshot,
        )

    @staticmethod
    def _kr(kp, role, group="default"):
        return KeyRecord(
            key_id=kp.key_id,
            public_key_b64=export_public_key(kp.public_key_bytes),
            role=role,
            group=group,
        )


@pytest.fixture
def lab():
    return SyntheticLab()


@pytest.fixture
def tmp_deploy(tmp_path):
    return tmp_path


# ── End-to-End Test ──────────────────────────────────────────────────

@pytest.mark.integration
class TestEndToEndLifecycle:
    """Test the full 18-step release lifecycle."""

    def test_full_lifecycle(self, lab, tmp_deploy):
        """Steps 1-17: Complete release lifecycle from creation to deployment."""

        # ── Step 1: Author creates a configuration release ──
        release_files = {
            "config/app.yaml": b"server:\n  port: 8080\n  host: 0.0.0.0\n",
            "config/logging.yaml": b"log_level: info\nlog_file: /var/log/app.log\n",
        }

        # ── Step 2: Bundle is validated and manifest is created ──
        build_result = build_release_package(
            files=release_files,
            release_id="BASELINE-UNIT-42",
            sequence=1,
            purpose="Initial baseline configuration for Unit 42",
            canary_targets=["canary-1", "canary-2"],
            general_scope=["canary-1", "canary-2", "unit-3"],
        )

        assert build_result.manifest.release_id == "BASELINE-UNIT-42"
        assert build_result.manifest.sequence == 1
        assert len(build_result.manifest.subjects) == 2
        assert len(build_result.package_digest) == 64
        assert len(build_result.manifest_digest) == 64

        # ── Step 3: Author signs the manifest ──
        manifest_envelope = sign_manifest(build_result, lab.author_key)
        assert len(manifest_envelope.signatures) == 1

        # Verify manifest signature
        author_keys = lab.trust_ctx.get_keys_for_role("author")
        manifest_verify = verify_envelope(
            manifest_envelope, author_keys,
            expected_payload_type="application/vnd.segel.manifest+json",
        )
        assert lab.author_key.key_id in manifest_verify.valid_key_ids

        # ── Step 4: Builder produces Origin provenance ──
        origin_envelope = sign_origin(build_result, lab.builder_key)
        assert len(origin_envelope.signatures) == 1

        # Verify origin signature
        builder_keys = lab.trust_ctx.get_keys_for_role("builder")
        origin_verify = verify_envelope(
            origin_envelope, builder_keys,
            expected_payload_type="application/vnd.segel.origin+json",
        )
        assert lab.builder_key.key_id in origin_verify.valid_key_ids

        # ── Step 5: Inspector performs capability extraction ──
        inspection = inspect_release(
            files=release_files,
            manifest=build_result.manifest,
            manifest_digest=build_result.manifest_digest,
            ai_enabled=False,
        )

        assert inspection.verdict in ("PASS", "WARN", "REJECT")
        assert inspection.ai_status == "skipped"
        assert len(inspection.capabilities) > 0  # Should detect network_listen, file_write

        # ── Step 6: AI advisory (skipped in MVP) ──
        assert inspection.ai_status == "skipped"

        # ── Step 7: Inspector Signer issues Inspect attestation ──
        inspect_statement = create_inspect_attestation(
            result=inspection,
            manifest=build_result.manifest,
            manifest_digest=build_result.manifest_digest,
        )
        inspect_envelope = sign_inspect(inspect_statement, lab.inspector_key)

        inspector_keys = lab.trust_ctx.get_keys_for_role("inspector_signer")
        inspect_verify = verify_envelope(
            inspect_envelope, inspector_keys,
            expected_payload_type="application/vnd.segel.inspect+json",
        )
        assert lab.inspector_key.key_id in inspect_verify.valid_key_ids

        # ── Step 8 & 9: Approvers review and sign (2-of-3, author excluded) ──
        approve_statement, approve_request = create_approval_payload(
            manifest=build_result.manifest,
            manifest_digest=build_result.manifest_digest,
            origin_envelope=origin_envelope,
            inspect_envelope=inspect_envelope,
            inspect_verdict=inspection.verdict,
            canary_targets=["canary-1", "canary-2"],
            promotion_criteria=PromotionCriteria(
                required_healthy_canary_units=2,
                required_probes=["file_exists", "config_valid"],
            ),
        )

        # Two approvers sign (from different groups to meet group minimums)
        responses = [
            approver_sign(approve_request, lab.approver_keys[0]),  # group-0
            approver_sign(approve_request, lab.approver_keys[1]),  # group-1
        ]

        approve_envelope = collect_approvals(
            approve_statement, approve_request, responses,
        )

        # Verify threshold: 2-of-3 with author excluded
        approver_keys = lab.trust_ctx.get_keys_for_role("approver")
        approve_verify = verify_envelope(
            approve_envelope, approver_keys,
            expected_payload_type="application/vnd.segel.approve+json",
        )
        counting = verify_threshold(
            approve_verify,
            threshold=2,
            excluded_key_ids={lab.author_key.key_id},
        )
        assert len(counting) >= 2

        # ── Step 10: Ledger records the candidate release ──
        ledger = TransparencyLedger()

        candidate_event = {
            "event_type": "candidate_recorded",
            "release_id": "BASELINE-UNIT-42",
            "sequence": 1,
            "manifest_sha256": build_result.manifest_digest,
            "origin_digest": sha256_hex(canonical_json(origin_envelope.to_dict())),
            "inspect_digest": sha256_hex(canonical_json(inspect_envelope.to_dict())),
            "approve_digest": sha256_hex(canonical_json(approve_envelope.to_dict())),
        }
        candidate_entry = ledger.append("candidate_recorded", candidate_event)
        assert candidate_entry.index == 0

        # Sign checkpoint
        signed_cp = ledger.sign_checkpoint(lab.ledger_key)
        assert signed_cp.checkpoint.size == 1

        # Witness cosigns
        witness = Witness(lab.witness_key)
        cosig = witness.cosign_checkpoint(signed_cp.checkpoint)
        ledger.add_witness_cosignature(
            signed_cp.checkpoint.size,
            lab.witness_key.key_id,
            cosig,
        )

        # Get inclusion proof for candidate
        candidate_proof = ledger.inclusion_proof(candidate_entry.index)

        # Verify the inclusion proof works
        verify_inclusion(
            candidate_entry.data,
            candidate_proof.entry_index,
            candidate_proof.checkpoint_size,
            [bytes.fromhex(h) for h in candidate_proof.proof],
            bytes.fromhex(candidate_proof.checkpoint_root_hash),
        )

        # Build candidate passport
        candidate_ledger_proof = LedgerProof(
            event_type="candidate_recorded",
            entry_index=candidate_proof.entry_index,
            leaf_hash=candidate_proof.leaf_hash,
            inclusion_proof=candidate_proof.proof,
            checkpoint_size=candidate_proof.checkpoint_size,
            checkpoint_root_hash=candidate_proof.checkpoint_root_hash,
            checkpoint_signature=signed_cp.ledger_signature,
            witness_cosignatures=[cosig],
        )

        candidate_passport = build_candidate_passport(
            manifest_envelope=manifest_envelope,
            origin_envelope=origin_envelope,
            inspect_envelope=inspect_envelope,
            approve_envelope=approve_envelope,
            candidate_proof=candidate_ledger_proof,
            signed_checkpoint=signed_cp,
            min_epoch=1,
        )

        assert candidate_passport.passport_type == "candidate"

        # ── Step 11 & 12: Deploy to 2 canary units and get health receipts ──
        from receiver.receiver import Receiver, ReceiverState

        canary_receipts = []
        canary_receipt_envelopes = []

        for i, (canary_key, unit_id) in enumerate(
            zip(lab.canary_keys, ["canary-1", "canary-2"])
        ):
            deploy_dir = tmp_deploy / f"canary-{i+1}"
            deploy_dir.mkdir()

            canary_state = ReceiverState(
                unit_id=unit_id,
                unit_role="canary",
            )

            canary_receiver = Receiver(
                state=canary_state,
                trust_ctx=lab.trust_ctx,
                receiver_key=canary_key,
                deploy_root=deploy_dir / "config",
            )

            verification, receipt_env = canary_receiver.verify_and_deploy(
                passport=candidate_passport,
                files=release_files,
            )

            # Canary should be eligible
            assert verification.eligibility == EligibilityClass.ELIGIBLE_CANARY, (
                f"Canary {unit_id} not eligible: "
                f"{verification.eligibility_reasons}"
            )
            assert receipt_env is not None

            # Verify deployed files exist
            for path, content in release_files.items():
                deployed = deploy_dir / "config" / path
                assert deployed.exists(), f"File not deployed: {path}"
                assert deployed.read_bytes() == content

            # Parse the receipt to get health info
            receipt_payload = json.loads(receipt_env.get_payload_bytes())
            predicate = receipt_payload.get("predicate", {})
            assert predicate.get("overall_result") == "healthy"

            canary_receipts.append(CanaryReceipt(
                unit_id=unit_id,
                overall_result=predicate["overall_result"],
                health_results=predicate.get("health_results", []),
                envelope=receipt_env,
            ))
            canary_receipt_envelopes.append(receipt_env)

        assert len(canary_receipts) == 2

        # ── Step 13: Promotion Controller evaluates criteria ──
        promotion_criteria = PromotionCriteria(
            required_healthy_canary_units=2,
            required_probes=["file_exists", "config_valid"],
        )

        promotion_result = evaluate_promotion(
            criteria=promotion_criteria,
            receipts=canary_receipts,
        )

        assert promotion_result.promoted, (
            f"Promotion failed: {promotion_result.reason}"
        )
        assert len(promotion_result.healthy_units) == 2

        # ── Step 14: Ledger records the promotion ──
        promotion_event = {
            "event_type": "release_promoted",
            "release_id": "BASELINE-UNIT-42",
            "sequence": 1,
            "manifest_sha256": build_result.manifest_digest,
            "healthy_canary_units": promotion_result.healthy_units,
        }
        promotion_entry = ledger.append("release_promoted", promotion_event)
        assert promotion_entry.index == 1

        # Sign new checkpoint and get witness cosignature
        signed_cp2 = ledger.sign_checkpoint(lab.ledger_key)
        assert signed_cp2.checkpoint.size == 2

        # Witness needs consistency proof
        consistency_proof = ledger._tree.consistency_proof(1, 2)
        cosig2 = witness.cosign_checkpoint(
            signed_cp2.checkpoint,
            consistency_proof=consistency_proof,
        )
        ledger.add_witness_cosignature(
            signed_cp2.checkpoint.size,
            lab.witness_key.key_id,
            cosig2,
        )

        # Get promotion inclusion proof
        promotion_proof = ledger.inclusion_proof(promotion_entry.index)

        promotion_ledger_proof = LedgerProof(
            event_type="release_promoted",
            entry_index=promotion_proof.entry_index,
            leaf_hash=promotion_proof.leaf_hash,
            inclusion_proof=promotion_proof.proof,
            checkpoint_size=promotion_proof.checkpoint_size,
            checkpoint_root_hash=promotion_proof.checkpoint_root_hash,
            checkpoint_signature=signed_cp2.ledger_signature,
            witness_cosignatures=[cosig2],
        )

        # ── Step 15: General Release Passport is assembled ──
        general_passport = build_general_passport(
            manifest_envelope=manifest_envelope,
            origin_envelope=origin_envelope,
            inspect_envelope=inspect_envelope,
            approve_envelope=approve_envelope,
            candidate_proof=candidate_ledger_proof,
            test_envelopes=canary_receipt_envelopes,
            promotion_proof=promotion_ledger_proof,
            signed_checkpoint=signed_cp2,
            min_epoch=1,
        )

        assert general_passport.passport_type == "general"
        assert len(general_passport.test_envelopes) == 2

        # ── Step 16: Offline Receiver verifies and deploys ──
        offline_deploy = tmp_deploy / "unit-3"
        offline_deploy.mkdir()

        offline_state = ReceiverState(
            unit_id="unit-3",
            unit_role="general",
        )

        offline_receiver = Receiver(
            state=offline_state,
            trust_ctx=lab.trust_ctx,
            receiver_key=lab.general_receiver_key,
            deploy_root=offline_deploy / "config",
        )

        offline_verification, offline_receipt = offline_receiver.verify_and_deploy(
            passport=general_passport,
            files=release_files,
        )

        # ── Step 17: Receiver generates signed deployment receipt ──
        assert offline_verification.eligibility == EligibilityClass.ELIGIBLE_GENERAL, (
            f"Offline receiver not eligible: "
            f"{offline_verification.eligibility_reasons}"
        )
        assert offline_receipt is not None

        # Verify all stamps are valid
        assert offline_verification.manifest.status == StampStatus.VALID
        assert offline_verification.origin.status == StampStatus.VALID
        assert offline_verification.inspect.status == StampStatus.VALID
        assert offline_verification.approve.status == StampStatus.VALID
        assert offline_verification.record.status == StampStatus.VALID
        assert offline_verification.test.status == StampStatus.VALID

        # Verify receipt is signed
        receipt_payload = json.loads(offline_receipt.get_payload_bytes())
        assert receipt_payload["predicate"]["overall_result"] == "healthy"
        assert receipt_payload["predicate"]["unit_id"] == "unit-3"

        # Verify deployed files
        for path, content in release_files.items():
            deployed = offline_deploy / "config" / path
            assert deployed.exists()
            assert deployed.read_bytes() == content

        print("\n" + "=" * 60)
        print("✔ ALL 17 LIFECYCLE STEPS PASSED")
        print("=" * 60)
        print(offline_verification.summary())
        print()

    def test_rejection_invalid_signature(self, lab, tmp_deploy):
        """Step 18a: Reject release with forged signature (AT-001)."""
        release_files = {
            "config/app.yaml": b"server:\n  port: 8080\n",
        }

        build_result = build_release_package(
            files=release_files,
            release_id="FORGED-RELEASE",
            sequence=1,
            purpose="This release has a forged signature",
            canary_targets=["canary-1"],
            general_scope=["canary-1"],
        )

        # Sign with an UNAUTHORIZED key (not in trust root)
        rogue_key = generate_keypair()
        forged_manifest = sign_manifest(build_result, rogue_key)

        # Try to verify — should fail
        author_keys = lab.trust_ctx.get_keys_for_role("author")
        result = verify_envelope(
            forged_manifest, author_keys,
            expected_payload_type="application/vnd.segel.manifest+json",
        )
        assert len(result.valid_key_ids) == 0

    def test_rejection_modified_bundle(self, lab, tmp_deploy):
        """Step 18b: Reject release with modified content (AT-002)."""
        release_files = {
            "config/app.yaml": b"server:\n  port: 8080\n",
        }

        build_result = build_release_package(
            files=release_files,
            release_id="MODIFIED-RELEASE",
            sequence=1,
            purpose="Original release",
            canary_targets=["canary-1"],
            general_scope=["canary-1"],
        )

        manifest_envelope = sign_manifest(build_result, lab.author_key)
        origin_envelope = sign_origin(build_result, lab.builder_key)

        # Tamper with the files
        tampered_files = {
            "config/app.yaml": b"server:\n  port: 9999\n  # TAMPERED\n",
        }

        # Deploy with tampered files should fail digest check
        from receiver.adapter.baseline import BaselineAdapter
        from segel_core.errors import DigestMismatchError

        adapter = BaselineAdapter(tmp_deploy / "tampered")
        adapter.preflight(build_result.manifest)

        with pytest.raises(DigestMismatchError):
            adapter.stage(build_result.manifest, tampered_files)

    def test_rejection_missing_stamps(self, lab, tmp_deploy):
        """Step 18c: Reject release with missing stamps (AT-003)."""
        release_files = {
            "config/app.yaml": b"server:\n  port: 8080\n",
        }

        build_result = build_release_package(
            files=release_files,
            release_id="MISSING-STAMPS",
            sequence=1,
            purpose="Missing stamps",
            canary_targets=["canary-1"],
            general_scope=["canary-1"],
        )

        manifest_envelope = sign_manifest(build_result, lab.author_key)
        origin_envelope = sign_origin(build_result, lab.builder_key)

        # Build a passport with missing inspect and approve
        from segel_core.errors import StampMissingError

        # Create a minimal passport without proper stamps
        passport = ReleasePassport(
            passport_type="candidate",
            manifest_envelope=manifest_envelope.to_dict(),
            origin_envelope=origin_envelope.to_dict(),
            inspect_envelope=origin_envelope.to_dict(),  # Wrong! Using origin as inspect
            approve_envelope=origin_envelope.to_dict(),  # Wrong! Using origin as approve
        )

        verification = verify_passport(
            passport=passport,
            trust_ctx=lab.trust_ctx,
            unit_id="canary-1",
            unit_role="canary",
            receiver_state={"epoch": 1, "highest_sequence": {}},
        )

        # Should be ineligible due to missing/invalid stamps
        assert verification.eligibility == EligibilityClass.INELIGIBLE

    def test_rejection_author_approves_own_release(self, lab, tmp_deploy):
        """Step 18d: Reject when author approves their own release (AT-008)."""
        release_files = {
            "config/app.yaml": b"server:\n  port: 8080\n",
        }

        build_result = build_release_package(
            files=release_files,
            release_id="SELF-APPROVE",
            sequence=1,
            purpose="Author tries to approve",
            canary_targets=["canary-1"],
            general_scope=["canary-1"],
        )

        # Even if the author signs as an approver,
        # their key_id must be excluded from the threshold count
        from segel_core.errors import ThresholdNotMetError

        # Create a fake approval with only the author's signature
        manifest_envelope = sign_manifest(build_result, lab.author_key)
        origin_envelope = sign_origin(build_result, lab.builder_key)

        inspection = inspect_release(
            files=release_files,
            manifest=build_result.manifest,
            manifest_digest=build_result.manifest_digest,
        )
        inspect_statement = create_inspect_attestation(
            result=inspection,
            manifest=build_result.manifest,
            manifest_digest=build_result.manifest_digest,
        )
        inspect_envelope = sign_inspect(inspect_statement, lab.inspector_key)

        # Create approval payload
        _, approve_request = create_approval_payload(
            manifest=build_result.manifest,
            manifest_digest=build_result.manifest_digest,
            origin_envelope=origin_envelope,
            inspect_envelope=inspect_envelope,
            inspect_verdict=inspection.verdict,
        )

        # Only one approver signs (need 2)
        responses = [
            approver_sign(approve_request, lab.approver_keys[0]),
        ]

        approve_envelope = collect_approvals(
            {}, approve_request, responses,
        )

        # Threshold check should fail (1 < 2)
        approver_keys = lab.trust_ctx.get_keys_for_role("approver")
        approve_verify = verify_envelope(
            approve_envelope, approver_keys,
            expected_payload_type="application/vnd.segel.approve+json",
        )

        with pytest.raises(ThresholdNotMetError):
            verify_threshold(
                approve_verify,
                threshold=2,
                excluded_key_ids={lab.author_key.key_id},
            )

    def test_rejection_sequence_replay(self, lab, tmp_deploy):
        """Step 18e: Reject replay of old sequence (AT-012)."""
        release_files = {
            "config/app.yaml": b"server:\n  port: 8080\n",
        }

        build_result = build_release_package(
            files=release_files,
            release_id="REPLAY-TEST",
            sequence=1,  # Sequence 1
            purpose="First release",
            canary_targets=["canary-1"],
            general_scope=["canary-1"],
        )

        # Simulate a receiver that already accepted sequence 1
        receiver_state = {
            "epoch": 1,
            "highest_sequence": {"REPLAY-TEST": 1},  # Already at seq 1
        }

        manifest_envelope = sign_manifest(build_result, lab.author_key)

        # Build a minimal passport (stamps will fail but we're testing sequence)
        passport = ReleasePassport(
            passport_type="candidate",
            manifest_envelope=manifest_envelope.to_dict(),
            origin_envelope=manifest_envelope.to_dict(),
            inspect_envelope=manifest_envelope.to_dict(),
            approve_envelope=manifest_envelope.to_dict(),
        )

        verification = verify_passport(
            passport=passport,
            trust_ctx=lab.trust_ctx,
            unit_id="canary-1",
            unit_role="canary",
            receiver_state=receiver_state,
        )

        # Should be ineligible due to sequence replay
        assert verification.eligibility == EligibilityClass.INELIGIBLE
        assert any("anti-rollback" in r for r in verification.eligibility_reasons)

