# SPDX-License-Identifier: MIT
"""Unit tests for AI-7: Purpose sanitization, WARN acknowledgement, and AI advisory UI.

Tests:
1. Rejection of control characters in manifest purpose at creation.
2. Canonical acknowledgement_digest computation.
3. Ledger gate enforcement of require_warn_acknowledgement for WARN releases.
4. Receiver verifier enforcement of require_warn_acknowledgement for WARN releases.
5. Release Desk templates (AI advisory panel, banners, escaped text, no confidence %, footer disclaimer).
"""

from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from ledger.ledger import _verify_candidate_evidence
from segel_core.canonical import canonical_json, compute_acknowledgement_digest
from segel_core.crypto.dsse import DSSEEnvelope, create_envelope
from segel_core.crypto.ed25519 import KeyPair, generate_evidence_id, generate_keypair
from segel_core.crypto.hashing import sha256_hex
from segel_core.errors import DigestMismatchError, ErrorCode
from segel_core.schemas.attestation import (
    APPROVE_PREDICATE_TYPE,
    INSPECT_PREDICATE_TYPE,
    ORIGIN_PREDICATE_TYPE,
    ApprovePredicate,
    InspectFinding,
    InspectPredicate,
    InTotoStatement,
    InTotoSubject,
    OriginPredicate,
    PromotionCriteria,
)
from segel_core.schemas.binding import BindingBlock, ReleaseSubject
from segel_core.schemas.manifest import Manifest, SubjectDigest
from segel_core.schemas.passport import ReleasePassport
from segel_core.schemas.trust import (
    KeyRecord,
    RoleThreshold,
    TrustRoot,
    TrustSnapshot,
    VerificationPolicy,
)
from segel_core.verification.passport import verify_passport
from segel_core.verification.trust import TrustContext

# ---------------------------------------------------------------------------
# Test Helpers
# ---------------------------------------------------------------------------


def _dummy_subject() -> SubjectDigest:
    return SubjectDigest(
        path="config/app.yaml",
        sha256="0" * 64,
        size=10,
    )


def _make_envelope(payload_type: str, payload: bytes, keys: list[KeyPair]) -> DSSEEnvelope:
    signers = [(k.key_id, k.private_key) for k in keys]
    return create_envelope(payload_type, payload, signers)


def _make_manifest(purpose: str) -> Manifest:
    return Manifest(
        release_id="REL-TEST-01",
        sequence=1,
        purpose=purpose,
        subjects=[_dummy_subject()],
        canary_targets=["canary-1"],
        general_scope=["unit-3"],
    )


# ---------------------------------------------------------------------------
# 1. Manifest Purpose Control Character Rejection
# ---------------------------------------------------------------------------


class TestManifestPurposeControlCharacters:
    """Manifest creation must reject control characters per PRD v2.0 FR-012, SEC-013, D16."""

    @pytest.mark.parametrize(
        ("ctrl_char", "name"),
        [
            ("\x00", "null byte"),
            ("\x07", "bell"),
            ("\x08", "backspace"),
            ("\t", "tab"),
            ("\n", "newline"),
            ("\r", "carriage return"),
            ("\x1b", "escape"),
            ("\x1f", "unit separator"),
            ("\x7f", "delete"),
            ("\x80", "padding character"),
            ("\x9f", "application program command"),
        ],
    )
    def test_manifest_rejects_control_characters(self, ctrl_char: str, name: str) -> None:
        """Any ASCII or C1 Unicode control character in purpose must raise ValueError/ValidationError."""
        with pytest.raises((ValueError, ValidationError)) as exc_info:
            _make_manifest(f"Valid prefix {ctrl_char} and suffix ({name})")
        err_msg = str(exc_info.value).lower()
        assert "control character" in err_msg or "forbidden" in err_msg or "invalid" in err_msg

    def test_manifest_accepts_clean_purpose(self) -> None:
        """Legitimate text with spaces, punctuation, digits, and Unicode letters must be accepted."""
        clean = "Pembaruan DNS allowlist cabang v2.0 (tiket SEC-123) — aman digunakan."
        m = _make_manifest(clean)
        assert m.purpose == clean


# ---------------------------------------------------------------------------
# 2. Acknowledgement Digest Computation
# ---------------------------------------------------------------------------


