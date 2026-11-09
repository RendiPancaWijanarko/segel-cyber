# SPDX-License-Identifier: MIT
"""Corpus verification script for SEGEL AI Purpose and Expectation Corpus.

Per docs/ai_decisions.md (D9, D9b, D14, D15, D17):
- Recomputes ground-truth labels from structured baseline diff against expectation map.
- Validates Baseline v1 schema conformance and rejects unknown keys (extra=forbid).
- Verifies exact stratification (6 exemplars, 30 consistent, 30 inconsistent; 24 dev / 36 test).
- Computes and verifies mismatch_kind per item (never hand-written).
- Exits with status 0 on full verification, or non-zero on any defect.

Keyword evasion is measured in AI-4 against the independently written docs/b1_keywords.md.
"""

from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path
from typing import Any

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(WORKSPACE_ROOT / "src"))

from inspector.baseline import BaselineV1, diff_capabilities  # noqa: E402

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


def compute_diff_capabilities(prev: BaselineV1, curr: BaselineV1) -> set[str]:
    """Compute observable capability kinds from candidate baseline relative to previous."""
    diff_kinds: set[str] = set()

    prev_dns = set(prev.dns_allowlist)
    curr_dns = set(curr.dns_allowlist)
    if curr_dns - prev_dns:
        diff_kinds.add("dns_allowlist_change")

    prev_rules = {(r.destination, str(r.port), r.proto) for r in prev.firewall.outbound_allowed}
    curr_rules = {(r.destination, str(r.port), r.proto) for r in curr.firewall.outbound_allowed}
    if curr_rules - prev_rules:
        diff_kinds.add("outbound_rule_added")

    prev_acc = {a.name: a.privilege for a in prev.accounts}
    curr_acc = {a.name: a.privilege for a in curr.accounts}
    for name, priv in curr_acc.items():
        if name not in prev_acc:
            diff_kinds.add("account_added")
        if priv.lower() in {"admin", "root", "wheel", "sudo", "privileged"} and (
            name not in prev_acc
            or prev_acc[name].lower() not in {"admin", "root", "wheel", "sudo", "privileged"}
        ):
            diff_kinds.add("privilege_granted")

    is_log_disabled = curr.logging.enabled is False and (
        prev.logging.enabled is True or not curr.logging.enabled
    )
    if is_log_disabled:
        diff_kinds.add("logging_disabled")
    elif curr.logging.destination and curr.logging.destination != prev.logging.destination:
        diff_kinds.add("logging_changed")

    prev_en = set(prev.services.enabled)
    curr_en = set(curr.services.enabled)
    if curr_en - prev_en:
        diff_kinds.add("service_enabled")

    prev_dis = set(prev.services.disabled)
    curr_dis = set(curr.services.disabled)
    if curr_dis - prev_dis:
        diff_kinds.add("service_disabled")

    prev_tasks = set(prev.scheduled_tasks)
    curr_tasks = set(curr.scheduled_tasks)
    if curr_tasks - prev_tasks:
        diff_kinds.add("scheduled_task_added")

    prev_anchors = set(prev.trust_anchors)
    curr_anchors = set(curr.trust_anchors)
    if curr_anchors - prev_anchors:
        diff_kinds.add("trust_anchor_added")

    diff = diff_capabilities(prev, curr)
    diff_count = len(diff["new"]) + len(diff["changed"]) + len(diff["removed"])
    if diff_count >= 8:
        diff_kinds.add("broad_change")

    return diff_kinds


def compute_mismatch_kind(extra_caps: set[str], label: str) -> str:
    """Compute mismatch_kind from the set of extra capabilities outside expectation map."""
    if label == "consistent" or not extra_caps:
        return "none"
    severities = {CAPABILITY_SEVERITY.get(c, "warn") for c in extra_caps}
    if severities <= {"pass"}:
        return "silent"
    return "deterministic"


