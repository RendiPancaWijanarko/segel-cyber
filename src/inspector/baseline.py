# SPDX-License-Identifier: MIT
"""Baseline v1 schema definition, duplicate-key JSON parser, and structured capability extractor.

Per PRD v2.0 §7.5, TAS §8.4, and docs/ai_decisions.md (D2, D3, D17):
- Baseline v1 JSON configuration format parsed with stdlib json.
- Object pairs hook rejecting duplicate keys at any nesting level.
- Pydantic models with extra="forbid" on all structures.
- Structured capability extraction with stable <kind>#<n> instance IDs.
- Predecessor diffing identifying new, changed, and removed entries.
- Broad change detection triggering when >= 8 differences exist.
"""

from __future__ import annotations

import json
from collections import defaultdict
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, ValidationError

# ── Baseline v1 Pydantic Models ──────────────────────────────────────


class OutboundRule(BaseModel):
    """Allowed outbound firewall destination."""

    model_config = ConfigDict(extra="forbid")

    destination: str
    port: int | str
    proto: str = "tcp"


class FirewallConfig(BaseModel):
    """Firewall configuration section."""

    model_config = ConfigDict(extra="forbid")

    outbound_allowed: list[OutboundRule] = Field(default_factory=list)


class ServicesConfig(BaseModel):
    """Services configuration section."""

    model_config = ConfigDict(extra="forbid")

    enabled: list[str] = Field(default_factory=list)
    disabled: list[str] = Field(default_factory=list)


class AccountEntry(BaseModel):
    """User/operator account declaration."""

    model_config = ConfigDict(extra="forbid")

    name: str
    privilege: str


class LoggingConfig(BaseModel):
    """System and audit logging configuration."""

    model_config = ConfigDict(extra="forbid")

    enabled: bool = True
    destination: str = ""


class BaselineV1(BaseModel):
    """Baseline v1 configuration document."""

    model_config = ConfigDict(extra="forbid")

    schema_version: str | None = Field(default=None)
    firewall: FirewallConfig = Field(default_factory=FirewallConfig)
    dns_allowlist: list[str] = Field(default_factory=list)
    services: ServicesConfig = Field(default_factory=ServicesConfig)
    accounts: list[AccountEntry] = Field(default_factory=list)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    scheduled_tasks: list[str] = Field(default_factory=list)
    trust_anchors: list[str] = Field(default_factory=list)


# ── Strict JSON Parsing with Duplicate Key Rejection ─────────────────


def reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    """Object pairs hook for json.loads that raises ValueError on duplicate keys."""
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"Duplicate key detected in JSON: {key!r}")
        result[key] = value
    return result


def parse_baseline_v1(raw: str | bytes) -> BaselineV1:
    """Parse raw bytes or string into BaselineV1, rejecting duplicate keys and extra fields."""
    raw_text = raw.decode("utf-8") if isinstance(raw, bytes) else raw

    data = json.loads(raw_text, object_pairs_hook=reject_duplicate_keys)
    if not isinstance(data, dict):
        raise ValueError("Baseline v1 document must be a JSON object")
    return BaselineV1.model_validate(data)


# ── Predecessor Diffing ───────────────────────────────────────────────

ELEVATED_PRIVILEGES = {"admin", "root", "wheel", "sudo", "privileged"}


