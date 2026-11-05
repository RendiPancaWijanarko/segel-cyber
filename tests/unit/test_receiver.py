# SPDX-License-Identifier: MIT
"""Unit tests for the Receiver and Baseline Adapter.

Tests offline verification, deployment lifecycle, rollback, and security.
"""

import json
import pytest

from receiver.receiver import Receiver, ReceiverState
from receiver.adapter.baseline import BaselineAdapter, DeploymentState, ADAPTER_ID
from segel_core.crypto.ed25519 import generate_keypair, export_public_key
from segel_core.crypto.hashing import sha256_hex
from segel_core.errors import (
    DigestMismatchError,
    PackageMalformedError,
    StateCorruptError,
)
from segel_core.schemas.manifest import Manifest, SubjectDigest


def _make_manifest_and_files():
    content_a = b"server:\n  port: 8080\n"
    content_b = b"log_level: info\n"
    files = {
        "config/a.yaml": content_a,
        "config/b.yaml": content_b,
    }
    manifest = Manifest(
        release_id="TEST-1",
        sequence=1,
        purpose="test",
        subjects=[
            SubjectDigest(path="config/a.yaml", sha256=sha256_hex(content_a), size=len(content_a)),
            SubjectDigest(path="config/b.yaml", sha256=sha256_hex(content_b), size=len(content_b)),
        ],
        canary_targets=["canary-1"],
        general_scope=["canary-1", "unit-3"],
    )
    return manifest, files


class TestBaselineAdapterPreflight:
    """Test preflight checks."""

    def test_preflight_creates_deploy_root(self, tmp_path):
        deploy_root = tmp_path / "deploy"
        adapter = BaselineAdapter(deploy_root)
        manifest, _ = _make_manifest_and_files()
        adapter.preflight(manifest)
        assert deploy_root.exists()

    def test_preflight_detects_path_escape(self, tmp_path):
        adapter = BaselineAdapter(tmp_path / "deploy")
        manifest = Manifest(
            release_id="ESCAPE-1", sequence=1, purpose="escape",
            subjects=[
                SubjectDigest(path="../../etc/passwd", sha256="a" * 64, size=10),
            ],
        )
        with pytest.raises(PackageMalformedError, match="escape"):
            adapter.preflight(manifest)


class TestBaselineAdapterStage:
    """Test file staging and digest verification."""

    def test_stage_valid_files(self, tmp_path):
        adapter = BaselineAdapter(tmp_path / "deploy")
        manifest, files = _make_manifest_and_files()
        adapter.preflight(manifest)
        staged = adapter.stage(manifest, files)
        assert len(staged) == 2
        assert "config/a.yaml" in staged
        assert "config/b.yaml" in staged

    def test_stage_digest_mismatch(self, tmp_path):
        adapter = BaselineAdapter(tmp_path / "deploy")
        manifest, files = _make_manifest_and_files()
        adapter.preflight(manifest)

        # Tamper with file content
        tampered = dict(files)
        tampered["config/a.yaml"] = b"TAMPERED CONTENT"

        with pytest.raises(DigestMismatchError, match="Digest mismatch"):
            adapter.stage(manifest, tampered)

    def test_stage_missing_file(self, tmp_path):
        adapter = BaselineAdapter(tmp_path / "deploy")
        manifest, files = _make_manifest_and_files()
        adapter.preflight(manifest)

        # Remove a file
        incomplete = {"config/a.yaml": files["config/a.yaml"]}

        with pytest.raises(DigestMismatchError, match="missing"):
            adapter.stage(manifest, incomplete)

    def test_stage_size_mismatch(self, tmp_path):
        adapter = BaselineAdapter(tmp_path / "deploy")
        content = b"data"
        manifest = Manifest(
            release_id="SIZE-1", sequence=1, purpose="size test",
            subjects=[
                SubjectDigest(
                    path="config/a.yaml",
                    sha256=sha256_hex(content),
                    size=999,  # Wrong size
                ),
            ],
        )
        adapter.preflight(manifest)
        with pytest.raises(DigestMismatchError, match="Size mismatch"):
            adapter.stage(manifest, {"config/a.yaml": content})


