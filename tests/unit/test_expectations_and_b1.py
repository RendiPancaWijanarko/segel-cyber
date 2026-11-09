# SPDX-License-Identifier: MIT
"""Unit tests for deterministic expectation check and B1 keyword classifier.

Per docs/ai_decisions.md (D6, D15, D17):
- Expectation map in src/inspector/policy/expectations.py.
- derive_findings(purpose_class, capabilities) -> findings.
- B1 keyword classifier: single-class match returns L1..L5, abstains (None) on
  zero or multiple matches; never returns L6.
- Integration into inspect_release.
"""

from __future__ import annotations

from inspector.inspector import inspect_release
from inspector.policy.expectations import (
    EXPECTATION_MAP,
    classify_purpose_b1,
    derive_findings,
)
from segel_core.schemas.manifest import Manifest, SubjectDigest


def test_expectation_map_structure() -> None:
    """Validate canonical expectation map classes and capabilities."""
    assert set(EXPECTATION_MAP.keys()) == {"L1", "L2", "L3", "L4", "L5", "L6"}
    assert EXPECTATION_MAP["L1"] == {"dns_allowlist_change"}
    assert EXPECTATION_MAP["L2"] == {"account_added"}
    assert EXPECTATION_MAP["L3"] == {"logging_changed"}
    assert EXPECTATION_MAP["L4"] == {"outbound_rule_added"}
    assert EXPECTATION_MAP["L5"] == {"service_disabled"}
    assert EXPECTATION_MAP["L6"] == set()


def test_derive_findings_abstain() -> None:
    """When purpose_class is None, derive_findings abstains (returns empty list)."""
    caps = [{"capability_id": "outbound_rule_added"}]
    findings = derive_findings(None, caps)
    assert findings == []


def test_derive_findings_consistent() -> None:
    """When all capabilities are expected, derive_findings returns no warning findings."""
    caps = [{"capability_id": "dns_allowlist_change"}]
    findings = derive_findings("L1", caps)
    assert len(findings) == 0


def test_derive_findings_inconsistent_warn() -> None:
    """When unexpected capabilities are present, derive_findings generates warn findings."""
    caps = [
        {"capability_id": "dns_allowlist_change"},
        {"capability_id": "outbound_rule_added"},
        {"capability_id": "service_enabled"},
    ]
    findings = derive_findings("L1", caps)
    warn_ids = {f.capability_id for f in findings if f.severity == "warn"}
    assert warn_ids == {"outbound_rule_added", "service_enabled"}
    for f in findings:
        assert f.severity == "warn"
        assert f.source == "deterministic"


def test_derive_findings_l6_vague() -> None:
    """L6 plus any capability yields one warn 'purpose too vague to verify'."""
    caps = [{"capability_id": "account_added"}]
    findings = derive_findings("L6", caps)
    assert len(findings) == 1
    assert findings[0].severity == "warn"
    assert "purpose too vague to verify" in findings[0].description.lower()

    # L6 with no capabilities yields no findings
    assert derive_findings("L6", []) == []


def test_classify_purpose_b1_single_class() -> None:
    """B1 classifies single-class purpose in Indonesian and English."""
    # L1
    assert classify_purpose_b1("Pembaruan alamat DNS resolver kantor cabang") == "L1"
    assert classify_purpose_b1("Update DNS forwarder configuration") == "L1"

    # L2
    assert classify_purpose_b1("Penambahan akun operator monitoring jaringan") == "L2"
    assert classify_purpose_b1("Create user account for remote technician") == "L2"

    # L3
    assert classify_purpose_b1("Pengalihan tujuan log audit ke syslog terpusat") == "L3"
    assert classify_purpose_b1("Update centralized audit log target") == "L3"

    # L4
    assert classify_purpose_b1("Penambahan aturan firewall keluar untuk server baru") == "L4"
    assert classify_purpose_b1("Add outbound egress rule for remote connection") == "L4"

    # L5
    assert classify_purpose_b1("Hardening node dengan menonaktifkan layanan tidak aman") == "L5"
    assert classify_purpose_b1("Disable unused legacy services for hardening") == "L5"


def test_classify_purpose_b1_abstains() -> None:
    """B1 abstains (returns None) on no match, multi-class match, or vague purpose."""
    # No match
    assert classify_purpose_b1("Initial baseline setup") is None
    assert classify_purpose_b1("Miscellaneous bug fixes") is None

    # Multi-class conflict (e.g. DNS resolver + user account)
    assert classify_purpose_b1("Pembaruan DNS resolver dan penambahan akun operator") is None
    assert classify_purpose_b1("Update firewall outbound rule and disable services") is None

    # Vague purpose: B1 never returns L6
    assert classify_purpose_b1("Routine system maintenance update") is None


def test_classify_purpose_b1_word_boundaries() -> None:
    """B1 uses word boundaries so common words do not trigger false matches."""
    # 'import' should not match 'port'
    assert classify_purpose_b1("Import system configuration data") is None
    # 'support' should not match 'port'
    assert classify_purpose_b1("Provide technical support") is None
    # 'author' should not match 'auth'
    assert classify_purpose_b1("Package author verification") is None


def test_inspect_release_b1_integration() -> None:
    """inspect_release applies expectation check when B1 matches and abstains otherwise."""
    manifest_sha = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"

    # Manifest with L1 purpose and baseline JSON having DNS + extra outbound rule
    baseline_json = b'{"firewall":{"outbound_allowed":[{"destination":"1.1.1.1","port":443,"proto":"tcp"}]},"dns_allowlist":["10.0.0.1"],"services":{"enabled":[],"disabled":[]},"accounts":[],"logging":{"enabled":true,"destination":""},"scheduled_tasks":[],"trust_anchors":[]}'

    valid_sha = "a" * 64
    manifest_l1 = Manifest(
        release_id="REL-TEST-01",
        sequence=1,
        purpose="Pembaruan DNS resolver cabang",
        subjects=[SubjectDigest(path="baseline.json", sha256=valid_sha, size=100)],
    )

    result_l1 = inspect_release(
        files={"baseline.json": baseline_json},
        manifest=manifest_l1,
        manifest_digest=manifest_sha,
    )

    # Expectation check should have flagged outbound_rule_added as unexpected for L1
    exp_findings = [
        f for f in result_l1.deterministic_findings
        if f.capability_id == "outbound_rule_added" and f.severity == "warn"
    ]
    assert len(exp_findings) >= 1
    assert result_l1.verdict == "WARN"

    # Manifest with unclassified purpose: B1 abstains, verdict remains PASS
    manifest_unclassified = Manifest(
        release_id="REL-TEST-02",
        sequence=2,
        purpose="General update",
        subjects=[SubjectDigest(path="baseline.json", sha256=valid_sha, size=100)],
    )

    result_unclass = inspect_release(
        files={"baseline.json": baseline_json},
        manifest=manifest_unclassified,
        manifest_digest=manifest_sha,
    )

    # When B1 abstains, no expectation mismatch warning is added
    exp_warns = [
        f for f in result_unclass.deterministic_findings
        if "unexpected" in f.description.lower()
    ]
    assert len(exp_warns) == 0
