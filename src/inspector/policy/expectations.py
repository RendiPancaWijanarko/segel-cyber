# SPDX-License-Identifier: MIT
"""Expectations and B1 keyword classifier for release purpose inspection.

Per docs/ai_decisions.md (D6, D15, D17):
- EXPECTATION_MAP maps purpose classes L1..L6 to expected capabilities.
- derive_findings(purpose_class, capabilities) produces deterministic findings:
  warn for each capability outside the class's expected set;
  L6 plus any capability gives one warn "purpose too vague to verify".
- classify_purpose_b1(purpose) performs keyword matching across L1..L5:
  abstains (returns None) on no match or multi-class match;
  never returns L6.
"""

from __future__ import annotations

import re
from typing import Any

from segel_core.schemas.attestation import InspectFinding

EXPECTATION_MAP: dict[str, set[str]] = {
    "L1": {"dns_allowlist_change"},
    "L2": {"account_added"},
    "L3": {"logging_changed"},
    "L4": {"outbound_rule_added"},
    "L5": {"service_disabled"},
    "L6": set(),
}

# Generic B1 keyword vocabulary per docs/b1_keywords.md
B1_KEYWORDS: dict[str, list[str]] = {
    "L1": [
        # English
        r"dns",
        r"nameserver[s]?",
        r"name\s+server[s]?",
        r"resolver[s]?",
        r"forwarder[s]?",
        r"domain\s+resolution",
        r"name\s+resolution",
        r"dns\s+allowlist",
        r"dns\s+whitelist",
        r"dns\s+lookup",
        r"domain\s+lookup",
        r"recursive\s+dns",
        r"caching\s+dns",
        r"coredns",
        r"bind",
        r"unbound",
        r"dns\s+record[s]?",
        # Indonesian
        r"server\s+dns",
        r"server\s+nama",
        r"resolusi\s+nama",
        r"resolusi\s+domain",
        r"penerjemah\s+nama",
        r"pengurai\s+nama",
        r"pengarah\s+dns",
        r"daftar\s+izin\s+dns",
        r"kueri\s+domain",
        r"pencarian\s+domain",
        r"alamat\s+dns",
        r"domain\s+resolusi",
    ],
    "L2": [
        # English
        r"account[s]?",
        r"user[s]?",
        r"username[s]?",
        r"operator[s]?",
        r"technician[s]?",
        r"personnel",
        r"profile[s]?",
        r"roster",
        r"identit(?:y|ies)",
        r"credentials",
        r"provision(?:ing)?",
        r"onboard(?:ing)?",
        r"user\s+account",
        r"operator\s+account",
        r"maintenance\s+account",
        r"service\s+account",
        r"login\s+profile",
        # Indonesian
        r"akun(?:-akun)?",
        r"pengguna",
        r"teknisi",
        r"personel",
        r"profil",
        r"identitas",
        r"kredensial",
        r"petugas",
        r"staf",
        r"pembuatan\s+akun",
        r"penambahan\s+akun",
        r"registrasi\s+akun",
        r"pendaftaran\s+user",
        r"identitas\s+personel",
        r"daftar\s+pengguna",
    ],
    "L3": [
        # English
        r"log[s]?",
        r"logging",
        r"syslog[s]?",
        r"audit",
        r"audit\s+log[s]?",
        r"audit\s+trail",
        r"audit\s+stream",
        r"journal",
        r"event\s+log[s]?",
        r"telemetry",
        r"siem",
        r"collector",
        r"log\s+collector",
        r"log\s+forwarder",
        r"logging\s+destination",
        r"log\s+target",
        r"event\s+forwarding",
        r"event\s+transmission",
        r"audit\s+repository",
        r"event\s+aggregation",
        # Indonesian
        r"catatan\s+audit",
        r"jejak\s+audit",
        r"rekam\s+jejak",
        r"rekaman\s+audit",
        r"berkas\s+log",
        r"pengiriman\s+log",
        r"tujuan\s+log",
        r"server\s+log",
        r"repositori\s+log",
        r"pencatatan\s+log",
        r"peristiwa\s+sistem",
        r"jurnal\s+sistem",
        r"agregasi\s+log",
        r"kolektor\s+log",
        r"penanganan\s+data\s+log",
    ],
    "L4": [
        # English
        r"firewall[s]?",
        r"outbound",
        r"egress",
        r"network\s+rule[s]?",
        r"firewall\s+rule[s]?",
        r"port[s]?",
        r"traffic",
        r"permit\s+traffic",
        r"egress\s+traffic",
        r"route",
        r"routing",
        r"uplink",
        r"connection",
        r"egress\s+rule",
        r"outbound\s+rule",
        r"network\s+allowlist",
        r"egress\s+allowlist",
        r"packet\s+filter",
        r"upstream\s+connection",
        # Indonesian
        r"dinding\s+api",
        r"aturan\s+firewall",
        r"filter\s+paket",
        r"aturan\s+jaringan",
        r"jalur\s+koneksi",
        r"pembukaan\s+port",
        r"lalu\s+lintas",
        r"transmisi\s+data",
        r"koneksi\s+keluar",
        r"rute\s+keluar",
        r"izin\s+keluar",
        r"allowlist\s+jaringan",
        r"firewall\s+keluar",
        r"aturan\s+keluar",
    ],
    "L5": [
        # English
        r"harden(?:ing)?",
        r"disabl(?:e|ing|ed)",
        r"service[s]?",
        r"daemon[s]?",
        r"attack\s+surface",
        r"decommission(?:ing)?",
        r"legacy\s+service",
        r"unused\s+service",
        r"shutdown\s+service",
        r"turn\s+off\s+service",
        r"exposure\s+reduction",
        r"system\s+posture",
        # Indonesian
        r"pengerasan",
        r"mematikan",
        r"menonaktifkan",
        r"nonaktifkan",
        r"penonaktifan",
        r"matikan",
        r"layanan",
        r"protokol\s+legacy",
        r"protokol\s+tidak\s+aman",
        r"bidang\s+serang",
        r"pengurangan\s+bidang\s+serang",
        r"dekomisi",
        r"penghentian\s+layanan",
        r"keamanan\s+baseline",
    ],
}