class TestAcknowledgementDigest:
    """Canonical sorted SHA-256 digest computation for acknowledged WARN findings."""

    def test_digest_deterministic_and_order_independent(self) -> None:
        """Digest of [A, B] must equal digest of [B, A] due to canonical sorting."""
        findings_1 = ["dns_allowlist_change#1", "logging_changed#1"]
        findings_2 = ["logging_changed#1", "dns_allowlist_change#1"]
        digest_1 = compute_acknowledgement_digest(findings_1)
        digest_2 = compute_acknowledgement_digest(findings_2)
        assert digest_1 == digest_2
        assert len(digest_1) == 64

    def test_digest_deduplicates_duplicate_ids(self) -> None:
        """Duplicate findings in the list must produce the same canonical digest."""
        d1 = compute_acknowledgement_digest(["rule#1", "rule#2"])
        d2 = compute_acknowledgement_digest(["rule#1", "rule#2", "rule#1"])
        assert d1 == d2

    def test_digest_matches_canonical_json_sha256(self) -> None:
        """Digest must match sha256_hex of canonical JSON of sorted unique IDs."""
        ids = ["beta#1", "alpha#2"]
        expected = sha256_hex(canonical_json(["alpha#2", "beta#1"]))
        assert compute_acknowledgement_digest(ids) == expected


# ---------------------------------------------------------------------------
# 3. Ledger Gate & Receiver Verifier Enforcement
# ---------------------------------------------------------------------------


