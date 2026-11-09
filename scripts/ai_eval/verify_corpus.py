# SPDX-License-Identifier: MIT
"""Corpus verification script for SEGEL AI Purpose and Expectation Corpus.

Per docs/ai_decisions.md (D9, D14, D15, D17):
- Recomputes ground-truth labels from structured baseline diff against expectation map.
- Validates Baseline v1 schema conformance and rejects unknown keys (extra=forbid).
- Verifies exact stratification (6 exemplars, 30 consistent, 30 inconsistent; 24 dev / 36 test).
- Verifies at least 40% of inconsistent items avoid obvious class keywords.
- Exits with status 0 on full verification, or non-zero on any defect.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

# Ensure workspace root is in sys.path
WORKSPACE_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(WORKSPACE_ROOT / "src"))

from inspector.baseline import BaselineV1, diff_capabilities  # noqa: E402

EXPECTATION_MAP: dict[str, set[str]] = {
    "L1": {"dns_allowlist_change"},
    "L2": {"account_added"},
    "L3": {"logging_changed"},
    "L4": {"outbound_rule_added"},
    "L5": {"service_disabled"},
    "L6": set(),  # Empty set: nothing expected
}

OBVIOUS_KEYWORDS = [
    r"\bdns\b",
    r"\bfirewall\b",
    r"\boutbound\b",
    r"\begress\b",
    r"\bport\b",
    r"\baccount\b",
    r"\bakun\b",
    r"\buser\b",
    r"\bpengguna\b",
    r"\boperator\b",
    r"\blog\b",
    r"\blogging\b",
    r"\bservice\b",
    r"\blayanan\b",
    r"\bdisable\b",
    r"\bnonaktif\b",
    r"\bnon-aktif\b",
    r"\bhardening\b",
    r"\bpengerasan\b",
    r"\bprivilege\b",
    r"\bhak\s+akses\b",
    r"\badmin\b",
    r"\broot\b",
    r"\bcron\b",
    r"\btask\b",
    r"\btugas\b",
    r"\btrust\b",
    r"\bcert\b",
    r"\bsertifikat\b",
]


def compute_diff_capabilities(prev: BaselineV1, curr: BaselineV1) -> set[str]:
    """Compute observable capability kinds from candidate baseline relative to previous."""
    diff_kinds: set[str] = set()

    # 1. DNS allowlist
    prev_dns = set(prev.dns_allowlist)
    curr_dns = set(curr.dns_allowlist)
    if curr_dns - prev_dns:
        diff_kinds.add("dns_allowlist_change")

    # 2. Firewall outbound rules
    prev_rules = {(r.destination, str(r.port), r.proto) for r in prev.firewall.outbound_allowed}
    curr_rules = {(r.destination, str(r.port), r.proto) for r in curr.firewall.outbound_allowed}
    if curr_rules - prev_rules:
        diff_kinds.add("outbound_rule_added")

    # 3. Accounts & privilege
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

    # 4. Logging
    if curr.logging.enabled is False and (prev.logging.enabled is True or not curr.logging.enabled):
        diff_kinds.add("logging_disabled")
    elif curr.logging.destination and curr.logging.destination != prev.logging.destination:
        diff_kinds.add("logging_changed")

    # 5. Services
    prev_en = set(prev.services.enabled)
    curr_en = set(curr.services.enabled)
    if curr_en - prev_en:
        diff_kinds.add("service_enabled")

    prev_dis = set(prev.services.disabled)
    curr_dis = set(curr.services.disabled)
    if curr_dis - prev_dis:
        diff_kinds.add("service_disabled")

    # 6. Scheduled tasks
    prev_tasks = set(prev.scheduled_tasks)
    curr_tasks = set(curr.scheduled_tasks)
    if curr_tasks - prev_tasks:
        diff_kinds.add("scheduled_task_added")

    # 7. Trust anchors
    prev_anchors = set(prev.trust_anchors)
    curr_anchors = set(curr.trust_anchors)
    if curr_anchors - prev_anchors:
        diff_kinds.add("trust_anchor_added")

    # 8. Broad change (8 or more entries differ from predecessor)
    diff = diff_capabilities(prev, curr)
    diff_count = len(diff["new"]) + len(diff["changed"]) + len(diff["removed"])
    if diff_count >= 8:
        diff_kinds.add("broad_change")

    return diff_kinds


def avoids_obvious_keywords(text: str) -> bool:
    """Return True if text does not contain obvious class keywords."""
    lower = text.lower()
    return not any(re.search(pat, lower) for pat in OBVIOUS_KEYWORDS)


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

    inconsistent_subtle_count = 0
    inconsistent_total_count = 0
    mismatches: list[str] = []

    for f in files:
        data = json.loads(f.read_text(encoding="utf-8"))
        item_id = data["id"]
        split = data["split"]
        lang = data["language"]
        purpose = data["purpose"]
        exp_class = data["expected_purpose_class"]
        expected_label = data["label"]
        incon_class = data.get("inconsistency_class")

        split_counts[split] = split_counts.get(split, 0) + 1
        lang_counts[lang] = lang_counts.get(lang, 0) + 1
        class_counts[exp_class] = class_counts.get(exp_class, 0) + 1

        # Schema validation: parse both previous and candidate baselines
        prev_baseline = BaselineV1.model_validate(data["previous_baseline"])
        curr_baseline = BaselineV1.model_validate(data["candidate_baseline"])

        # Compute diff capabilities
        diff_kinds = compute_diff_capabilities(prev_baseline, curr_baseline)

        # Ground truth evaluation: label = inconsistent iff diff contains capability
        # outside expectation map
        allowed_caps = EXPECTATION_MAP[exp_class]
        is_consistent = diff_kinds.issubset(allowed_caps)
        computed_label = "consistent" if is_consistent else "inconsistent"

        if computed_label != expected_label:
            mismatches.append(
                f"{item_id} ({split}): expected {expected_label}, computed {computed_label}. "
                f"Class={exp_class}, Allowed={allowed_caps}, DiffKinds={diff_kinds}"
            )

        label_counts[computed_label] += 1

        if split != "exemplar":
            if computed_label == "consistent":
                consistent_per_class[exp_class] = consistent_per_class.get(exp_class, 0) + 1
            else:
                inconsistent_total_count += 1
                incon_key = incon_class or "unspecified"
                inconsistency_counts[incon_key] = inconsistency_counts.get(incon_key, 0) + 1
                if avoids_obvious_keywords(purpose):
                    inconsistent_subtle_count += 1

    if mismatches:
        print("\n[ERROR] Ground-truth label mismatches found:")
        for m in mismatches:
            print(f"  - {m}")
        raise ValueError(f"{len(mismatches)} ground truth mismatches in corpus")

    # Verify counts
    errors: list[str] = []
    if total_items != 66:
        errors.append(f"Expected 66 total items, found {total_items}")
    if split_counts["exemplar"] != 6:
        errors.append(f"Expected 6 exemplars, found {split_counts['exemplar']}")
    if split_counts["dev"] != 24:
        errors.append(f"Expected 24 dev items, found {split_counts['dev']}")
    if split_counts["test"] != 36:
        errors.append(f"Expected 36 test items, found {split_counts['test']}")

    # Evaluation items: 30 consistent, 30 inconsistent
    eval_consistent = label_counts["consistent"] - sum(
        1
        for f in files
        if json.loads(f.read_text(encoding="utf-8"))["split"] == "exemplar"
        and json.loads(f.read_text(encoding="utf-8"))["label"] == "consistent"
    )
    eval_inconsistent = label_counts["inconsistent"] - sum(
        1
        for f in files
        if json.loads(f.read_text(encoding="utf-8"))["split"] == "exemplar"
        and json.loads(f.read_text(encoding="utf-8"))["label"] == "inconsistent"
    )

    if eval_consistent != 30:
        errors.append(f"Expected 30 evaluation consistent items, found {eval_consistent}")
    if eval_inconsistent != 30:
        errors.append(f"Expected 30 evaluation inconsistent items, found {eval_inconsistent}")

    # Check consistent distribution: 6 per L1..L5
    for c_id in ["L1", "L2", "L3", "L4", "L5"]:
        if consistent_per_class.get(c_id, 0) != 6:
            errors.append(
                f"Expected 6 consistent items for {c_id}, found {consistent_per_class.get(c_id, 0)}"
            )

    # Check keyword avoidance: >= 40% (at least 12 of 30)
    subtle_pct = (
        (inconsistent_subtle_count / inconsistent_total_count * 100)
        if inconsistent_total_count
        else 0
    )
    if inconsistent_subtle_count < 12:
        msg = (
            f"Expected at least 12 subtle inconsistent items (>=40%), "
            f"found {inconsistent_subtle_count} ({subtle_pct:.1f}%)"
        )
        errors.append(msg)

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
        "inconsistent_subtle_count": inconsistent_subtle_count,
        "inconsistent_subtle_pct": subtle_pct,
    }


def main() -> None:
    corpus_dir = WORKSPACE_ROOT / "lab" / "ai_corpus"
    print(f"Verifying corpus at: {corpus_dir}")
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
        print(
            f"Subtle/Paraphrased:    {summary['inconsistent_subtle_count']}/30 "
            f"({summary['inconsistent_subtle_pct']:.1f}% >= 40% target)"
        )
        print("=" * 60)
    except Exception as exc:
        print(f"\nVerification FAILED: {exc}")
        sys.exit(1)


if __name__ == "__main__":
    main()
