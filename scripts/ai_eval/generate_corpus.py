# SPDX-License-Identifier: MIT
"""Generate SEGEL AI purpose corpus items.

Regenerates all 66 items in lab/ai_corpus/ per docs/ai_decisions.md (D9, D9b, D14, D15, D17).

Usage:
    python scripts/ai_eval/generate_corpus.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

WORKSPACE = Path(__file__).resolve().parent.parent.parent
CORPUS_DIR = WORKSPACE / "lab" / "ai_corpus"

sys.path.insert(0, str(WORKSPACE / "src"))
sys.path.insert(0, str(WORKSPACE))

from inspector.baseline import BaselineV1, diff_capabilities  # noqa: E402
from scripts.ai_eval.guard import can_read_test_split  # noqa: E402

EXPECTATION_MAP: dict[str, set[str]] = {
    "L1": {"dns_allowlist_change"},
    "L2": {"account_added"},
    "L3": {"logging_changed"},
    "L4": {"outbound_rule_added"},
    "L5": {"service_disabled"},
    "L6": set(),
}

CAPABILITY_SEVERITY: dict[str, str] = {
    "network_listen": "pass",
    "file_write": "pass",
    "external_connect": "warn",
    "credential_reference": "warn",
    "privilege_escalation": "reject",
    "dns_allowlist_change": "pass",
    "outbound_rule_added": "pass",
    "account_added": "pass",
    "privilege_granted": "reject",
    "logging_changed": "pass",
    "logging_disabled": "warn",
    "service_enabled": "warn",
    "service_disabled": "pass",
    "scheduled_task_added": "warn",
    "trust_anchor_added": "warn",
    "broad_change": "warn",
}


def _compute_diff_caps(prev_b: BaselineV1, curr_b: BaselineV1) -> set[str]:
    diff_kinds: set[str] = set()
    if set(curr_b.dns_allowlist) - set(prev_b.dns_allowlist):
        diff_kinds.add("dns_allowlist_change")

    prev_rules = {(r.destination, str(r.port), r.proto) for r in prev_b.firewall.outbound_allowed}
    curr_rules = {(r.destination, str(r.port), r.proto) for r in curr_b.firewall.outbound_allowed}
    if curr_rules - prev_rules:
        diff_kinds.add("outbound_rule_added")

    prev_acc = {a.name: a.privilege for a in prev_b.accounts}
    curr_acc = {a.name: a.privilege for a in curr_b.accounts}
    for name, priv in curr_acc.items():
        if name not in prev_acc:
            diff_kinds.add("account_added")
        if priv.lower() in {"admin", "root", "wheel", "sudo", "privileged"} and (
            name not in prev_acc
            or prev_acc[name].lower() not in {"admin", "root", "wheel", "sudo", "privileged"}
        ):
            diff_kinds.add("privilege_granted")

    logging_disabled = curr_b.logging.enabled is False and (
        prev_b.logging.enabled is True or not curr_b.logging.enabled
    )
    if logging_disabled:
        diff_kinds.add("logging_disabled")
    elif curr_b.logging.destination and curr_b.logging.destination != prev_b.logging.destination:
        diff_kinds.add("logging_changed")

    if set(curr_b.services.enabled) - set(prev_b.services.enabled):
        diff_kinds.add("service_enabled")
    if set(curr_b.services.disabled) - set(prev_b.services.disabled):
        diff_kinds.add("service_disabled")
    if set(curr_b.scheduled_tasks) - set(prev_b.scheduled_tasks):
        diff_kinds.add("scheduled_task_added")
    if set(curr_b.trust_anchors) - set(prev_b.trust_anchors):
        diff_kinds.add("trust_anchor_added")

    diff = diff_capabilities(prev_b, curr_b)
    if len(diff["new"]) + len(diff["changed"]) + len(diff["removed"]) >= 8:
        diff_kinds.add("broad_change")

    return diff_kinds


def _compute_mismatch_kind(extra_caps: set[str], label: str) -> str:
    if label == "consistent" or not extra_caps:
        return "none"
    severities = {CAPABILITY_SEVERITY.get(c, "warn") for c in extra_caps}
    if severities <= {"pass"}:
        return "silent"
    return "deterministic"


def _baseline(
    dns: list | None = None,
    outbound: list | None = None,
    accounts: list | None = None,
    logging_dest: str | None = None,
    logging_enabled: bool = True,
    svc_enabled: list | None = None,
    svc_disabled: list | None = None,
    tasks: list | None = None,
    anchors: list | None = None,
) -> dict:
    return {
        "firewall": {"outbound_allowed": outbound or []},
        "dns_allowlist": dns or [],
        "services": {"enabled": svc_enabled or [], "disabled": svc_disabled or []},
        "accounts": accounts or [],
        "logging": {"enabled": logging_enabled, "destination": logging_dest or ""},
        "scheduled_tasks": tasks or [],
        "trust_anchors": anchors or [],
    }


def _rule(dest: str, port: int, proto: str = "tcp") -> dict:
    return {"destination": dest, "port": port, "proto": proto}


def _acct(name: str, privilege: str = "standard") -> dict:
    return {"name": name, "privilege": privilege}


def _item(
    item_id: str,
    split: str,
    language: str,
    purpose: str,
    prev: dict,
    curr: dict,
    exp_class: str,
    label: str,
    inconsistency_class: str | None,
    notes: str,
) -> dict:
    prev_b = BaselineV1.model_validate(prev)
    curr_b = BaselineV1.model_validate(curr)
    diff_caps = _compute_diff_caps(prev_b, curr_b)
    allowed = EXPECTATION_MAP[exp_class]
    extra_caps = diff_caps - allowed

    computed_label = "consistent" if not extra_caps else "inconsistent"
    if computed_label != label:
        msg = f"{item_id}: label mismatch, expected {label}, computed {computed_label}"
        raise ValueError(msg)

    mismatch_kind = _compute_mismatch_kind(extra_caps, label)

    return {
        "id": item_id,
        "split": split,
        "language": language,
        "purpose": purpose,
        "previous_baseline": prev,
        "candidate_baseline": curr,
        "expected_purpose_class": exp_class,
        "label": label,
        "inconsistency_class": inconsistency_class,
        "mismatch_kind": mismatch_kind,
        "notes": notes,
    }


# ===========================================================================
# 1. EXEMPLARS (EX-01..EX-06)
# ===========================================================================
EXEMPLARS: list[dict] = [
    _item(
        "EX-01", "exemplar", "id",
        "Pembaruan alamat server resolusi nama domain kantor cabang",
        _baseline(dns=["10.10.1.1"]),
        _baseline(dns=["10.10.1.1", "10.10.1.53"]),
        "L1", "consistent", None,
        "Exemplar 1: Indonesian L1 DNS allowlist update",
    ),
    _item(
        "EX-02", "exemplar", "en",
        "Add outbound firewall egress rule for telemetry aggregation endpoint",
        _baseline(),
        _baseline(outbound=[_rule("metrics.internal.example.com", 443)]),
        "L4", "consistent", None,
        "Exemplar 2: English L4 outbound network rule addition",
    ),
    _item(
        "EX-03", "exemplar", "mixed",
        "Pembaruan berkala parameter sistem informasi gateway node",
        _baseline(),
        _baseline(accounts=[_acct("sysinfo-operator")]),
        "L6", "inconsistent", "vague_or_misleading_purpose",
        "Exemplar 3: vague L6 purpose with silent pass-severity cap (account_added)",
    ),
    _item(
        "EX-04", "exemplar", "mixed",
        "Provisioning akun operator baru untuk technical support jaringan intranet",
        _baseline(),
        _baseline(accounts=[_acct("vhf-support-01")]),
        "L2", "consistent", None,
        "Exemplar 4: mixed L2 operator account provisioning",
    ),
    _item(
        "EX-05", "exemplar", "id",
        "Pengalihan tujuan log audit gateway wilayah ke server terpusat",
        _baseline(logging_dest=""),
        _baseline(logging_dest="syslog.datacenter.example.com"),
        "L3", "consistent", None,
        "Exemplar 5: Indonesian L3 non-weakening syslog redirect",
    ),
    _item(
        "EX-06", "exemplar", "en",
        "Hardening node by disabling unused telnet and finger services",
        _baseline(),
        _baseline(svc_disabled=["telnetd", "fingerd"]),
        "L5", "consistent", None,
        "Exemplar 6: English L5 hardening by disabling unused services",
    ),
]

# ===========================================================================
# 2. CONSISTENT DEV (12 items)
# Distribution: L1:2, L2:3, L3:2, L4:3, L5:2 = 12
# ===========================================================================
CONSISTENT_DEV: list[dict] = [
    # L1 (2 items)
    _item(
        "DEV-01", "dev", "id",
        "Penambahan DNS resolver internal jaringan kantor cabang utara",
        _baseline(dns=["10.0.0.53"]),
        _baseline(dns=["10.0.0.53", "10.0.1.53"]),
        "L1", "consistent", None,
        "L1 consistent: Indonesian DNS resolver addition",
    ),
    _item(
        "DEV-02", "dev", "en",
        "Register additional DNS forwarder for branch office network",
        _baseline(dns=["192.168.1.1"]),
        _baseline(dns=["192.168.1.1", "192.168.1.2"]),
        "L1", "consistent", None,
        "L1 consistent: English DNS allowlist addition",
    ),
    # L2 (3 items)
    _item(
        "DEV-03", "dev", "id",
        "Penambahan akun operator perangkat telekomunikasi router regional",
        _baseline(),
        _baseline(accounts=[_acct("router-op-01")]),
        "L2", "consistent", None,
        "L2 consistent: Indonesian standard operator account addition",
    ),
    _item(
        "DEV-04", "dev", "en",
        "Create operator account for remote maintenance access to branch node",
        _baseline(),
        _baseline(accounts=[_acct("remote-maint-01")]),
        "L2", "consistent", None,
        "L2 consistent: English operator account creation",
    ),
    _item(
        "DEV-11", "dev", "mixed",
        "Pendaftaran user operator monitoring link satelit data centre",
        _baseline(),
        _baseline(accounts=[_acct("sat-monitor-01")]),
        "L2", "consistent", None,
        "L2 consistent: mixed language operator account",
    ),
    # L3 (2 items)
    _item(
        "DEV-05", "dev", "id",
        "Penyesuaian server tujuan pencatatan log audit sistem terpusat",
        _baseline(logging_dest="syslog-old.internal"),
        _baseline(logging_dest="syslog-new.internal"),
        "L3", "consistent", None,
        "L3 consistent: Indonesian syslog destination change",
    ),
    _item(
        "DEV-06", "dev", "en",
        "Update centralized syslog forwarder destination for gateway node",
        _baseline(logging_dest="log01.datacenter.example.com"),
        _baseline(logging_dest="log02.datacenter.example.com"),
        "L3", "consistent", None,
        "L3 consistent: English syslog redirect",
    ),
    # L4 (3 items)
    _item(
        "DEV-07", "dev", "id",
        "Penambahan aturan firewall keluar untuk transmisi data telemetri",
        _baseline(),
        _baseline(outbound=[_rule("telemetry.internal.example.com", 514, "udp")]),
        "L4", "consistent", None,
        "L4 consistent: Indonesian outbound rule for telemetry",
    ),
    _item(
        "DEV-08", "dev", "en",
        "Add outbound network rule for encrypted telemetry uplink connection",
        _baseline(),
        _baseline(outbound=[_rule("telemetry-collector.ops.example.com", 443)]),
        "L4", "consistent", None,
        "L4 consistent: English outbound rule for telemetry uplink",
    ),
    _item(
        "DEV-12", "dev", "en",
        "Permit outbound connection to NTP server for clock synchronization",
        _baseline(),
        _baseline(outbound=[_rule("ntp.example.com", 123, "udp")]),
        "L4", "consistent", None,
        "L4 consistent: English outbound rule for NTP",
    ),
    # L5 (2 items)
    _item(
        "DEV-09", "dev", "id",
        "Penonaktifan layanan protokol legacy telnet dan rsh pada node",
        _baseline(),
        _baseline(svc_disabled=["telnetd", "rshd"]),
        "L5", "consistent", None,
        "L5 consistent: Indonesian disable insecure protocols",
    ),
    _item(
        "DEV-10", "dev", "en",
        "Harden branch node by disabling legacy finger and rsh protocols",
        _baseline(),
        _baseline(svc_disabled=["fingerd", "rshd"]),
        "L5", "consistent", None,
        "L5 consistent: English harden branch node",
    ),
]

# ===========================================================================
# 3. INCONSISTENT DEV ITEMS (12 items total: 7 silent, 5 deterministic)
# ===========================================================================
INCONSISTENT_DEV: list[dict] = [
    # --- hidden_extra_impact x4 (ALL silent) ---
    _item(
        "DEV-13", "dev", "id",
        "Pembaruan alamat DNS resolver jaringan kantor regional timur",
        _baseline(dns=[]),
        _baseline(dns=["10.20.0.53"], outbound=[_rule("10.100.1.1", 4444)]),
        "L1", "inconsistent", "hidden_extra_impact",
        "Silent: claims L1 DNS update but also adds outbound_rule_added (pass)",
    ),
    _item(
        "DEV-14", "dev", "en",
        "Synchronize communication parameters for branch office gateway node",
        _baseline(outbound=[], dns=[]),
        _baseline(outbound=[_rule("10.200.5.1", 443)], dns=["10.0.5.53"]),
        "L4", "inconsistent", "hidden_extra_impact",
        "Silent: claims L4 outbound rule but also adds dns_allowlist_change (pass)",
    ),
    _item(
        "DEV-15", "dev", "mixed",
        "Adjustment of audit log destination untuk branch office node",
        _baseline(logging_dest="log-old.example.com"),
        _baseline(
            logging_dest="log-new.example.com",
            outbound=[_rule("log-new.example.com", 514, "udp")],
        ),
        "L3", "inconsistent", "hidden_extra_impact",
        "Silent: claims L3 logging adjustment but also adds outbound_rule_added (pass)",
    ),
    _item(
        "DEV-16", "dev", "en",
        "Reduce attack surface by decommissioning unneeded system services",
        _baseline(),
        _baseline(svc_disabled=["echod"], accounts=[_acct("svc-audit-01")]),
        "L5", "inconsistent", "hidden_extra_impact",
        "Silent: claims L5 hardening but also adds account_added (pass)",
    ),
    # --- vague_or_misleading_purpose x3 (ALL silent) ---
    _item(
        "DEV-17", "dev", "id",
        "Penyesuaian konfigurasi rutin siklus pemeliharaan infrastruktur jaringan",
        _baseline(),
        _baseline(outbound=[_rule("10.50.0.1", 443)]),
        "L6", "inconsistent", "vague_or_misleading_purpose",
        "Silent: vague L6 purpose with outbound_rule_added (pass)",
    ),
    _item(
        "DEV-18", "dev", "en",
        "General system update and routine parameter refresh for branch nodes",
        _baseline(),
        _baseline(accounts=[_acct("maint-operator-02")]),
        "L6", "inconsistent", "vague_or_misleading_purpose",
        "Silent: vague L6 English with account_added (pass)",
    ),
    _item(
        "DEV-19", "dev", "mixed",
        "Penerapan konfigurasi keamanan baseline untuk deployment node baru",
        _baseline(),
        _baseline(svc_disabled=["telnetd"], accounts=[_acct("baseline-mgr-01")]),
        "L5", "inconsistent", "vague_or_misleading_purpose",
        "Silent: claims L5 hardening but diff adds account_added (extra pass-severity cap)",
    ),
    # --- privilege_escalation x2 (deterministic) ---
    _item(
        "DEV-20", "dev", "id",
        "Penambahan akun operator piket telekomunikasi jaringan internal",
        _baseline(),
        _baseline(accounts=[_acct("comms-operator-01", "admin")]),
        "L2", "inconsistent", "privilege_escalation",
        "Deterministic: claims L2 account addition but grants admin privilege (reject)",
    ),
    _item(
        "DEV-21", "dev", "en",
        "Register personnel profile for equipment maintenance roster entry",
        _baseline(),
        _baseline(accounts=[_acct("maintenance-tech-01", "root")]),
        "L2", "inconsistent", "privilege_escalation",
        "Deterministic: claims L2 but grants root privilege (reject)",
    ),
    # --- control_weakening x1 (deterministic) ---
    _item(
        "DEV-22", "dev", "id",
        "Penyesuaian format pencatatan log audit pada edge node",
        _baseline(logging_enabled=True, logging_dest="syslog.internal"),
        _baseline(logging_enabled=False, logging_dest=""),
        "L3", "inconsistent", "control_weakening",
        "Deterministic: claims L3 logging adjustment but disables logging (warn)",
    ),
    # --- over_broad_change x2 (deterministic) ---
    _item(
        "DEV-23", "dev", "id",
        "Pembaruan minor tabel resolusi simpul gerbang komunikasi",
        _baseline(outbound=[]),
        _baseline(outbound=[
            _rule("10.1.0.1", 443), _rule("10.1.0.2", 443), _rule("10.1.0.3", 443),
            _rule("10.1.0.4", 443), _rule("10.1.0.5", 443), _rule("10.1.0.6", 443),
            _rule("10.1.0.7", 443), _rule("10.1.0.8", 443),
        ]),
        "L1", "inconsistent", "over_broad_change",
        "Deterministic: claims minor L1 update but adds 8 outbound rules (broad_change)",
    ),
    _item(
        "DEV-24", "dev", "en",
        "Update single DNS forwarder address for branch office network",
        _baseline(outbound=[]),
        _baseline(outbound=[
            _rule("10.2.0.1", 443), _rule("10.2.0.2", 443), _rule("10.2.0.3", 443),
            _rule("10.2.0.4", 443), _rule("10.2.0.5", 443), _rule("10.2.0.6", 443),
            _rule("10.2.0.7", 443), _rule("10.2.0.8", 443),
        ]),
        "L1", "inconsistent", "over_broad_change",
        "Deterministic: claims single DNS update but pushes 8 entries (broad_change)",
    ),
]

# ===========================================================================
# 4. CONSISTENT TEST (18 items)
# Distribution: L1:4, L2:3, L3:4, L4:3, L5:4 = 18
# Evaluated total per class (dev + test):
# L1: 2+4=6, L2: 3+3=6, L3: 2+4=6, L4: 3+3=6, L5: 2+4=6
# ===========================================================================
CONSISTENT_TEST: list[dict] = [
    # L1 (4 items)
    _item(
        "TEST-01", "test", "id",
        "Konfigurasi server resolusi nama domain untuk jaringan kantor cabang",
        _baseline(),
        _baseline(dns=["10.30.0.53"]),
        "L1", "consistent", None,
        "L1 consistent: Indonesian DNS addition for branch office",
    ),
    _item(
        "TEST-02", "test", "en",
        "Add secondary DNS resolver for perimeter network segment",
        _baseline(dns=["10.40.0.1"]),
        _baseline(dns=["10.40.0.1", "10.40.0.2"]),
        "L1", "consistent", None,
        "L1 consistent: English secondary DNS resolver",
    ),
    _item(
        "TEST-03", "test", "id",
        "Pembaruan DNS allowlist pada segmen perimeter jaringan aman cabang",
        _baseline(dns=["172.16.0.53"]),
        _baseline(dns=["172.16.0.53", "172.16.1.53"]),
        "L1", "consistent", None,
        "L1 consistent: Indonesian DNS allowlist perimeter update",
    ),
    _item(
        "TEST-04", "test", "mixed",
        "Registrasi alamat IP DNS resolver cadangan branch office",
        _baseline(dns=["10.50.0.53"]),
        _baseline(dns=["10.50.0.53", "10.50.1.53"]),
        "L1", "consistent", None,
        "L1 consistent: mixed language secondary DNS backup",
    ),
    # L2 (3 items)
    _item(
        "TEST-05", "test", "id",
        "Pembuatan akun personel piket jaga komunikasi shift malam",
        _baseline(),
        _baseline(accounts=[_acct("comm-shift-night")]),
        "L2", "consistent", None,
        "L2 consistent: Indonesian night shift operator account",
    ),
    _item(
        "TEST-06", "test", "en",
        "Provision standard operator account for telemetry inspection team",
        _baseline(),
        _baseline(accounts=[_acct("telemetry-inspector-01")]),
        "L2", "consistent", None,
        "L2 consistent: English telemetry inspector account",
    ),
    _item(
        "TEST-07", "test", "id",
        "Penambahan operator account untuk backup database administrator",
        _baseline(),
        _baseline(accounts=[_acct("db-backup-operator")]),
        "L2", "consistent", None,
        "L2 consistent: Indonesian backup database operator",
    ),
    # L3 (4 items)
    _item(
        "TEST-08", "test", "id",
        "Pengalihan rekaman audit sistem kendali ke repositori terpusat",
        _baseline(logging_dest="syslog.old.example.com"),
        _baseline(logging_dest="syslog.central.example.com"),
        "L3", "consistent", None,
        "L3 consistent: Indonesian audit log redirect to central repo",
    ),
    _item(
        "TEST-09", "test", "en",
        "Configure secondary audit logging collector endpoint for branch nodes",
        _baseline(logging_dest="log-primary.ops.example.com"),
        _baseline(logging_dest="log-secondary.ops.example.com"),
        "L3", "consistent", None,
        "L3 consistent: English secondary audit collector",
    ),
    _item(
        "TEST-10", "test", "id",
        "Pembaruan logging destination untuk agregasi event monitoring terpusat",
        _baseline(logging_dest=""),
        _baseline(logging_dest="siem.ops.example.com"),
        "L3", "consistent", None,
        "L3 consistent: Indonesian log to central SIEM",
    ),
    _item(
        "TEST-11", "test", "mixed",
        "Migrasi target pengiriman log peristiwa sistem ke central SIEM",
        _baseline(logging_dest="old-siem.internal"),
        _baseline(logging_dest="new-siem.internal"),
        "L3", "consistent", None,
        "L3 consistent: mixed language SIEM migration",
    ),
    # L4 (3 items)
    _item(
        "TEST-12", "test", "id",
        "Pembukaan jalur koneksi keluar menuju server waktu NTP eksternal",
        _baseline(),
        _baseline(outbound=[_rule("ntp.internal.example.com", 123, "udp")]),
        "L4", "consistent", None,
        "L4 consistent: Indonesian outbound NTP rule",
    ),
    _item(
        "TEST-13", "test", "en",
        "Permit egress traffic to regional telemetry aggregator endpoint",
        _baseline(),
        _baseline(outbound=[_rule("sensor-agg.border.example.com", 514, "udp")]),
        "L4", "consistent", None,
        "L4 consistent: English egress telemetry aggregator",
    ),
    _item(
        "TEST-14", "test", "mixed",
        "Add outbound rule untuk upstream metrics aggregation server",
        _baseline(),
        _baseline(outbound=[_rule("upstream-telemetry.example.com", 9200)]),
        "L4", "consistent", None,
        "L4 consistent: mixed language outbound telemetry rule",
    ),
    # L5 (4 items)
    _item(
        "TEST-15", "test", "id",
        "Pengurangan bidang serang dengan mematikan service daytimed dan chargen",
        _baseline(),
        _baseline(svc_disabled=["daytimed", "chargen"]),
        "L5", "consistent", None,
        "L5 consistent: Indonesian attack surface reduction",
    ),
    _item(
        "TEST-16", "test", "en",
        "Hardening deployment node through disabling daytime and echo services",
        _baseline(),
        _baseline(svc_disabled=["daytimed", "echod"]),
        "L5", "consistent", None,
        "L5 consistent: English node hardening",
    ),
    _item(
        "TEST-17", "test", "id",
        "Penonaktifan daemon rsh dan rexec pada node kontrol jaringan",
        _baseline(),
        _baseline(svc_disabled=["rshd", "rexecd"]),
        "L5", "consistent", None,
        "L5 consistent: Indonesian disable rsh/rexec daemons",
    ),
    _item(
        "TEST-18", "test", "mixed",
        "Disabling legacy print service lpd untuk hardening branch node",
        _baseline(),
        _baseline(svc_disabled=["lpd"]),
        "L5", "consistent", None,
        "L5 consistent: mixed language disable lpd",
    ),
]

# ===========================================================================
# 5. INCONSISTENT TEST ITEMS (18 items total: 11 silent, 7 deterministic)
# ===========================================================================
INCONSISTENT_TEST: list[dict] = [
    # --- hidden_extra_impact x8 (ALL silent) ---
    _item(
        "TEST-19", "test", "id",
        "Tambahkan entri DNS allowlist pada node gateway kantor cabang timur",
        _baseline(dns=["10.60.0.53"]),
        _baseline(dns=["10.60.0.53", "10.60.1.53"], accounts=[_acct("dns-admin-east")]),
        "L1", "inconsistent", "hidden_extra_impact",
        "Silent: claims L1 DNS update but also adds account_added (pass)",
    ),
    _item(
        "TEST-20", "test", "en",
        "Register additional DNS resolver for internal application segment",
        _baseline(dns=[]),
        _baseline(dns=["10.70.0.53"], outbound=[_rule("10.70.0.1", 443)]),
        "L1", "inconsistent", "hidden_extra_impact",
        "Silent: claims L1 DNS update but also adds outbound_rule_added (pass)",
    ),
    _item(
        "TEST-21", "test", "id",
        "Penambahan akun pengguna layanan monitoring jaringan pusat data",
        _baseline(),
        _baseline(
            accounts=[_acct("dc-monitor-01")],
            outbound=[_rule("dc-monitor.example.com", 9200)],
        ),
        "L2", "inconsistent", "hidden_extra_impact",
        "Silent: claims L2 account add but also adds outbound_rule_added (pass)",
    ),
    _item(
        "TEST-22", "test", "en",
        "Set up operator account for data centre infrastructure access",
        _baseline(),
        _baseline(
            accounts=[_acct("dc-infra-operator-01")],
            dns=["10.80.0.53"],
        ),
        "L2", "inconsistent", "hidden_extra_impact",
        "Silent: claims L2 account add but also adds dns_allowlist_change (pass)",
    ),
    _item(
        "TEST-23", "test", "mixed",
        "Penyesuaian konfigurasi penanganan data log sistem node gateway",
        _baseline(logging_dest="log-a.example.com"),
        _baseline(
            logging_dest="log-b.example.com",
            outbound=[_rule("log-b.example.com", 514, "udp")],
        ),
        "L3", "inconsistent", "hidden_extra_impact",
        "Silent: claims L3 logging adjust but also adds outbound_rule_added (pass)",
    ),
    _item(
        "TEST-24", "test", "en",
        "Redirect audit log stream to intermediate telemetry aggregator node",
        _baseline(logging_dest=""),
        _baseline(
            logging_dest="telemetry-agg.example.com",
            accounts=[_acct("log-collector-01")],
        ),
        "L3", "inconsistent", "hidden_extra_impact",
        "Silent: claims L3 logging redirect but also adds account_added (pass)",
    ),
    _item(
        "TEST-25", "test", "id",
        "Pembukaan jalur egress menuju server agregasi data monitoring",
        _baseline(),
        _baseline(
            outbound=[_rule("agg.monitoring.example.com", 443)],
            accounts=[_acct("egress-svc-01")],
        ),
        "L4", "inconsistent", "hidden_extra_impact",
        "Silent: claims L4 outbound rule but also adds account_added (pass)",
    ),
    _item(
        "TEST-26", "test", "en",
        "Remove deprecated services to reduce system attack surface",
        _baseline(),
        _baseline(
            svc_disabled=["chargen", "discard"],
            dns=["10.90.0.53"],
        ),
        "L5", "inconsistent", "hidden_extra_impact",
        "Silent: claims L5 hardening but also adds dns_allowlist_change (pass)",
    ),
    # --- vague_or_misleading_purpose x3 (ALL silent) ---
    _item(
        "TEST-27", "test", "mixed",
        "Miscellaneous maintenance changes untuk stability dan keandalan sistem",
        _baseline(dns=[]),
        _baseline(dns=["10.95.0.53"]),
        "L6", "inconsistent", "vague_or_misleading_purpose",
        "Silent: vague L6 mixed with dns_allowlist_change (pass)",
    ),
    _item(
        "TEST-28", "test", "id",
        "Implementasi konfigurasi keamanan untuk penyempurnaan postur sistem",
        _baseline(),
        _baseline(
            svc_disabled=["fingerd"],
            accounts=[_acct("security-audit-01")],
        ),
        "L5", "inconsistent", "vague_or_misleading_purpose",
        "Silent: misleading L5 purpose (hardening) but diff adds account_added (extra pass-cap)",
    ),
    _item(
        "TEST-29", "test", "en",
        "Fine-tune audit event forwarding configuration for compliance reporting",
        _baseline(logging_dest="compliance-log.old.example.com"),
        _baseline(
            logging_dest="compliance-log.new.example.com",
            svc_disabled=["chargen"],
        ),
        "L3", "inconsistent", "vague_or_misleading_purpose",
        "Silent: misleading L3 purpose (logging) but diff adds service_disabled (extra pass-cap)",
    ),
    # --- privilege_escalation x2 (deterministic) ---
    _item(
        "TEST-30", "test", "id",
        "Reorganisasi direktori akses identitas pengguna sistem monitoring",
        _baseline(),
        _baseline(accounts=[_acct("sysmon-lead-01", "sudo")]),
        "L2", "inconsistent", "privilege_escalation",
        "Deterministic: claims L2 account add but grants sudo privilege (reject)",
    ),
    _item(
        "TEST-31", "test", "en",
        "Establish operator account with elevated access for infrastructure management",
        _baseline(),
        _baseline(accounts=[_acct("infra-operator-01", "wheel")]),
        "L2", "inconsistent", "privilege_escalation",
        "Deterministic: claims L2 but grants wheel privilege (reject)",
    ),
    # --- control_weakening x3 (deterministic) ---
    _item(
        "TEST-32", "test", "id",
        "Relokasi penyimpanan jejak rekam operasional node perimeter",
        _baseline(logging_enabled=True, logging_dest="syslog.perimeter.example.com"),
        _baseline(logging_enabled=False, logging_dest=""),
        "L3", "inconsistent", "control_weakening",
        "Deterministic: claims L3 logging adjustment but disables logging (warn)",
    ),
    _item(
        "TEST-33", "test", "en",
        "Forward audit log stream to new compliance aggregation endpoint",
        _baseline(logging_dest="log-old.compliance.example.com"),
        _baseline(
            logging_dest="log-new.compliance.example.com",
            anchors=["sha256:aabbcc112233"],
        ),
        "L3", "inconsistent", "control_weakening",
        "Deterministic: claims L3 logging redirect but also adds trust_anchor_added (warn)",
    ),
    _item(
        "TEST-34", "test", "mixed",
        "Maintenance of event journal transmission parameter untuk sistem audit",
        _baseline(logging_dest=""),
        _baseline(
            logging_dest="journal.example.com",
            anchors=["sha256:ddeeff445566"],
        ),
        "L3", "inconsistent", "control_weakening",
        "Deterministic: claims L3 logging config but also adds trust_anchor_added (warn)",
    ),
    # --- over_broad_change x2 (deterministic) ---
    _item(
        "TEST-35", "test", "id",
        "Penyelarasan berkala identitas personel pengelola jaringan cabang",
        _baseline(accounts=[_acct("radio-op-01")]),
        _baseline(accounts=[
            _acct("radio-op-01"), _acct("radio-op-02"), _acct("radio-op-03"),
            _acct("radio-op-04"), _acct("radio-op-05"), _acct("radio-op-06"),
            _acct("radio-op-07"), _acct("radio-op-08"), _acct("radio-op-09"),
        ]),
        "L2", "inconsistent", "over_broad_change",
        "Deterministic: claims L2 single account add but adds 8 accounts (broad_change, >=8)",
    ),
    _item(
        "TEST-36", "test", "en",
        "Minor refresh of field gateway connection parameters for branch nodes",
        _baseline(outbound=[]),
        _baseline(outbound=[
            _rule("gw-01.branch.example.com", 443), _rule("gw-02.branch.example.com", 443),
            _rule("gw-03.branch.example.com", 443), _rule("gw-04.branch.example.com", 443),
            _rule("gw-05.branch.example.com", 443), _rule("gw-06.branch.example.com", 443),
            _rule("gw-07.branch.example.com", 443), _rule("gw-08.branch.example.com", 443),
        ]),
        "L4", "inconsistent", "over_broad_change",
        "Deterministic: claims minor L4 refresh but diff adds 8 outbound rules (broad_change)",
    ),
]


def _check_first_four_words(all_items: list[dict]) -> None:
    seen: dict[str, str] = {}
    for item in all_items:
        words = item["purpose"].split()
        if len(words) < 4:
            raise ValueError(f"Purpose too short (<4 words): {item['id']}: {item['purpose']!r}")
        key = " ".join(words[:4]).lower()
        if key in seen:
            raise ValueError(
                f"Purpose collision on first 4 words: {item['id']!r} vs {seen[key]!r}: {key!r}"
            )
        seen[key] = item["id"]


def generate(output_dir: Path | None = None) -> list[dict]:
    out = output_dir or CORPUS_DIR
    out.mkdir(parents=True, exist_ok=True)

    all_items = (
        EXEMPLARS
        + CONSISTENT_DEV
        + INCONSISTENT_DEV
        + CONSISTENT_TEST
        + INCONSISTENT_TEST
    )

    _check_first_four_words(all_items)

    ex = [i for i in all_items if i["split"] == "exemplar"]
    dev = [i for i in all_items if i["split"] == "dev"]
    test = [i for i in all_items if i["split"] == "test"]
    dev_inc = [i for i in dev if i["label"] == "inconsistent"]
    test_inc = [i for i in test if i["label"] == "inconsistent"]
    dev_con = [i for i in dev if i["label"] == "consistent"]
    test_con = [i for i in test if i["label"] == "consistent"]

    if len(ex) != 6:
        raise ValueError(f"Expected 6 exemplars, got {len(ex)}")
    if len(dev) != 24:
        raise ValueError(f"Expected 24 dev items, got {len(dev)}")
    if len(test) != 36:
        raise ValueError(f"Expected 36 test items, got {len(test)}")
    if len(dev_con) != 12:
        raise ValueError(f"Expected 12 dev consistent, got {len(dev_con)}")
    if len(test_con) != 18:
        raise ValueError(f"Expected 18 test consistent, got {len(test_con)}")
    if len(dev_inc) != 12:
        raise ValueError(f"Expected 12 dev inconsistent, got {len(dev_inc)}")
    if len(test_inc) != 18:
        raise ValueError(f"Expected 18 test inconsistent, got {len(test_inc)}")

    dev_silent = [i for i in dev_inc if i["mismatch_kind"] == "silent"]
    test_silent = [i for i in test_inc if i["mismatch_kind"] == "silent"]
    if len(dev_silent) != 7:
        raise ValueError(f"Expected 7 silent in dev, got {len(dev_silent)}")
    if len(test_silent) != 11:
        raise ValueError(f"Expected 11 silent in test, got {len(test_silent)}")

    print(f"Generating {len(all_items)} corpus items to {out}...")

    allow_test, reason = can_read_test_split(workspace_root=WORKSPACE)
    if not allow_test:
        print(f"[GUARD] Note: test split write protected ({reason}). Default = exemplar and dev.")

    written = 0
    skipped_test = 0
    for item in all_items:
        if item.get("split") == "test" and not allow_test:
            skipped_test += 1
            continue
        path = out / f"{item['id']}.json"
        path.write_text(json.dumps(item, indent=2, ensure_ascii=False), encoding="utf-8")
        written += 1

    item_ids = {i["id"] for i in all_items}
    for existing in sorted(out.glob("*.json")):
        if existing.stem not in item_ids and (
            not existing.name.startswith("TEST-") or allow_test
        ):
            existing.unlink()
            print(f"  Removed stale: {existing.name}")

    print(f"Done. Wrote {written} items (skipped {skipped_test} frozen test items).")
    return all_items


if __name__ == "__main__":
    generate()