class TestBaselineAdapterFullLifecycle:
    """Test the full 10-step deployment lifecycle."""

    def test_full_lifecycle(self, tmp_path):
        deploy_root = tmp_path / "deploy"
        adapter = BaselineAdapter(deploy_root)
        manifest, files = _make_manifest_and_files()

        # 1. Preflight
        adapter.preflight(manifest)

        # 2. Snapshot
        pre_digest = adapter.snapshot()
        assert len(pre_digest) == 64

        # 3. Stage
        staged = adapter.stage(manifest, files)
        assert len(staged) == 2

        # 5. Backup
        backup_path = adapter.backup()
        assert backup_path

        # 6. Apply
        adapter.apply(manifest)

        # Verify files deployed
        assert (deploy_root / "config/a.yaml").exists()
        assert (deploy_root / "config/b.yaml").exists()
        assert (deploy_root / "config/a.yaml").read_bytes() == files["config/a.yaml"]

        # 7. Health check
        results = adapter.health_check(manifest)
        assert all(r.passed for r in results)

        # 8. Commit
        post_digest = adapter.commit()
        assert post_digest != pre_digest

        # 10. Cleanup
        adapter.cleanup()


class TestBaselineAdapterRollback:
    """Test rollback functionality."""

    def test_rollback_restores_previous_state(self, tmp_path):
        deploy_root = tmp_path / "deploy"
        adapter = BaselineAdapter(deploy_root)
        manifest, files = _make_manifest_and_files()

        # Pre-existing file
        deploy_root.mkdir(parents=True)
        (deploy_root / "config").mkdir()
        (deploy_root / "config" / "old.yaml").write_bytes(b"old content")

        adapter.preflight(manifest)
        adapter.backup()
        adapter.stage(manifest, files)
        adapter.apply(manifest)

        # Old file should be gone after apply
        # Now rollback
        adapter.rollback()

        # Old file should be back
        assert (deploy_root / "config" / "old.yaml").exists()
        assert (deploy_root / "config" / "old.yaml").read_bytes() == b"old content"


class TestBaselineAdapterHealthCheck:
    """Test health probes."""

    def test_file_exists_probe(self, tmp_path):
        deploy_root = tmp_path / "deploy"
        adapter = BaselineAdapter(deploy_root)
        manifest, files = _make_manifest_and_files()
        adapter.preflight(manifest)
        adapter.stage(manifest, files)
        adapter.apply(manifest)

        results = adapter.health_check(manifest)
        file_exists_results = [r for r in results if r.probe == "file_exists"]
        assert all(r.passed for r in file_exists_results)

    def test_config_valid_probe(self, tmp_path):
        deploy_root = tmp_path / "deploy"
        adapter = BaselineAdapter(deploy_root)
        manifest, files = _make_manifest_and_files()
        adapter.preflight(manifest)
        adapter.stage(manifest, files)
        adapter.apply(manifest)

        results = adapter.health_check(manifest)
        config_valid_results = [r for r in results if r.probe == "config_valid"]
        assert all(r.passed for r in config_valid_results)


class TestReceiverState:
    """Test ReceiverState serialization."""

    def test_to_dict(self):
        state = ReceiverState(unit_id="unit-1", unit_role="canary")
        d = state.to_dict()
        assert d["unit_id"] == "unit-1"
        assert d["unit_role"] == "canary"
        assert d["epoch"] == 1
        assert d["recovery_mode"] is False

    def test_from_dict_roundtrip(self):
        state = ReceiverState(
            unit_id="unit-1", unit_role="general",
            epoch=3, highest_sequence={"REL-1": 5},
        )
        d = state.to_dict()
        restored = ReceiverState.from_dict(d)
        assert restored.unit_id == "unit-1"
        assert restored.epoch == 3
        assert restored.highest_sequence["REL-1"] == 5

    def test_state_persistence(self, tmp_path):
        state_dir = tmp_path / "state"
        state = ReceiverState(unit_id="unit-1", unit_role="canary")
        state.highest_sequence["TEST-1"] = 1
        state.state_version = 1

        # Save manually (simulating _save_state)
        state_dir.mkdir()
        import json
        (state_dir / "receiver_state.json").write_text(
            json.dumps(state.to_dict(), indent=2), encoding="utf-8",
        )

        # Reload
        data = json.loads((state_dir / "receiver_state.json").read_text(encoding="utf-8"))
        restored = ReceiverState.from_dict(data)
        assert restored.highest_sequence["TEST-1"] == 1


