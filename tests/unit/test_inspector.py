# SPDX-License-Identifier: MIT
"""Unit tests for the Inspector component.

Tests capability extraction, policy evaluation, and inspect attestation.
"""

import pytest

from inspector.inspector import (
    extract_capabilities,
    evaluate_policy,
    inspect_release,
    create_inspect_attestation,
    sign_inspect,
    CAPABILITY_RULES,
    POLICY_RULES_V1,
)
from segel_core.crypto.ed25519 import generate_keypair
from segel_core.crypto.dsse import verify_envelope
from segel_core.crypto.hashing import sha256_hex
from segel_core.schemas.manifest import Manifest, SubjectDigest
from segel_core.canonical import canonical_json


def _make_manifest(release_id="TEST-1", sequence=1):
    m = Manifest(
        release_id=release_id,
        sequence=sequence,
        purpose="test",
        subjects=[SubjectDigest(path="config/a.yaml", sha256="a" * 64, size=10)],
    )
    return m, sha256_hex(canonical_json(m))


class TestExtractCapabilities:
    """Test deterministic capability extraction."""

    def test_network_listen_detected(self):
        files = {"config/app.yaml": b"server:\n  port: 8080\n  host: 0.0.0.0\n"}
        caps = extract_capabilities(files)
        cap_ids = {c["capability_id"] for c in caps}
        assert "network_listen" in cap_ids

    def test_file_write_detected(self):
        files = {"config/logging.yaml": b"log_file: /var/log/app.log\n"}
        caps = extract_capabilities(files)
        cap_ids = {c["capability_id"] for c in caps}
        assert "file_write" in cap_ids

    def test_external_connect_detected(self):
        files = {"config/proxy.yaml": b"upstream: http://backend:9090\n"}
        caps = extract_capabilities(files)
        cap_ids = {c["capability_id"] for c in caps}
        assert "external_connect" in cap_ids

    def test_credential_reference_detected(self):
        files = {"config/db.yaml": b"password: s3cret\napi_key: abc123\n"}
        caps = extract_capabilities(files)
        cap_ids = {c["capability_id"] for c in caps}
        assert "credential_reference" in cap_ids

    def test_privilege_escalation_detected(self):
        files = {"config/run.yaml": b"run_as_root: true\n"}
        caps = extract_capabilities(files)
        cap_ids = {c["capability_id"] for c in caps}
        assert "privilege_escalation" in cap_ids

    def test_no_capabilities(self):
        files = {"config/simple.yaml": b"greeting: hello\ncount: 42\n"}
        caps = extract_capabilities(files)
        assert len(caps) == 0

    def test_multiple_files(self):
        files = {
            "config/a.yaml": b"port: 8080\n",
            "config/b.yaml": b"log_file: /tmp/app.log\n",
        }
        caps = extract_capabilities(files)
        cap_ids = {c["capability_id"] for c in caps}
        assert "network_listen" in cap_ids
        assert "file_write" in cap_ids

    def test_capability_has_location(self):
        files = {"config/app.yaml": b"line1\nport: 8080\nline3\n"}
        caps = extract_capabilities(files)
        port_caps = [c for c in caps if c["capability_id"] == "network_listen"]
        assert len(port_caps) >= 1
        assert port_caps[0]["file"] == "config/app.yaml"
        assert port_caps[0]["line"] == 2

    def test_binary_files_skipped(self):
        files = {"config/data.bin": b"\x00\x01\x02\xff\xfe"}
        caps = extract_capabilities(files)
        # Should not crash on binary content
        assert isinstance(caps, list)


