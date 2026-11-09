# SPDX-License-Identifier: MIT
"""Unit tests for the Inspector component.

Tests capability extraction, policy evaluation, and inspect attestation.
"""

import pytest

from inspector.inspector import (
    create_inspect_attestation,
    evaluate_policy,
    extract_capabilities,
    inspect_release,
    sign_inspect,
)
from segel_core.canonical import canonical_json
from segel_core.crypto.dsse import verify_envelope
from segel_core.crypto.ed25519 import generate_keypair
from segel_core.crypto.hashing import sha256_hex
from segel_core.schemas.manifest import Manifest, SubjectDigest


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


class TestRegexIdentifierBoundaries:
    """Test regex pattern identifier boundaries and false-match prevention (AI-2b)."""

    @pytest.mark.parametrize(
        ("content", "false_word"),
        [
            (b"import: true\n", "import:"),
            (b"support: 24x7\n", "support:"),
            (b"report: /var/log/report.txt\n", "report:"),
            (b"pseudo: false\n", "pseudo:"),
            (b"oauth: v2\n", "oauth:"),
            (b"nameserver: 1.1.1.1\n", "nameserver:"),
            (b"csrftoken: abcdef123456\n", "csrftoken:"),
            (b"author: devsecops\n", "author:"),
            (b"antiforgerytoken: xyz\n", "antiforgerytoken:"),
            (b"teleport: disabled\n", "teleport:"),
            (b"webserver: nginx\n", "webserver:"),
            (b"desudo: true\n", "desudo:"),
            (b"app_sudo: false\n", "app_sudo:"),
            (b"app_port: 8080\n", "app_port:"),
        ],
    )
    def test_false_match_produces_no_capabilities(self, content: bytes, false_word: str) -> None:
        """Assert that words embedding regex substrings do not produce capabilities."""
        caps = extract_capabilities({"config.yaml": content})
        assert len(caps) == 0, f"Expected 0 capabilities for '{false_word}', got: {caps}"

    def test_combined_false_matches_produce_no_capabilities(self) -> None:
        """Assert that a configuration with multiple common false-match keywords produces nothing."""
        content = (
            b"# System configuration\n"
            b"import: standard\n"
            b"support: helpdesk@internal\n"
            b"report: weekly\n"
            b"pseudo: none\n"
            b"oauth: internal_sso\n"
            b"nameserver: 10.0.0.53\n"
            b"csrftoken: csrf_token_val\n"
            b"author: release_engineer\n"
        )
        caps = extract_capabilities({"config/settings.yaml": content})
        assert len(caps) == 0, f"Expected 0 capabilities for false matches, got: {caps}"

    @pytest.mark.parametrize(
        ("content", "expected_cap"),
        [
            # network_listen
            (b"port: 8080\n", "network_listen"),
            (b"port = 8080\n", "network_listen"),
            (b"  port: 443\n", "network_listen"),
            (b"server: localhost\n", "network_listen"),
            (b"listen: 0.0.0.0\n", "network_listen"),
            (b"bind_address: 127.0.0.1\n", "network_listen"),
            # file_write
            (b"log_file: /var/log/app.log\n", "file_write"),
            (b"output_path: /tmp/out\n", "file_write"),
            (b"write_dir: /tmp/write\n", "file_write"),
            (b"data_dir: /var/data\n", "file_write"),
            # external_connect
            (b"upstream: http://backend:8080\n", "external_connect"),
            (b"remote_host: egress.domain.local\n", "external_connect"),
            (b"proxy: http://proxy:3128\n", "external_connect"),
            (b"api_url: https://api.internal\n", "external_connect"),
            # credential_reference
            (b"auth: basic\n", "credential_reference"),
            (b"token: eyJhbGciOi...\n", "credential_reference"),
            (b"password: mysecret\n", "credential_reference"),
            (b"secret: s3cr3t\n", "credential_reference"),
            (b"api_key: key-999\n", "credential_reference"),
            # privilege_escalation
            (b"sudo: ALL=(ALL)\n", "privilege_escalation"),
            (b"run_as_root: true\n", "privilege_escalation"),
            (b"privileged: yes\n", "privilege_escalation"),
        ],
    )
    def test_intended_positive_controls_detected(self, content: bytes, expected_cap: str) -> None:
        """Assert that intended positive keywords with boundaries are correctly detected."""
        caps = extract_capabilities({"config.yaml": content})
        cap_ids = {c["capability_id"] for c in caps}
        assert expected_cap in cap_ids, f"Expected '{expected_cap}' in {cap_ids} for content {content!r}"