_COMPILED_PATTERNS: dict[str, list[re.Pattern[str]]] = {
    cls_name: [re.compile(rf"\b(?:{pat})\b", re.IGNORECASE) for pat in patterns]
    for cls_name, patterns in B1_KEYWORDS.items()
}


def classify_purpose_b1(purpose: str | None) -> str | None:
    """Classify release purpose using the B1 keyword taxonomy.

    Returns:
        Canonical class string ("L1".."L5") if exactly one class matches.
        None if zero classes match or if keywords from multiple classes match
        (abstains on ambiguity or unknown purpose). Never returns "L6".
    """
    if not purpose or not isinstance(purpose, str):
        return None

    cleaned_text = purpose.strip()
    if not cleaned_text:
        return None

    matched_classes: list[str] = []
    for cls_name, patterns in _COMPILED_PATTERNS.items():
        if any(pat.search(cleaned_text) for pat in patterns):
            matched_classes.append(cls_name)

    if len(matched_classes) == 1:
        return matched_classes[0]

    # Zero matches or multi-class match -> abstain
    return None


def derive_findings(
    purpose_class: str | None,
    capabilities: list[dict[str, Any]] | set[str] | list[str],
) -> list[InspectFinding]:
    """Derive deterministic expectation check findings.

    Args:
        purpose_class: Classified purpose class (L1..L6) or None (abstain).
        capabilities: Observed capabilities (list of dicts or set/list of kind strings).

    Returns:
        List of InspectFinding:
        - If purpose_class is None: [] (abstains).
        - If purpose_class == "L6" and capabilities are non-empty:
          one InspectFinding(severity="warn", description="purpose too vague to verify").
        - For L1..L5: one InspectFinding(severity="warn") for each unique capability
          kind outside the expected set.
    """
    if purpose_class is None:
        return []

    # Extract distinct capability IDs
    cap_ids: set[str] = set()
    for c in capabilities:
        if isinstance(c, dict):
            cid = c.get("capability_id")
            if cid:
                cap_ids.add(str(cid))
        elif isinstance(c, str):
            cap_ids.add(c)

    # Class L6: vague or other
    if purpose_class == "L6":
        if cap_ids:
            return [
                InspectFinding(
                    capability_id="L6",
                    severity="warn",
                    source="deterministic",
                    description="purpose too vague to verify",
                )
            ]
        return []

    # Classes L1..L5
    allowed = EXPECTATION_MAP.get(purpose_class, set())
    unexpected = sorted(cap_ids - allowed)

    findings: list[InspectFinding] = []
    for uid in unexpected:
        findings.append(
            InspectFinding(
                capability_id=uid,
                severity="warn",
                source="deterministic",
                description=(
                    f"Unexpected capability '{uid}' outside expectation map for "
                    f"purpose class '{purpose_class}'"
                ),
            )
        )

    return findings