class TestEvaluatePolicy:
    """Test policy evaluation."""

    def test_pass_no_capabilities(self):
        verdict, findings = evaluate_policy([])
        assert verdict == "PASS"

    def test_pass_benign_capabilities(self):
        caps = [{"capability_id": "network_listen"}]
        verdict, findings = evaluate_policy(caps)
        assert verdict == "PASS"

    def test_warn_credential_reference(self):
        caps = [{"capability_id": "credential_reference"}]
        verdict, findings = evaluate_policy(caps)
        assert verdict == "WARN"

    def test_warn_external_connect(self):
        caps = [{"capability_id": "external_connect"}]
        verdict, findings = evaluate_policy(caps)
        assert verdict == "WARN"

    def test_reject_privilege_escalation(self):
        caps = [{"capability_id": "privilege_escalation"}]
        verdict, findings = evaluate_policy(caps)
        assert verdict == "REJECT"

    def test_reject_overrides_warn(self):
        caps = [
            {"capability_id": "credential_reference"},
            {"capability_id": "privilege_escalation"},
        ]
        verdict, findings = evaluate_policy(caps)
        assert verdict == "REJECT"

    def test_findings_have_structure(self):
        caps = [{"capability_id": "credential_reference"}]
        _, findings = evaluate_policy(caps)
        assert len(findings) > 0
        for f in findings:
            assert hasattr(f, "capability_id")
            assert hasattr(f, "severity")
            assert hasattr(f, "source")
            assert f.source == "deterministic"


class TestInspectRelease:
    """Test full inspect_release()."""

    def test_basic_inspection(self):
        files = {"config/app.yaml": b"server:\n  port: 8080\n"}
        manifest, digest = _make_manifest()
        result = inspect_release(files, manifest, digest, ai_enabled=False)
        assert result.verdict in ("PASS", "WARN", "REJECT")
        assert result.ai_status == "skipped"
        assert result.policy_version == 1
        assert len(result.capabilities) > 0

    def test_ai_disabled_by_default(self):
        files = {"config/a.yaml": b"key: value\n"}
        manifest, digest = _make_manifest()
        result = inspect_release(files, manifest, digest)
        assert result.ai_status == "skipped"
        assert result.ai_model_id == ""

    def test_ai_enabled_but_unavailable(self):
        """AI fails gracefully when Ollama is not available."""
        files = {"config/a.yaml": b"key: value\n"}
        manifest, digest = _make_manifest()
        result = inspect_release(files, manifest, digest, ai_enabled=True)
        assert result.ai_status == "failed"
        # AI failure should not change the deterministic verdict
        assert result.verdict in ("PASS", "WARN", "REJECT")


class TestInspectAttestation:
    """Test Inspect attestation creation and signing."""

    def test_create_attestation_structure(self):
        files = {"config/app.yaml": b"server:\n  port: 8080\n"}
        manifest, digest = _make_manifest()
        result = inspect_release(files, manifest, digest)
        stmt = create_inspect_attestation(result, manifest, digest)

        assert stmt["_type"] == "https://in-toto.io/Statement/v1"
        assert stmt["predicateType"] == "https://segel.dev/attestation/inspect/v1"
        pred = stmt["predicate"]
        assert pred["binding"]["stamp"] == "inspect"
        assert pred["verdict"] == result.verdict
        assert "deterministic_findings" in pred
        assert "capabilities" in pred

    def test_sign_inspect_valid(self):
        files = {"config/app.yaml": b"port: 8080\n"}
        manifest, digest = _make_manifest()
        result = inspect_release(files, manifest, digest)
        stmt = create_inspect_attestation(result, manifest, digest)

        inspector_key = generate_keypair()
        env = sign_inspect(stmt, inspector_key)
        assert env.payload_type == "application/vnd.segel.inspect+json"
        assert len(env.signatures) == 1

        from segel_core.crypto.ed25519 import PublicKeyInfo
        pub = PublicKeyInfo(
            key_id=inspector_key.key_id,
            public_key=inspector_key.public_key,
            public_key_bytes=inspector_key.public_key_bytes,
        )
        vr = verify_envelope(
            env, [pub],
            expected_payload_type="application/vnd.segel.inspect+json",
        )
        assert inspector_key.key_id in vr.valid_key_ids