def verify_corpus(corpus_dir: Path | str) -> dict[str, Any]:
    """Verify all items in the AI corpus directory."""
    dir_path = Path(corpus_dir)
    if not dir_path.exists():
        raise FileNotFoundError(f"Corpus directory not found: {dir_path}")

    files = sorted(dir_path.glob("*.json"))
    if not files:
        raise ValueError(f"No JSON items found in {dir_path}")

    total_items = len(files)
    split_counts: dict[str, int] = {"exemplar": 0, "dev": 0, "test": 0}
    label_counts: dict[str, int] = {"consistent": 0, "inconsistent": 0}
    lang_counts: dict[str, int] = {"id": 0, "en": 0, "mixed": 0}
    class_counts: dict[str, int] = {f"L{i}": 0 for i in range(1, 7)}
    inconsistency_counts: dict[str, int] = {}
    consistent_per_class: dict[str, int] = {f"L{i}": 0 for i in range(1, 6)}

    mismatch_by_split: dict[str, dict[str, int]] = {
        "exemplar": {"none": 0, "silent": 0, "deterministic": 0},
        "dev": {"none": 0, "silent": 0, "deterministic": 0},
        "test": {"none": 0, "silent": 0, "deterministic": 0},
    }

    mismatches: list[str] = []
    all_items_data: list[dict] = []

    for f in files:
        data = json.loads(f.read_text(encoding="utf-8"))
        item_id = data["id"]
        split = data["split"]
        lang = data["language"]
        exp_class = data["expected_purpose_class"]
        expected_label = data["label"]
        incon_class = data.get("inconsistency_class")
        item_mismatch_kind = data.get("mismatch_kind")

        split_counts[split] = split_counts.get(split, 0) + 1
        lang_counts[lang] = lang_counts.get(lang, 0) + 1
        class_counts[exp_class] = class_counts.get(exp_class, 0) + 1

        prev_baseline = BaselineV1.model_validate(data["previous_baseline"])
        curr_baseline = BaselineV1.model_validate(data["candidate_baseline"])

        diff_kinds = compute_diff_capabilities(prev_baseline, curr_baseline)

        allowed_caps = EXPECTATION_MAP[exp_class]
        extra_caps = diff_kinds - allowed_caps
        is_consistent = len(extra_caps) == 0
        computed_label = "consistent" if is_consistent else "inconsistent"

        if computed_label != expected_label:
            mismatches.append(
                f"{item_id} ({split}): expected {expected_label}, computed {computed_label}. "
                f"Class={exp_class}, Allowed={allowed_caps}, DiffKinds={diff_kinds}"
            )

        label_counts[computed_label] += 1

        mk = compute_mismatch_kind(extra_caps, computed_label)
        if item_mismatch_kind is not None and item_mismatch_kind != mk:
            mismatches.append(
                f"{item_id} ({split}): mismatch_kind in file ({item_mismatch_kind}) "
                f"differs from computed ({mk})"
            )

        mismatch_by_split[split][mk] += 1

        if split != "exemplar":
            if computed_label == "consistent":
                consistent_per_class[exp_class] = consistent_per_class.get(exp_class, 0) + 1
            else:
                incon_key = incon_class or "unspecified"
                inconsistency_counts[incon_key] = inconsistency_counts.get(incon_key, 0) + 1

        all_items_data.append({
            **data,
            "_diff_kinds": sorted(diff_kinds),
            "_extra_caps": sorted(extra_caps),
            "_mismatch_kind": mk,
        })

    if mismatches:
        print("\n[ERROR] Ground-truth label or mismatch_kind mismatches found:")
        for m in mismatches:
            print(f"  - {m}")
        raise ValueError(f"{len(mismatches)} ground truth mismatches in corpus")

    errors: list[str] = []
    if total_items != 66:
        errors.append(f"Expected 66 total items, found {total_items}")
    if split_counts["exemplar"] != 6:
        errors.append(f"Expected 6 exemplars, found {split_counts['exemplar']}")
    if split_counts["dev"] != 24:
        errors.append(f"Expected 24 dev items, found {split_counts['dev']}")
    if split_counts["test"] != 36:
        errors.append(f"Expected 36 test items, found {split_counts['test']}")

    eval_consistent = sum(
        1 for it in all_items_data if it["split"] != "exemplar" and it["label"] == "consistent"
    )
    eval_inconsistent = sum(
        1 for it in all_items_data if it["split"] != "exemplar" and it["label"] == "inconsistent"
    )

    if eval_consistent != 30:
        errors.append(f"Expected 30 evaluation consistent items, found {eval_consistent}")
    if eval_inconsistent != 30:
        errors.append(f"Expected 30 evaluation inconsistent items, found {eval_inconsistent}")

    for c_id in ["L1", "L2", "L3", "L4", "L5"]:
        if consistent_per_class.get(c_id, 0) != 6:
            errors.append(
                f"Expected 6 consistent items for {c_id}, found {consistent_per_class.get(c_id, 0)}"
            )

    dev_silent = mismatch_by_split["dev"]["silent"]
    test_silent = mismatch_by_split["test"]["silent"]
    if dev_silent != 7:
        errors.append(f"Expected 7 silent items in dev, found {dev_silent}")
    if test_silent != 11:
        errors.append(f"Expected 11 silent items in test, found {test_silent}")

    for it in all_items_data:
        cat = it.get("inconsistency_class")
        if cat == "hidden_extra_impact" and it["_mismatch_kind"] != "silent":
            errors.append(
                f"{it['id']}: hidden_extra_impact must be silent, got {it['_mismatch_kind']}"
            )
        if cat == "vague_or_misleading_purpose" and it["_mismatch_kind"] != "silent":
            errors.append(
                f"{it['id']}: vague_or_misleading_purpose must be silent, "
                f"got {it['_mismatch_kind']}"
            )

    if errors:
        print("\n[ERROR] Stratification validation errors:")
        for e in errors:
            print(f"  - {e}")
        raise ValueError(f"{len(errors)} stratification errors in corpus")

    return {
        "total_items": total_items,
        "split_counts": split_counts,
        "label_counts": label_counts,
        "eval_consistent": eval_consistent,
        "eval_inconsistent": eval_inconsistent,
        "lang_counts": lang_counts,
        "class_counts": class_counts,
        "eval_consistent_per_class": consistent_per_class,
        "inconsistency_category_counts": inconsistency_counts,
        "mismatch_by_split": mismatch_by_split,
        "all_items_data": all_items_data,
    }