class TestReceiverRecoveryMode:
    """Test recovery mode behavior."""

    def test_recovery_mode_blocks_deployment(self):
        from segel_core.schemas.passport import ReleasePassport
        from segel_core.schemas.trust import TrustRoot, VerificationPolicy, TrustSnapshot
        from segel_core.verification.trust import TrustContext

        state = ReceiverState(unit_id="unit-1", unit_role="canary", recovery_mode=True)
        key = generate_keypair()

        trust_root = TrustRoot(root_version=1, keys=[], roles=[])
        policy = VerificationPolicy(policy_version=1)
        snapshot = TrustSnapshot(epoch=1)
        trust_ctx = TrustContext(root=trust_root, policy=policy, snapshot=snapshot)

        receiver = Receiver(
            state=state, trust_ctx=trust_ctx,
            receiver_key=key, deploy_root="/tmp/test",
        )

        passport = ReleasePassport(
            passport_type="candidate",
            manifest_envelope={}, origin_envelope={},
            inspect_envelope={}, approve_envelope={},
        )

        with pytest.raises(StateCorruptError, match="recovery mode"):
            receiver.verify_and_deploy(passport, {})


class TestDeploymentReceiptSchema:
    """Test DeploymentReceipt schema per PRD v2.0 §12."""

    def test_deployment_receipt_schema_validation(self):
        from segel_core.schemas.binding import BindingBlock, ReleaseSubject
        from segel_core.schemas.receipt import DeploymentReceipt

        binding = BindingBlock(
            stamp="test",
            subject=ReleaseSubject(
                release_id="REL-100",
                sequence=1,
                manifest_sha256="a" * 64,
            ),
            trust_root_version=1,
            policy_version=1,
            evidence_id="a" * 32,
        )

        receipt = DeploymentReceipt(
            binding=binding,
            unit_id="canary-1",
            unit_role="canary",
            result="committed",
            pre_state_digest="b" * 64,
            post_state_digest="c" * 64,
            adapter_identity="segel-baseline-adapter/v1",
            health_results=[{"probe": "file_exists", "status": "ok"}],
            receiver_state_versions={"state_version": 2},
            informational_timestamp="2026-11-03T12:00:00Z",
        )

        assert receipt.unit_id == "canary-1"
        assert receipt.result == "committed"
        assert receipt.schema_version == "segel.receipt/v1"

        # Roundtrip
        raw_json = receipt.model_dump_json()
        restored = DeploymentReceipt.model_validate_json(raw_json)
        assert restored.unit_id == receipt.unit_id
        assert restored.binding.evidence_id == "a" * 32

    def test_deployment_receipt_invalid_fields_rejected(self):
        import pydantic
        from segel_core.schemas.binding import BindingBlock, ReleaseSubject
        from segel_core.schemas.receipt import DeploymentReceipt

        binding = BindingBlock(
            stamp="test",
            subject=ReleaseSubject(release_id="REL-1", sequence=1, manifest_sha256="0" * 64),
            trust_root_version=1,
            policy_version=1,
            evidence_id="b" * 32,
        )

        with pytest.raises(pydantic.ValidationError):
            DeploymentReceipt(
                binding=binding,
                unit_id="canary-1",
                unit_role="invalid_role",  # Must be canary or general
                result="committed",
            )

        with pytest.raises(pydantic.ValidationError):
            DeploymentReceipt(
                binding=binding,
                unit_id="canary-1",
                unit_role="canary",
                result="invalid_result",  # Must be committed, rolled_back, or failed
            )