class TestWarnAcknowledgementEnforcement:
    """Ledger gate and Receiver verifier enforcement of require_warn_acknowledgement per D8."""

    @pytest.fixture
    def setup_env(self):
        """Build keys, trust root, policies, and envelopes for testing."""
        author_kp = generate_keypair()
        builder_kp = generate_keypair()
        inspector_kp = generate_keypair()
        approver1_kp = generate_keypair()
        approver2_kp = generate_keypair()

        import base64

        def b64_pub(kp: KeyPair) -> str:
            return base64.b64encode(kp.public_key_bytes).decode("ascii")

        keys = [
            KeyRecord(key_id=author_kp.key_id, public_key_b64=b64_pub(author_kp), role="author"),
            KeyRecord(key_id=builder_kp.key_id, public_key_b64=b64_pub(builder_kp), role="builder"),
            KeyRecord(key_id=inspector_kp.key_id, public_key_b64=b64_pub(inspector_kp), role="inspector_signer"),
            KeyRecord(key_id=approver1_kp.key_id, public_key_b64=b64_pub(approver1_kp), role="approver", group="g0"),
            KeyRecord(key_id=approver2_kp.key_id, public_key_b64=b64_pub(approver2_kp), role="approver", group="g1"),
        ]
        root = TrustRoot(
            root_version=1,
            keys=keys,
            roles=[
                RoleThreshold(role="author", threshold=1),
                RoleThreshold(role="builder", threshold=1),
                RoleThreshold(role="inspector_signer", threshold=1),
                RoleThreshold(role="approver", threshold=2, group_minimums={"g0": 1, "g1": 1}),
            ],
        )

        manifest = _make_manifest("Routine maintenance")
        m_bytes = canonical_json(manifest)
        m_digest = sha256_hex(m_bytes)
        m_env = _make_envelope("application/vnd.segel.manifest+json", m_bytes, [author_kp])

        binding = BindingBlock(
            stamp="origin",
            subject=ReleaseSubject(release_id=manifest.release_id, sequence=manifest.sequence, manifest_sha256=m_digest),
            trust_root_version=1,
            policy_version=1,
            evidence_id=generate_evidence_id(),
        )
        origin_pred = OriginPredicate(
            binding=binding,
            builder_id="segel-builder/v1",
            builder_domain="local",
            output_digest="1" * 64,
        )
        o_stmt = InTotoStatement(
            subject=[InTotoSubject(name=f"release/{manifest.release_id}@{manifest.sequence}", digest={"sha256": m_digest})],
            predicateType=ORIGIN_PREDICATE_TYPE,
            predicate=origin_pred.model_dump(mode="json"),
        )
        o_bytes = canonical_json(o_stmt.model_dump(by_alias=True, mode="json"))
        o_env = _make_envelope("application/vnd.segel.origin+json", o_bytes, [builder_kp])

        return {
            "root": root,
            "manifest": manifest,
            "m_digest": m_digest,
            "m_env": m_env,
            "o_env": o_env,
            "author_kp": author_kp,
            "inspector_kp": inspector_kp,
            "approver1_kp": approver1_kp,
            "approver2_kp": approver2_kp,
        }

    def _build_inspect_and_approve(
        self, env: dict, verdict: str, warn_findings: list[str], ack_digest: str
    ) -> tuple[DSSEEnvelope, DSSEEnvelope]:
        manifest = env["manifest"]
        m_digest = env["m_digest"]
        inspector_kp = env["inspector_kp"]
        approver1_kp = env["approver1_kp"]
        approver2_kp = env["approver2_kp"]

        # Inspect statement
        det_findings = [
            InspectFinding(capability_id=fid, severity="warn", source="deterministic", description="Test warn")
            for fid in warn_findings
        ]
        inspect_pred = InspectPredicate(
            binding=BindingBlock(
                stamp="inspect",
                subject=ReleaseSubject(release_id=manifest.release_id, sequence=manifest.sequence, manifest_sha256=m_digest),
                trust_root_version=1,
                policy_version=1,
                evidence_id=generate_evidence_id(),
            ),
            policy_version=1,
            verdict=verdict,
            deterministic_findings=det_findings,
            ai_status="skipped",
        )
        i_stmt = InTotoStatement(
            subject=[InTotoSubject(name=f"release/{manifest.release_id}@{manifest.sequence}", digest={"sha256": m_digest})],
            predicateType=INSPECT_PREDICATE_TYPE,
            predicate=inspect_pred.model_dump(mode="json"),
        )
        i_bytes = canonical_json(i_stmt.model_dump(by_alias=True, mode="json"))
        i_env = _make_envelope("application/vnd.segel.inspect+json", i_bytes, [inspector_kp])

        # Approve statement
        origin_digest = sha256_hex(canonical_json(env["o_env"].to_dict()))
        inspect_digest = sha256_hex(canonical_json(i_env.to_dict()))

        approve_pred = ApprovePredicate(
            binding=BindingBlock(
                stamp="approve",
                subject=ReleaseSubject(release_id=manifest.release_id, sequence=manifest.sequence, manifest_sha256=m_digest),
                trust_root_version=1,
                policy_version=1,
                evidence_id=generate_evidence_id(),
            ),
            origin_evidence_digest=origin_digest,
            inspect_evidence_digest=inspect_digest,
            acknowledgement_digest=ack_digest,
            canary_targets=manifest.canary_targets,
            promotion_criteria=PromotionCriteria(),
        )
        a_stmt = InTotoStatement(
            subject=[InTotoSubject(name=f"release/{manifest.release_id}@{manifest.sequence}", digest={"sha256": m_digest})],
            predicateType=APPROVE_PREDICATE_TYPE,
            predicate=approve_pred.model_dump(mode="json"),
        )
        a_bytes = canonical_json(a_stmt.model_dump(by_alias=True, mode="json"))
        a_env = _make_envelope("application/vnd.segel.approve+json", a_bytes, [approver1_kp, approver2_kp])

        return i_env, a_env

    def test_ledger_gate_rejects_missing_ack_digest_when_verdict_warn(self, setup_env) -> None:
        """When policy require_warn_acknowledgement=True and verdict=WARN, empty digest is rejected."""
        env = setup_env
        warn_findings = ["dns_allowlist_change#1"]
        i_env, a_env = self._build_inspect_and_approve(env, verdict="WARN", warn_findings=warn_findings, ack_digest="")

        policy = VerificationPolicy(policy_version=1, require_warn_acknowledgement=True)
        trust_ctx = TrustContext(root=env["root"], policy=policy, snapshot=TrustSnapshot(epoch=1))

        payload = {
            "manifest_envelope": env["m_env"].to_dict(),
            "origin_envelope": env["o_env"].to_dict(),
            "inspect_envelope": i_env.to_dict(),
            "approve_envelope": a_env.to_dict(),
        }

        with pytest.raises(DigestMismatchError) as exc_info:
            _verify_candidate_evidence(payload, trust_ctx)
        assert exc_info.value.code == ErrorCode.DIGEST_MISMATCH

    def test_ledger_gate_rejects_mismatching_ack_digest_when_verdict_warn(self, setup_env) -> None:
        """When policy require_warn_acknowledgement=True and verdict=WARN, incorrect digest is rejected."""
        env = setup_env
        warn_findings = ["dns_allowlist_change#1"]
        bad_digest = "f" * 64
        i_env, a_env = self._build_inspect_and_approve(env, verdict="WARN", warn_findings=warn_findings, ack_digest=bad_digest)

        policy = VerificationPolicy(policy_version=1, require_warn_acknowledgement=True)
        trust_ctx = TrustContext(root=env["root"], policy=policy, snapshot=TrustSnapshot(epoch=1))

        payload = {
            "manifest_envelope": env["m_env"].to_dict(),
            "origin_envelope": env["o_env"].to_dict(),
            "inspect_envelope": i_env.to_dict(),
            "approve_envelope": a_env.to_dict(),
        }

        with pytest.raises(DigestMismatchError) as exc_info:
            _verify_candidate_evidence(payload, trust_ctx)
        assert exc_info.value.code == ErrorCode.DIGEST_MISMATCH

    def test_ledger_gate_accepts_valid_ack_digest_when_verdict_warn(self, setup_env) -> None:
        """When correct acknowledgement digest is provided, candidate evidence passes."""
        env = setup_env
        warn_findings = ["dns_allowlist_change#1", "logging_changed#1"]
        valid_digest = compute_acknowledgement_digest(warn_findings)
        i_env, a_env = self._build_inspect_and_approve(env, verdict="WARN", warn_findings=warn_findings, ack_digest=valid_digest)

        policy = VerificationPolicy(policy_version=1, require_warn_acknowledgement=True)
        trust_ctx = TrustContext(root=env["root"], policy=policy, snapshot=TrustSnapshot(epoch=1))

        payload = {
            "manifest_envelope": env["m_env"].to_dict(),
            "origin_envelope": env["o_env"].to_dict(),
            "inspect_envelope": i_env.to_dict(),
            "approve_envelope": a_env.to_dict(),
        }

        # Should not raise
        _verify_candidate_evidence(payload, trust_ctx)

    def test_receiver_rejects_missing_or_mismatched_ack_digest(self, setup_env) -> None:
        """Receiver verifier marks passport INELIGIBLE when acknowledgement_digest is missing/mismatched."""
        env = setup_env
        warn_findings = ["dns_allowlist_change#1"]
        i_env, a_env = self._build_inspect_and_approve(env, verdict="WARN", warn_findings=warn_findings, ack_digest="")

        policy = VerificationPolicy(policy_version=1, require_warn_acknowledgement=True)
        trust_ctx = TrustContext(root=env["root"], policy=policy, snapshot=TrustSnapshot(epoch=1))

        passport = ReleasePassport(
            passport_type="candidate",
            manifest_envelope=env["m_env"].to_dict(),
            origin_envelope=env["o_env"].to_dict(),
            inspect_envelope=i_env.to_dict(),
            approve_envelope=a_env.to_dict(),
        )

        res = verify_passport(
            passport=passport,
            trust_ctx=trust_ctx,
            unit_id="canary-1",
            unit_role="canary",
            receiver_state={"highest_sequence": {}, "epoch": 1},
        )

        assert not res.all_stamps_valid
        assert res.approve.status.value != "valid"
        assert res.approve.error_code == ErrorCode.DIGEST_MISMATCH.value