def _to_baseline(val: list[dict[str, Any]] | BaselineV1 | dict[str, Any]) -> BaselineV1:
    """Normalize input into BaselineV1."""
    if isinstance(val, BaselineV1):
        return val
    if isinstance(val, dict):
        return BaselineV1.model_validate(val)
    if isinstance(val, list):
        # Reconstruct synthetic baseline from capability list
        dns: list[str] = []
        rules: list[OutboundRule] = []
        serv_en: list[str] = []
        serv_dis: list[str] = []
        accs: list[AccountEntry] = []
        tasks: list[str] = []
        anchors: list[str] = []
        log_enabled = True
        log_dest = ""

        for c in val:
            cid = c.get("capability_id", "")
            if cid == "dns_allowlist_change" and c.get("destination"):
                dns.append(c["destination"])
            elif cid == "outbound_rule_added" and c.get("destination"):
                rules.append(
                    OutboundRule(
                        destination=c["destination"],
                        port=c.get("port", 0),
                        proto=c.get("proto", "tcp"),
                    )
                )
            elif cid == "service_enabled" and c.get("value"):
                serv_en.append(c["value"])
            elif cid == "service_disabled" and c.get("value"):
                serv_dis.append(c["value"])
            elif cid == "account_added" and c.get("account"):
                accs.append(AccountEntry(name=c["account"], privilege=c.get("value", "user")))
            elif cid == "logging_disabled":
                log_enabled = False
            elif cid == "logging_changed" and c.get("destination"):
                log_dest = c["destination"]
            elif cid == "scheduled_task_added" and c.get("value"):
                tasks.append(c["value"])
            elif cid == "trust_anchor_added" and c.get("value"):
                anchors.append(c["value"])

        return BaselineV1(
            dns_allowlist=dns,
            firewall=FirewallConfig(outbound_allowed=rules),
            services=ServicesConfig(enabled=serv_en, disabled=serv_dis),
            accounts=accs,
            logging=LoggingConfig(enabled=log_enabled, destination=log_dest),
            scheduled_tasks=tasks,
            trust_anchors=anchors,
        )
    raise TypeError(f"Cannot convert {type(val)} to BaselineV1")


def diff_capabilities(
    previous: list[dict[str, Any]] | BaselineV1 | dict[str, Any],
    current: list[dict[str, Any]] | BaselineV1 | dict[str, Any],
) -> dict[str, list[dict[str, Any]]]:
    """Diff predecessor and current configuration to determine new, changed, and removed entries."""
    p = _to_baseline(previous)
    c = _to_baseline(current)

    new_items: list[dict[str, Any]] = []
    changed_items: list[dict[str, Any]] = []
    removed_items: list[dict[str, Any]] = []

    # 1. DNS allowlist
    prev_dns = set(p.dns_allowlist)
    curr_dns = set(c.dns_allowlist)
    for d in curr_dns - prev_dns:
        new_items.append({"setting": "dns_allowlist", "destination": d, "value": d})
    for d in prev_dns - curr_dns:
        removed_items.append({"setting": "dns_allowlist", "destination": d, "value": d})

    # 2. Firewall outbound rules
    prev_rules = {(r.destination, str(r.port), r.proto): r for r in p.firewall.outbound_allowed}
    curr_rules = {(r.destination, str(r.port), r.proto): r for r in c.firewall.outbound_allowed}
    for k, r in curr_rules.items():
        if k not in prev_rules:
            new_items.append({
                "setting": "outbound_allowed",
                "destination": r.destination,
                "port": r.port,
                "proto": r.proto,
                "value": f"{r.destination}:{r.port}/{r.proto}",
            })
    for k, r in prev_rules.items():
        if k not in curr_rules:
            removed_items.append({
                "setting": "outbound_allowed",
                "destination": r.destination,
                "port": r.port,
                "proto": r.proto,
                "value": f"{r.destination}:{r.port}/{r.proto}",
            })

    # 3. Services
    prev_en = set(p.services.enabled)
    curr_en = set(c.services.enabled)
    prev_dis = set(p.services.disabled)
    curr_dis = set(c.services.disabled)

    for s in curr_en - prev_en:
        if s in prev_dis:
            changed_items.append({
                "setting": "service",
                "value": s,
                "old_value": "disabled",
                "new_value": "enabled",
            })
        else:
            new_items.append({"setting": "service", "value": s, "state": "enabled"})
    for s in prev_en - curr_en:
        if s not in curr_dis:
            removed_items.append({"setting": "service", "value": s, "state": "enabled"})

    for s in curr_dis - prev_dis:
        if s not in prev_en:  # already counted in changed above if it was in prev_en
            new_items.append({"setting": "service", "value": s, "state": "disabled"})
    for s in prev_dis - curr_dis:
        if s not in curr_en:
            removed_items.append({"setting": "service", "value": s, "state": "disabled"})

    # 4. Accounts
    prev_acc = {a.name: a.privilege for a in p.accounts}
    curr_acc = {a.name: a.privilege for a in c.accounts}
    for name, priv in curr_acc.items():
        if name not in prev_acc:
            new_items.append({"setting": "account", "account": name, "value": priv})
        elif prev_acc[name] != priv:
            changed_items.append({
                "setting": "account",
                "account": name,
                "old_value": prev_acc[name],
                "new_value": priv,
                "value": priv,
            })
    for name, priv in prev_acc.items():
        if name not in curr_acc:
            removed_items.append({"setting": "account", "account": name, "value": priv})

    # 5. Logging
    if p.logging.enabled != c.logging.enabled:
        changed_items.append({
            "setting": "logging.enabled",
            "old_value": str(p.logging.enabled),
            "new_value": str(c.logging.enabled),
            "value": str(c.logging.enabled),
        })
    if p.logging.destination != c.logging.destination:
        if not p.logging.destination and c.logging.destination:
            new_items.append({
                "setting": "logging.destination",
                "destination": c.logging.destination,
                "value": c.logging.destination,
            })
        elif p.logging.destination and not c.logging.destination:
            removed_items.append({
                "setting": "logging.destination",
                "destination": p.logging.destination,
                "value": p.logging.destination,
            })
        else:
            changed_items.append({
                "setting": "logging.destination",
                "destination": c.logging.destination,
                "old_value": p.logging.destination,
                "new_value": c.logging.destination,
                "value": c.logging.destination,
            })

    # 6. Scheduled tasks
    prev_tasks = set(p.scheduled_tasks)
    curr_tasks = set(c.scheduled_tasks)
    for t in curr_tasks - prev_tasks:
        new_items.append({"setting": "scheduled_task", "value": t})
    for t in prev_tasks - curr_tasks:
        removed_items.append({"setting": "scheduled_task", "value": t})

    # 7. Trust anchors
    prev_anchors = set(p.trust_anchors)
    curr_anchors = set(c.trust_anchors)
    for a in curr_anchors - prev_anchors:
        new_items.append({"setting": "trust_anchor", "value": a})
    for a in prev_anchors - curr_anchors:
        removed_items.append({"setting": "trust_anchor", "value": a})

    return {"new": new_items, "changed": changed_items, "removed": removed_items}


