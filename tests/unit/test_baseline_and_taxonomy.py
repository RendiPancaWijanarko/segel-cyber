# SPDX-License-Identifier: MIT
"""Unit tests for Baseline v1 schema parsing and structured capability extraction.

Tests capability extraction per kind, duplicate key rejection, Pydantic extra=forbid,
huge value handling, determinism, instance ID format, and predecessor diffing.
"""

from __future__ import annotations

import json

import pytest
from pydantic import ValidationError

from inspector.baseline import (
    diff_capabilities,
    extract_capabilities_structured,
    parse_baseline_v1,
)
from inspector.inspector import extract_capabilities


class TestBaselineV1SchemaParsing:
    """Tests for Baseline v1 JSON parsing with duplicate key rejection."""

    def test_valid_baseline_parsing(self) -> None:
        data = {
            "firewall": {
                "outbound_allowed": [
                    {"destination": "10.0.0.1", "port": 443, "proto": "tcp"},
                ]
            },
            "dns_allowlist": ["1.1.1.1", "8.8.8.8"],
            "services": {"enabled": ["chrony"], "disabled": ["telnet"]},
            "accounts": [
                {"name": "op1", "privilege": "operator"},
                {"name": "admin1", "privilege": "admin"},
            ],
            "logging": {"enabled": True, "destination": "/var/log/syslog"},
            "scheduled_tasks": ["/usr/local/bin/sync-time.sh"],
            "trust_anchors": ["sha256:abcd1234efgh5678"],
        }
        raw = json.dumps(data).encode("utf-8")
        baseline = parse_baseline_v1(raw)
        assert len(baseline.dns_allowlist) == 2
        assert len(baseline.firewall.outbound_allowed) == 1
        assert len(baseline.accounts) == 2
        assert baseline.logging.enabled is True

    def test_duplicate_keys_top_level_rejected(self) -> None:
        raw = b'{"dns_allowlist": ["1.1.1.1"], "dns_allowlist": ["8.8.8.8"]}'
        with pytest.raises(ValueError, match="Duplicate key detected"):
            parse_baseline_v1(raw)

    def test_duplicate_keys_nested_rejected(self) -> None:
        raw = b'{"firewall": {"outbound_allowed": [], "outbound_allowed": []}}'
        with pytest.raises(ValueError, match="Duplicate key detected"):
            parse_baseline_v1(raw)

    def test_extra_top_level_key_rejected(self) -> None:
        raw = b'{"unauthorized_key": "injected", "dns_allowlist": []}'
        with pytest.raises(ValidationError):
            parse_baseline_v1(raw)

    def test_extra_nested_key_rejected(self) -> None:
        raw = b'{"firewall": {"outbound_allowed": [], "injected": true}}'
        with pytest.raises(ValidationError):
            parse_baseline_v1(raw)

    def test_extra_account_key_rejected(self) -> None:
        raw = b'{"accounts": [{"name": "u", "privilege": "op", "extra": 1}]}'
        with pytest.raises(ValidationError):
            parse_baseline_v1(raw)

    def test_huge_values_handled_safely(self) -> None:
        huge_string = "a" * 100_000
        data = {
            "dns_allowlist": [f"{huge_string}.example.com"],
            "scheduled_tasks": [huge_string],
        }
        raw = json.dumps(data).encode("utf-8")
        baseline = parse_baseline_v1(raw)
        assert len(baseline.dns_allowlist[0]) > 100_000