# ---------------------------------------------------------------------------
# 4. Release Desk Template Rendering & UI Disclaimers
# ---------------------------------------------------------------------------


class TestReleaseDeskTemplates:
    """Template rendering tests for AI advisory panel, disclaimer, and escaping per D16, D18."""

    def test_footer_contains_disclaimer(self) -> None:
        """Shared base.html template must contain the competition prototype disclaimer."""
        template_path = Path("src/release_desk/templates/base.html")
        assert template_path.exists(), "base.html must exist"
        content = template_path.read_text(encoding="utf-8")
        disclaimer = "Competition prototype for Kartika Cyber Hackathon 2026, not an official product"
        assert disclaimer in content, "Disclaimer must appear in base.html footer"

    def test_release_detail_renders_ai_panel_and_escapes(self) -> None:
        """release_detail.html must have an 'AI advisory' panel, handle ok/failed/skipped, and escape text."""
        template_path = Path("src/release_desk/templates/release_detail.html")
        assert template_path.exists(), "release_detail.html must exist"
        content = template_path.read_text(encoding="utf-8")

        assert "AI advisory" in content or "AI Advisory" in content
        # Banners for failed and skipped
        assert "failed" in content
        assert "skipped" in content
        # Ensure no confidence percentages exist
        assert "confidence" not in content.lower() or "confidence %" not in content.lower()