# ── Structured Capability Extraction ─────────────────────────────────


def extract_capabilities_structured(
    files: dict[str, bytes],
    predecessor_files: dict[str, bytes] | None = None,
) -> list[dict[str, Any]]:
    """Extract capabilities from Baseline v1 JSON configuration files."""
    detected: list[dict[str, Any]] = []
    kind_counts: dict[str, int] = defaultdict(int)

    for path, content in sorted(files.items()):
        try:
            baseline = parse_baseline_v1(content)
        except (ValueError, json.JSONDecodeError, ValidationError):
            continue

        # 1. Firewall rules
        for rule in baseline.firewall.outbound_allowed:
            kind_counts["outbound_rule_added"] += 1
            detected.append({
                "capability_id": "outbound_rule_added",
                "instance_id": f"outbound_rule_added#{kind_counts['outbound_rule_added']}",
                "file": path,
                "line": 1,
                "destination": rule.destination,
                "port": rule.port,
                "proto": rule.proto,
                "account": None,
                "setting": "outbound_allowed",
                "value": f"{rule.destination}:{rule.port}/{rule.proto}",
                "description": (
                    f"Outbound firewall rule allowed to "
                    f"{rule.destination}:{rule.port}/{rule.proto}"
                ),
            })

        # 2. DNS allowlist
        for dns_dest in baseline.dns_allowlist:
            kind_counts["dns_allowlist_change"] += 1
            detected.append({
                "capability_id": "dns_allowlist_change",
                "instance_id": f"dns_allowlist_change#{kind_counts['dns_allowlist_change']}",
                "file": path,
                "line": 1,
                "destination": dns_dest,
                "port": None,
                "proto": None,
                "account": None,
                "setting": "dns_allowlist",
                "value": dns_dest,
                "description": f"DNS allowlist allows {dns_dest}",
            })

        # 3. Services enabled
        for s in baseline.services.enabled:
            kind_counts["service_enabled"] += 1
            detected.append({
                "capability_id": "service_enabled",
                "instance_id": f"service_enabled#{kind_counts['service_enabled']}",
                "file": path,
                "line": 1,
                "destination": None,
                "port": None,
                "proto": None,
                "account": None,
                "setting": "service",
                "value": s,
                "description": f"Service enabled: {s}",
            })

        # 4. Services disabled
        for s in baseline.services.disabled:
            kind_counts["service_disabled"] += 1
            detected.append({
                "capability_id": "service_disabled",
                "instance_id": f"service_disabled#{kind_counts['service_disabled']}",
                "file": path,
                "line": 1,
                "destination": None,
                "port": None,
                "proto": None,
                "account": None,
                "setting": "service",
                "value": s,
                "description": f"Service disabled: {s}",
            })

        # 5. Accounts
        for acc in baseline.accounts:
            kind_counts["account_added"] += 1
            detected.append({
                "capability_id": "account_added",
                "instance_id": f"account_added#{kind_counts['account_added']}",
                "file": path,
                "line": 1,
                "destination": None,
                "port": None,
                "proto": None,
                "account": acc.name,
                "setting": "account",
                "value": acc.privilege,
                "description": f"Account declared: {acc.name} with privilege {acc.privilege}",
            })
            if acc.privilege.lower() in ELEVATED_PRIVILEGES:
                kind_counts["privilege_granted"] += 1
                detected.append({
                    "capability_id": "privilege_granted",
                    "instance_id": f"privilege_granted#{kind_counts['privilege_granted']}",
                    "file": path,
                    "line": 1,
                    "destination": None,
                    "port": None,
                    "proto": None,
                    "account": acc.name,
                    "setting": "privilege",
                    "value": acc.privilege,
                    "description": (
                        f"Elevated privilege granted to account: "
                        f"{acc.name} ({acc.privilege})"
                    ),
                })

        # 6. Logging
        if not baseline.logging.enabled:
            kind_counts["logging_disabled"] += 1
            detected.append({
                "capability_id": "logging_disabled",
                "instance_id": f"logging_disabled#{kind_counts['logging_disabled']}",
                "file": path,
                "line": 1,
                "destination": baseline.logging.destination or None,
                "port": None,
                "proto": None,
                "account": None,
                "setting": "enabled",
                "value": "false",
                "description": "Logging is disabled",
            })
        elif baseline.logging.destination:
            kind_counts["logging_changed"] += 1
            detected.append({
                "capability_id": "logging_changed",
                "instance_id": f"logging_changed#{kind_counts['logging_changed']}",
                "file": path,
                "line": 1,
                "destination": baseline.logging.destination,
                "port": None,
                "proto": None,
                "account": None,
                "setting": "destination",
                "value": baseline.logging.destination,
                "description": f"Logging destination configured: {baseline.logging.destination}",
            })

        # 7. Scheduled tasks
        for task in baseline.scheduled_tasks:
            kind_counts["scheduled_task_added"] += 1
            detected.append({
                "capability_id": "scheduled_task_added",
                "instance_id": f"scheduled_task_added#{kind_counts['scheduled_task_added']}",
                "file": path,
                "line": 1,
                "destination": None,
                "port": None,
                "proto": None,
                "account": None,
                "setting": "scheduled_task",
                "value": task,
                "description": f"Scheduled task configured: {task}",
            })

        # 8. Trust anchors
        for anchor in baseline.trust_anchors:
            kind_counts["trust_anchor_added"] += 1
            detected.append({
                "capability_id": "trust_anchor_added",
                "instance_id": f"trust_anchor_added#{kind_counts['trust_anchor_added']}",
                "file": path,
                "line": 1,
                "destination": None,
                "port": None,
                "proto": None,
                "account": None,
                "setting": "trust_anchor",
                "value": anchor,
                "description": f"Trust anchor added: {anchor}",
            })

    # Predecessor diffing & broad_change evaluation
    if predecessor_files:
        prev_caps = extract_capabilities_structured(predecessor_files)
        diff = diff_capabilities(prev_caps, detected)
        diff_count = len(diff["new"]) + len(diff["changed"]) + len(diff["removed"])
        if diff_count >= 8:
            kind_counts["broad_change"] += 1
            first_file = sorted(files.keys())[0] if files else "baseline.json"
            detected.append({
                "capability_id": "broad_change",
                "instance_id": f"broad_change#{kind_counts['broad_change']}",
                "file": first_file,
                "line": 1,
                "destination": None,
                "port": None,
                "proto": None,
                "account": None,
                "setting": "diff_count",
                "value": str(diff_count),
                "description": (
                    f"Broad change detected: {diff_count} entries differ from predecessor"
                ),
            })

    return detected