class TestStructuredCapabilityExtraction:
    """Tests for structured capability extraction and taxonomy kinds."""

    def test_dns_allowlist_change_positive_and_negative(self) -> None:
        pos_files = {
            "baseline.json": json.dumps({"dns_allowlist": ["10.1.1.53", "10.1.1.54"]}).encode(
                "utf-8"
            )
        }
        caps = extract_capabilities_structured(pos_files)
        kinds = [c["capability_id"] for c in caps]
        assert kinds == ["dns_allowlist_change", "dns_allowlist_change"]
        assert caps[0]["instance_id"] == "dns_allowlist_change#1"
        assert caps[0]["destination"] == "10.1.1.53"
        assert caps[1]["instance_id"] == "dns_allowlist_change#2"

        # Negative
        neg_files = {"baseline.json": json.dumps({"dns_allowlist": []}).encode("utf-8")}
        neg_caps = extract_capabilities_structured(neg_files)
        assert not any(c["capability_id"] == "dns_allowlist_change" for c in neg_caps)

    def test_outbound_rule_added_positive_and_negative(self) -> None:
        pos_files = {
            "baseline.json": json.dumps({
                "firewall": {
                    "outbound_allowed": [
                        {"destination": "192.168.1.100", "port": 53, "proto": "udp"},
                        {"destination": "10.0.0.5", "port": 443, "proto": "tcp"},
                    ]
                }
            }).encode("utf-8")
        }
        caps = extract_capabilities_structured(pos_files)
        outbound = [c for c in caps if c["capability_id"] == "outbound_rule_added"]
        assert len(outbound) == 2
        assert outbound[0]["instance_id"] == "outbound_rule_added#1"
        assert outbound[0]["destination"] == "192.168.1.100"
        assert outbound[0]["port"] == 53
        assert outbound[0]["proto"] == "udp"

        neg_files = {"baseline.json": json.dumps({"firewall": {"outbound_allowed": []}}).encode("utf-8")}
        neg_caps = extract_capabilities_structured(neg_files)
        assert not any(c["capability_id"] == "outbound_rule_added" for c in neg_caps)

    def test_account_added_and_privilege_granted_positive_and_negative(self) -> None:
        # Operator only -> account_added only, no privilege_granted
        op_files = {
            "baseline.json": json.dumps({
                "accounts": [{"name": "jdoe", "privilege": "operator"}]
            }).encode("utf-8")
        }
        caps_op = extract_capabilities_structured(op_files)
        assert any(c["capability_id"] == "account_added" for c in caps_op)
        assert not any(c["capability_id"] == "privilege_granted" for c in caps_op)

        # Admin account -> both account_added and privilege_granted
        admin_files = {
            "baseline.json": json.dumps({
                "accounts": [{"name": "root_user", "privilege": "admin"}]
            }).encode("utf-8")
        }
        caps_admin = extract_capabilities_structured(admin_files)
        assert any(c["capability_id"] == "account_added" for c in caps_admin)
        priv_cap = [c for c in caps_admin if c["capability_id"] == "privilege_granted"]
        assert len(priv_cap) == 1
        assert priv_cap[0]["instance_id"] == "privilege_granted#1"
        assert priv_cap[0]["account"] == "root_user"

    def test_logging_changed_and_disabled_positive_and_negative(self) -> None:
        # Logging enabled with destination -> logging_changed
        enabled_files = {
            "baseline.json": json.dumps({
                "logging": {"enabled": True, "destination": "syslog.corp.local"}
            }).encode("utf-8")
        }
        caps_enabled = extract_capabilities_structured(enabled_files)
        assert any(c["capability_id"] == "logging_changed" for c in caps_enabled)
        assert not any(c["capability_id"] == "logging_disabled" for c in caps_enabled)

        # Logging disabled -> logging_disabled
        disabled_files = {
            "baseline.json": json.dumps({
                "logging": {"enabled": False, "destination": ""}
            }).encode("utf-8")
        }
        caps_disabled = extract_capabilities_structured(disabled_files)
        assert any(c["capability_id"] == "logging_disabled" for c in caps_disabled)

    def test_service_enabled_and_disabled_positive_and_negative(self) -> None:
        files = {
            "baseline.json": json.dumps({
                "services": {"enabled": ["rsyslog"], "disabled": ["telnet", "rsh"]}
            }).encode("utf-8")
        }
        caps = extract_capabilities_structured(files)
        en = [c for c in caps if c["capability_id"] == "service_enabled"]
        dis = [c for c in caps if c["capability_id"] == "service_disabled"]
        assert len(en) == 1
        assert en[0]["value"] == "rsyslog"
        assert len(dis) == 2
        assert dis[0]["instance_id"] == "service_disabled#1"
        assert dis[1]["instance_id"] == "service_disabled#2"

    def test_scheduled_task_and_trust_anchor(self) -> None:
        files = {
            "baseline.json": json.dumps({
                "scheduled_tasks": ["cron_backup"],
                "trust_anchors": ["cert_fingerprint_01"],
            }).encode("utf-8")
        }
        caps = extract_capabilities_structured(files)
        tasks = [c for c in caps if c["capability_id"] == "scheduled_task_added"]
        anchors = [c for c in caps if c["capability_id"] == "trust_anchor_added"]
        assert len(tasks) == 1
        assert tasks[0]["value"] == "cron_backup"
        assert len(anchors) == 1
        assert anchors[0]["value"] == "cert_fingerprint_01"