def generate_review_summary_md(summary: dict[str, Any], output_file: Path | str) -> str:
    """Generate docs/ai_corpus_review_summary.md contents and optionally write to file."""
    items = summary["all_items_data"]
    split_counts = summary["split_counts"]
    mismatch_by_split = summary["mismatch_by_split"]
    lang_counts = summary["lang_counts"]

    lang_by_split: dict[str, dict[str, int]] = {
        "exemplar": {"id": 0, "en": 0, "mixed": 0},
        "dev": {"id": 0, "en": 0, "mixed": 0},
        "test": {"id": 0, "en": 0, "mixed": 0},
    }
    for it in items:
        lang_by_split[it["split"]][it["language"]] += 1

    class_by_split: dict[str, dict[str, int]] = {
        f"L{i}": {"exemplar": 0, "dev": 0, "test": 0, "total": 0} for i in range(1, 7)
    }
    for it in items:
        c = it["expected_purpose_class"]
        s = it["split"]
        class_by_split[c][s] += 1
        class_by_split[c]["total"] += 1

    eval_con_per_class: dict[str, dict[str, int]] = {
        f"L{i}": {"dev": 0, "test": 0, "total": 0} for i in range(1, 6)
    }
    for it in items:
        if it["split"] != "exemplar" and it["label"] == "consistent":
            c = it["expected_purpose_class"]
            s = it["split"]
            eval_con_per_class[c][s] += 1
            eval_con_per_class[c]["total"] += 1

    incon_cats = [
        "hidden_extra_impact",
        "vague_or_misleading_purpose",
        "privilege_escalation",
        "control_weakening",
        "over_broad_change",
    ]
    eval_incon_per_cat: dict[str, dict[str, int]] = {
        cat: {"dev": 0, "test": 0, "total": 0} for cat in incon_cats
    }
    for it in items:
        if it["split"] != "exemplar" and it["label"] == "inconsistent":
            cat = it.get("inconsistency_class")
            if cat in eval_incon_per_cat:
                s = it["split"]
                eval_incon_per_cat[cat][s] += 1
                eval_incon_per_cat[cat]["total"] += 1

    ex_con = sum(1 for it in items if it["split"] == "exemplar" and it["label"] == "consistent")
    ex_inc = sum(1 for it in items if it["split"] == "exemplar" and it["label"] == "inconsistent")
    dev_con = sum(1 for it in items if it["split"] == "dev" and it["label"] == "consistent")
    dev_inc = sum(1 for it in items if it["split"] == "dev" and it["label"] == "inconsistent")
    test_con = sum(1 for it in items if it["split"] == "test" and it["label"] == "consistent")
    test_inc = sum(1 for it in items if it["split"] == "test" and it["label"] == "inconsistent")
    tot_con = ex_con + dev_con + test_con
    tot_inc = ex_inc + dev_inc + test_inc
    tot_all = tot_con + tot_inc

    random.seed(42)
    sampled = sorted(random.sample(items, 16), key=lambda x: x["id"])

    # Header section
    p1 = (
        "This document summarizes the composition, stratification, and sample review of the "
        "SEGEL AI purpose and expectation corpus in `lab/ai_corpus/`. The corpus was authored "
        "with AI assistance, adheres to Baseline v1 JSON schema, and is validated by "
        "`scripts/ai_eval/verify_corpus.py` against the expectation map in "
        "`docs/ai_decisions.md` (D17, D9b)."
    )
    p2 = (
        "> Per project rules, no model under test (such as Ollama or local LLMs) was used to "
        "author or assign ground-truth labels. Ground-truth labels and `mismatch_kind` are "
        "determined by structural diff evaluation of candidate configurations against the "
        "predecessor baseline. Keyword evasion is measured in AI-4 against the independently "
        "written docs/b1_keywords.md."
    )

    t_none = (
        mismatch_by_split["exemplar"]["none"]
        + mismatch_by_split["dev"]["none"]
        + mismatch_by_split["test"]["none"]
    )
    t_silent = (
        mismatch_by_split["exemplar"]["silent"]
        + mismatch_by_split["dev"]["silent"]
        + mismatch_by_split["test"]["silent"]
    )
    t_det = (
        mismatch_by_split["exemplar"]["deterministic"]
        + mismatch_by_split["dev"]["deterministic"]
        + mismatch_by_split["test"]["deterministic"]
    )

    lines: list[str] = [
        "# SEGEL AI Purpose and Expectation Corpus: Review Summary",
        "",
        p1,
        "",
        "> [!NOTE]",
        p2,
        "",
        "---",
        "",
        "## 1. Corpus Summary Counts",
        "",
        "### Overall Splits",
        "| Split | Consistent | Inconsistent | Total |",
        "|---|---|---|---|",
        f"| Exemplar (`exemplar`) | {ex_con} | {ex_inc} | {split_counts['exemplar']} |",
        f"| Development (`dev`) | {dev_con} | {dev_inc} | {split_counts['dev']} |",
        f"| Evaluation / Test (`test`) | {test_con} | {test_inc} | {split_counts['test']} |",
        f"| **Total** | **{tot_con}** | **{tot_inc}** | **{tot_all}** |",
        "",
        "### Mismatch Kind per Split (D9b Rebalancing)",
        (
            "| Split | `none` (Consistent) | `silent` (Pass-Severity Extra) | "
            "`deterministic` (Warn/Reject Extra) | Total |"
        ),
        "|---|---|---|---|---|",
        (
            f"| Exemplar (`exemplar`) | {mismatch_by_split['exemplar']['none']} | "
            f"{mismatch_by_split['exemplar']['silent']} | "
            f"{mismatch_by_split['exemplar']['deterministic']} | {split_counts['exemplar']} |"
        ),
        (
            f"| Development (`dev`) | {mismatch_by_split['dev']['none']} | "
            f"{mismatch_by_split['dev']['silent']} | "
            f"{mismatch_by_split['dev']['deterministic']} | {split_counts['dev']} |"
        ),
        (
            f"| Evaluation / Test (`test`) | {mismatch_by_split['test']['none']} | "
            f"{mismatch_by_split['test']['silent']} | "
            f"{mismatch_by_split['test']['deterministic']} | {split_counts['test']} |"
        ),
        f"| **Total** | **{t_none}** | **{t_silent}** | **{t_det}** | **{tot_all}** |",
        "",
        "### Language Distribution",
        "| Language | Code | Exemplar | Dev | Test | Total |",
        "|---|---|---|---|---|---|",
        (
            f"| Indonesian | `id` | {lang_by_split['exemplar']['id']} | "
            f"{lang_by_split['dev']['id']} | {lang_by_split['test']['id']} | "
            f"{lang_counts['id']} |"
        ),
        (
            f"| English | `en` | {lang_by_split['exemplar']['en']} | "
            f"{lang_by_split['dev']['en']} | {lang_by_split['test']['en']} | "
            f"{lang_counts['en']} |"
        ),
        (
            f"| Mixed (ID/EN) | `mixed` | {lang_by_split['exemplar']['mixed']} | "
            f"{lang_by_split['dev']['mixed']} | {lang_by_split['test']['mixed']} | "
            f"{lang_counts['mixed']} |"
        ),
        (
            f"| **Total** | | **{split_counts['exemplar']}** | "
            f"**{split_counts['dev']}** | **{split_counts['test']}** | **{tot_all}** |"
        ),
        "",
        "### Expected Purpose Class Distribution",
        "| Class | Description | Exemplar | Dev | Test | Total |",
        "|---|---|---|---|---|---|",
        (
            f"| L1 | DNS allowlist update | {class_by_split['L1']['exemplar']} | "
            f"{class_by_split['L1']['dev']} | {class_by_split['L1']['test']} | "
            f"{class_by_split['L1']['total']} |"
        ),
        (
            f"| L2 | Account management (standard) | {class_by_split['L2']['exemplar']} | "
            f"{class_by_split['L2']['dev']} | {class_by_split['L2']['test']} | "
            f"{class_by_split['L2']['total']} |"
        ),
        (
            f"| L3 | Syslog / telemetry redirection | {class_by_split['L3']['exemplar']} | "
            f"{class_by_split['L3']['dev']} | {class_by_split['L3']['test']} | "
            f"{class_by_split['L3']['total']} |"
        ),
        (
            f"| L4 | Egress network rule update | {class_by_split['L4']['exemplar']} | "
            f"{class_by_split['L4']['dev']} | {class_by_split['L4']['test']} | "
            f"{class_by_split['L4']['total']} |"
        ),
        (
            f"| L5 | System hardening (service disabled) | {class_by_split['L5']['exemplar']} | "
            f"{class_by_split['L5']['dev']} | {class_by_split['L5']['test']} | "
            f"{class_by_split['L5']['total']} |"
        ),
        (
            f"| L6 | Vague or unclassified purpose | {class_by_split['L6']['exemplar']} | "
            f"{class_by_split['L6']['dev']} | {class_by_split['L6']['test']} | "
            f"{class_by_split['L6']['total']} |"
        ),
        (
            f"| **Total** | | **{split_counts['exemplar']}** | "
            f"**{split_counts['dev']}** | **{split_counts['test']}** | **{tot_all}** |"
        ),
        "",
        "### Consistent Evaluation Items by Purpose Class (Target: 6 each, Total: 30)",
        "| Purpose Class | Description | Dev Count | Test Count | Total Eval Count |",
        "|---|---|---|---|---|",
        (
            f"| L1 | DNS allowlist update | {eval_con_per_class['L1']['dev']} | "
            f"{eval_con_per_class['L1']['test']} | {eval_con_per_class['L1']['total']} |"
        ),
        (
            f"| L2 | Account management (standard) | {eval_con_per_class['L2']['dev']} | "
            f"{eval_con_per_class['L2']['test']} | {eval_con_per_class['L2']['total']} |"
        ),
        (
            f"| L3 | Syslog / telemetry redirection | {eval_con_per_class['L3']['dev']} | "
            f"{eval_con_per_class['L3']['test']} | {eval_con_per_class['L3']['total']} |"
        ),
        (
            f"| L4 | Egress network rule update | {eval_con_per_class['L4']['dev']} | "
            f"{eval_con_per_class['L4']['test']} | {eval_con_per_class['L4']['total']} |"
        ),
        (
            f"| L5 | System hardening (service disabled) | {eval_con_per_class['L5']['dev']} | "
            f"{eval_con_per_class['L5']['test']} | {eval_con_per_class['L5']['total']} |"
        ),
        (
            f"| **Total Consistent** | | "
            f"**{sum(v['dev'] for v in eval_con_per_class.values())}** | "
            f"**{sum(v['test'] for v in eval_con_per_class.values())}** | "
            f"**{sum(v['total'] for v in eval_con_per_class.values())}** |"
        ),
        "",
        "### Inconsistent Evaluation Items by Category (D9b Target: Dev 12, Test 18)",
        (
            "| Inconsistency Category | Category Key | Mismatch Kind | Dev Count | "
            "Test Count | Total Eval Count |"
        ),
        "|---|---|---|---|---|---|",
        (
            f"| (a) Hidden extra impact | `hidden_extra_impact` | `silent` | "
            f"{eval_incon_per_cat['hidden_extra_impact']['dev']} | "
            f"{eval_incon_per_cat['hidden_extra_impact']['test']} | "
            f"{eval_incon_per_cat['hidden_extra_impact']['total']} |"
        ),
        (
            f"| (b) Vague or misleading purpose | `vague_or_misleading_purpose` | `silent` | "
            f"{eval_incon_per_cat['vague_or_misleading_purpose']['dev']} | "
            f"{eval_incon_per_cat['vague_or_misleading_purpose']['test']} | "
            f"{eval_incon_per_cat['vague_or_misleading_purpose']['total']} |"
        ),
        (
            f"| (c) Privilege escalation | `privilege_escalation` | `deterministic` | "
            f"{eval_incon_per_cat['privilege_escalation']['dev']} | "
            f"{eval_incon_per_cat['privilege_escalation']['test']} | "
            f"{eval_incon_per_cat['privilege_escalation']['total']} |"
        ),
        (
            f"| (d) Control weakening | `control_weakening` | `deterministic` | "
            f"{eval_incon_per_cat['control_weakening']['dev']} | "
            f"{eval_incon_per_cat['control_weakening']['test']} | "
            f"{eval_incon_per_cat['control_weakening']['total']} |"
        ),
        (
            f"| (e) Over-broad change (diff >= 8) | `over_broad_change` | `deterministic` | "
            f"{eval_incon_per_cat['over_broad_change']['dev']} | "
            f"{eval_incon_per_cat['over_broad_change']['test']} | "
            f"{eval_incon_per_cat['over_broad_change']['total']} |"
        ),
        (
            f"| **Total Inconsistent** | | | "
            f"**{sum(v['dev'] for v in eval_incon_per_cat.values())}** | "
            f"**{sum(v['test'] for v in eval_incon_per_cat.values())}** | "
            f"**{sum(v['total'] for v in eval_incon_per_cat.values())}** |"
        ),
        "",
        "---",
        "",
        "## 2. 16 Items Sampled with Fixed Seed (Seed = 42)",
        "",
        (
            "The following 16 items were sampled randomly using Python standard library "
            "`random.seed(42)` and sorted by item ID:"
        ),
        "",
        (
            "| Item ID | Split | Lang | Purpose Text | Candidate - Previous Capabilities | "
            "Expected Class | Label | Inconsistency Class | Mismatch Kind |"
        ),
        "|---|---|---|---|---|---|---|---|---|",
    ]

    for it in sampled:
        diff_str = ", ".join(it["_diff_kinds"]) if it["_diff_kinds"] else "none"
        incon = it.get("inconsistency_class") or "-"
        lines.append(
            f"| `{it['id']}` | {it['split']} | {it['language']} | {it['purpose']} | "
            f"`{diff_str}` | {it['expected_purpose_class']} | {it['label']} | "
            f"{incon} | `{it['_mismatch_kind']}` |"
        )

    lines.extend([
        "",
        "---",
        "",
        "## 3. Script Validation Output",
        "",
        "Execution of `scripts/ai_eval/verify_corpus.py` reports:",
        "",
        "```",
        "Verifying corpus at: lab/ai_corpus",
        "",
        "============================================================",
        "AI CORPUS VERIFICATION: ALL CHECKS PASSED",
        "============================================================",
        f"Total items:           {summary['total_items']}",
        (
            f"Splits:                {split_counts['exemplar']} exemplars, "
            f"{split_counts['dev']} dev, {split_counts['test']} test"
        ),
        (
            f"Evaluation items:      {summary['eval_consistent']} consistent, "
            f"{summary['eval_inconsistent']} inconsistent (total 60)"
        ),
        (
            f"Languages:             {lang_counts['id']} id, {lang_counts['en']} en, "
            f"{lang_counts['mixed']} mixed"
        ),
        f"Consistent by Class:   {summary['eval_consistent_per_class']}",
        f"Inconsistent by Cat:   {summary['inconsistency_category_counts']}",
        "",
        "Counts per split x mismatch_kind:",
        "  split               none     silent    deterministic",
        (
            f"  exemplar               {mismatch_by_split['exemplar']['none']}          "
            f"{mismatch_by_split['exemplar']['silent']}                "
            f"{mismatch_by_split['exemplar']['deterministic']}"
        ),
        (
            f"  dev                   {mismatch_by_split['dev']['none']}          "
            f"{mismatch_by_split['dev']['silent']}                "
            f"{mismatch_by_split['dev']['deterministic']}"
        ),
        (
            f"  test                  {mismatch_by_split['test']['none']}         "
            f"{mismatch_by_split['test']['silent']}                "
            f"{mismatch_by_split['test']['deterministic']}"
        ),
        "============================================================",
        "```",
        "",
        "- Ground truth evaluation mismatches: 0",
        "- Schema validation failures: 0",
        "- Stratification requirement errors: 0",
        "- Mismatch kind calculation errors: 0",
        (
            "- Keyword evasion is measured in AI-4 against the independently written "
            "docs/b1_keywords.md."
        ),
        "",
    ])

    content = "\n".join(lines)
    if output_file:
        out_p = Path(output_file)
        out_p.parent.mkdir(parents=True, exist_ok=True)
        out_p.write_text(content, encoding="utf-8")
        print(f"Wrote summary to: {out_p}")
    return content


def generate_compact_tsv(summary: dict[str, Any]) -> str:
    """Generate compact TSV of all 66 items."""
    header = (
        "id\tsplit\tlang\texpected_class\tlabel\tcategory\tmismatch_kind\t"
        "candidate_minus_previous_caps\tpurpose"
    )
    lines = [header]
    for it in summary["all_items_data"]:
        diff_str = ",".join(it["_diff_kinds"]) if it["_diff_kinds"] else "none"
        cat_str = it.get("inconsistency_class") or "none"
        lines.append(
            f"{it['id']}\t{it['split']}\t{it['language']}\t{it['expected_purpose_class']}\t"
            f"{it['label']}\t{cat_str}\t{it['_mismatch_kind']}\t{diff_str}\t{it['purpose']}"
        )
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Verify SEGEL AI corpus and optionally generate summary."
    )
    parser.add_argument(
        "--summary",
        type=str,
        default=None,
        help="Path to write docs/ai_corpus_review_summary.md",
    )
    parser.add_argument("--tsv", action="store_true", help="Print compact TSV of all items")
    args = parser.parse_args()

    corpus_dir = WORKSPACE_ROOT / "lab" / "ai_corpus"
    print("Verifying corpus at: lab/ai_corpus")
    try:
        summary = verify_corpus(corpus_dir)
        print("\n" + "=" * 60)
        print("AI CORPUS VERIFICATION: ALL CHECKS PASSED")
        print("=" * 60)
        print(f"Total items:           {summary['total_items']}")
        print(
            f"Splits:                {summary['split_counts']['exemplar']} exemplars, "
            f"{summary['split_counts']['dev']} dev, {summary['split_counts']['test']} test"
        )
        print(
            f"Evaluation items:      {summary['eval_consistent']} consistent, "
            f"{summary['eval_inconsistent']} inconsistent (total 60)"
        )
        print(
            f"Languages:             {summary['lang_counts']['id']} id, "
            f"{summary['lang_counts']['en']} en, {summary['lang_counts']['mixed']} mixed"
        )
        print(f"Consistent by Class:   {summary['eval_consistent_per_class']}")
        print(f"Inconsistent by Cat:   {summary['inconsistency_category_counts']}")
        print("\nCounts per split x mismatch_kind:")
        print(f"  {'split':<12} {'none':>8} {'silent':>10} {'deterministic':>16}")
        for split in ["exemplar", "dev", "test"]:
            d = summary["mismatch_by_split"][split]
            print(f"  {split:<12} {d['none']:>8} {d['silent']:>10} {d['deterministic']:>16}")
        print("=" * 60)

        if args.summary:
            generate_review_summary_md(summary, args.summary)

        if args.tsv:
            print("\nCOMPACT TSV:")
            print(generate_compact_tsv(summary))

    except Exception as exc:
        print(f"\nVerification FAILED: {exc}")
        sys.exit(1)


if __name__ == "__main__":
    main()