class TestDeterminismAndInstanceIdStability:
    """Tests deterministic ordering and instance-ID stability."""

    def test_instance_id_format_and_ordering(self) -> None:
        files = {
            "b_conf.json": json.dumps({"dns_allowlist": ["2.2.2.2"]}).encode("utf-8"),
            "a_conf.json": json.dumps({"dns_allowlist": ["1.1.1.1"]}).encode("utf-8"),
        }
        caps1 = extract_capabilities_structured(files)
        caps2 = extract_capabilities_structured(files)

        # Deterministic between runs
        assert caps1 == caps2

        # Stable order: file path first (a_conf.json before b_conf.json)
        assert caps1[0]["file"] == "a_conf.json"
        assert caps1[0]["instance_id"] == "dns_allowlist_change#1"
        assert caps1[0]["destination"] == "1.1.1.1"

        assert caps1[1]["file"] == "b_conf.json"
        assert caps1[1]["instance_id"] == "dns_allowlist_change#2"
        assert caps1[1]["destination"] == "2.2.2.2"


class TestPredecessorDiffAndBroadChange:
    """Tests diff_capabilities and broad_change trigger threshold."""

    def test_diff_capabilities_new_changed_removed(self) -> None:
        prev = {
            "dns_allowlist": ["1.1.1.1", "8.8.8.8"],
            "services": {"enabled": ["ssh"], "disabled": ["telnet"]},
            "accounts": [{"name": "alice", "privilege": "user"}],
        }
        curr = {
            "dns_allowlist": ["1.1.1.1", "9.9.9.9"],  # removed 8.8.8.8, added 9.9.9.9
            "services": {"enabled": ["chrony"], "disabled": ["telnet"]},  # removed ssh, added chrony
            "accounts": [{"name": "alice", "privilege": "operator"}],  # changed privilege
        }
        diff = diff_capabilities(prev, curr)
        assert "new" in diff
        assert "changed" in diff
        assert "removed" in diff

        assert len(diff["changed"]) >= 1  # alice privilege user -> operator
        assert any(item["setting"] == "account" and item["account"] == "alice" for item in diff["changed"])

    def test_broad_change_threshold_below_8(self) -> None:
        # 7 differences -> broad_change NOT emitted (7 additions relative to empty)
        prev_exact = {"dns_allowlist": []}
        curr_exact = {"dns_allowlist": [f"10.0.0.{i}" for i in range(7)]}

        files_curr = {"baseline.json": json.dumps(curr_exact).encode("utf-8")}
        files_prev = {"baseline.json": json.dumps(prev_exact).encode("utf-8")}

        caps = extract_capabilities_structured(files_curr, predecessor_files=files_prev)
        assert not any(c["capability_id"] == "broad_change" for c in caps)

    def test_broad_change_threshold_8_or_more(self) -> None:
        # 8 differences -> broad_change IS emitted
        prev_exact = {"dns_allowlist": []}
        curr_exact = {"dns_allowlist": [f"10.0.0.{i}" for i in range(8)]}

        files_curr = {"baseline.json": json.dumps(curr_exact).encode("utf-8")}
        files_prev = {"baseline.json": json.dumps(prev_exact).encode("utf-8")}

        caps = extract_capabilities_structured(files_curr, predecessor_files=files_prev)
        broad = [c for c in caps if c["capability_id"] == "broad_change"]
        assert len(broad) == 1
        assert broad[0]["instance_id"] == "broad_change#1"
        assert int(broad[0]["value"]) >= 8


class TestRegexFallbackPreservation:
    """Tests that existing regex paths remain untouched and functional."""

    def test_yaml_files_fall_back_to_regex(self) -> None:
        files = {
            "app.yaml": b"server:\n  port: 8080\n",
            "db.yaml": b"password: mysecret\n",
        }
        caps = extract_capabilities(files)
        kinds = {c["capability_id"] for c in caps}
        assert "network_listen" in kinds
        assert "credential_reference" in kinds
        # Instance IDs assigned to regex caps as well
        port_cap = next(c for c in caps if c["capability_id"] == "network_listen")
        assert port_cap["instance_id"] == "network_listen#1"
