# SPDX-License-Identifier: MIT
"""Baseline evaluation harness for SEGEL AI Purpose and Expectation Corpus.

Per docs/ai_decisions.md (D6, D15, D17):
- Evaluates Baseline B0 (no expectation check, default capability rules only)
  and Baseline B1 (generic keyword classifier per docs/b1_keywords.md).
- Evaluates ONLY the DEV split (DEV-*.json). Test split is strictly isolated.
- Reports metrics across:
  (i) all inconsistent items
  (ii) deterministic inconsistent items (and default severity flagging)
  (iii) silent inconsistent items (the AI-relevant subset)
- Defines the 'hard subset': silent inconsistent items missed by B1.
- Breaks down silent items by purpose class and language.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(WORKSPACE_ROOT / "src"))
sys.path.insert(0, str(WORKSPACE_ROOT))

from inspector.baseline import BaselineV1  # noqa: E402
from inspector.policy.expectations import (  # noqa: E402
    classify_purpose_b1,
    derive_findings,
)
from scripts.ai_eval.guard import (  # noqa: E402
    guard_read_corpus_file,
)
from scripts.ai_eval.verify_corpus import (  # noqa: E402
    CAPABILITY_SEVERITY,
    compute_diff_capabilities,
)


def calculate_metrics(
    tp: int,
    fn: int,
    fp: int,
    tn: int,
) -> dict[str, Any]:
    """Calculate confusion counts and classification metrics."""
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) > 0 else 0.0
    return {
        "tp": tp,
        "fn": fn,
        "fp": fp,
        "tn": tn,
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1": round(f1, 4),
    }


def evaluate_dev_split(
    corpus_dir: Path | str,
) -> dict[str, Any]:
    """Evaluate B0 and B1 baselines on the DEV split of the corpus."""
    dir_path = Path(corpus_dir)
    dev_files = sorted(dir_path.glob("DEV-*.json"))
    if not dev_files:
        raise FileNotFoundError(f"No DEV-*.json files found in {dir_path}")

    items: list[dict[str, Any]] = []
    for f in dev_files:
        data = guard_read_corpus_file(f)
        if data.get("split") != "dev":
            raise ValueError(f"File {f.name} has split '{data.get('split')}', expected 'dev'")
        prev = BaselineV1.model_validate(data["previous_baseline"])
        curr = BaselineV1.model_validate(data["candidate_baseline"])
        diff_kinds = compute_diff_capabilities(prev, curr)

        # Default severity evaluation
        has_default_severity_flag = any(
            CAPABILITY_SEVERITY.get(c, "warn") in {"warn", "reject"} for c in diff_kinds
        )

        # Baseline B0: no expectation check -> 0 expectation findings
        b0_detected = False

        # Baseline B1: keyword classification + expectation check
        b1_class = classify_purpose_b1(data.get("purpose"))
        b1_findings = derive_findings(b1_class, diff_kinds)
        b1_detected = len(b1_findings) > 0

        items.append({
            "id": data["id"],
            "split": data["split"],
            "language": data["language"],
            "purpose": data["purpose"],
            "expected_purpose_class": data["expected_purpose_class"],
            "label": data["label"],
            "inconsistency_class": data.get("inconsistency_class"),
            "mismatch_kind": data["mismatch_kind"],
            "diff_kinds": sorted(diff_kinds),
            "default_severity_flagged": has_default_severity_flag,
            "b0_detected": b0_detected,
            "b1_class": b1_class,
            "b1_detected": b1_detected,
            "b1_findings": b1_findings,
        })

    consistent_items = [it for it in items if it["label"] == "consistent"]
    inconsistent_items = [it for it in items if it["label"] == "inconsistent"]
    deterministic_incon = [
        it for it in inconsistent_items if it["mismatch_kind"] == "deterministic"
    ]
    silent_incon = [it for it in inconsistent_items if it["mismatch_kind"] == "silent"]

    # Consistent items evaluation
    b0_fp = sum(1 for it in consistent_items if it["b0_detected"])
    b0_tn = len(consistent_items) - b0_fp
    b1_fp = sum(1 for it in consistent_items if it["b1_detected"])
    b1_tn = len(consistent_items) - b1_fp

    # B0 metrics
    b0_all = calculate_metrics(
        tp=sum(1 for it in inconsistent_items if it["b0_detected"]),
        fn=sum(1 for it in inconsistent_items if not it["b0_detected"]),
        fp=b0_fp,
        tn=b0_tn,
    )
    b0_det = calculate_metrics(
        tp=sum(1 for it in deterministic_incon if it["b0_detected"]),
        fn=sum(1 for it in deterministic_incon if not it["b0_detected"]),
        fp=b0_fp,
        tn=b0_tn,
    )
    b0_silent = calculate_metrics(
        tp=sum(1 for it in silent_incon if it["b0_detected"]),
        fn=sum(1 for it in silent_incon if not it["b0_detected"]),
        fp=b0_fp,
        tn=b0_tn,
    )

    # B1 metrics
    b1_all = calculate_metrics(
        tp=sum(1 for it in inconsistent_items if it["b1_detected"]),
        fn=sum(1 for it in inconsistent_items if not it["b1_detected"]),
        fp=b1_fp,
        tn=b1_tn,
    )
    b1_det = calculate_metrics(
        tp=sum(1 for it in deterministic_incon if it["b1_detected"]),
        fn=sum(1 for it in deterministic_incon if not it["b1_detected"]),
        fp=b1_fp,
        tn=b1_tn,
    )
    b1_silent = calculate_metrics(
        tp=sum(1 for it in silent_incon if it["b1_detected"]),
        fn=sum(1 for it in silent_incon if not it["b1_detected"]),
        fp=b1_fp,
        tn=b1_tn,
    )

    # Deterministic items flagged by default-severity rules regardless of purpose
    det_flagged_by_rules = sum(1 for it in deterministic_incon if it["default_severity_flagged"])
    silent_flagged_by_rules = sum(1 for it in silent_incon if it["default_severity_flagged"])
    det_ratio = (
        det_flagged_by_rules / len(deterministic_incon) if deterministic_incon else 0.0
    )

    # Hard subset: silent items missed by B1
    hard_subset = [it["id"] for it in silent_incon if not it["b1_detected"]]

    # Per-class breakdown for silent items
    per_class_silent: dict[str, dict[str, Any]] = {}
    for cls in ["L1", "L2", "L3", "L4", "L5", "L6"]:
        cls_items = [it for it in silent_incon if it["expected_purpose_class"] == cls]
        tp = sum(1 for it in cls_items if it["b1_detected"])
        fn = sum(1 for it in cls_items if not it["b1_detected"])
        rec = (tp / len(cls_items)) if cls_items else 0.0
        per_class_silent[cls] = {
            "total": len(cls_items),
            "detected": tp,
            "missed": fn,
            "recall": round(rec, 4),
        }

    # Per-language breakdown for silent items
    per_lang_silent: dict[str, dict[str, Any]] = {}
    for lang in ["id", "en", "mixed"]:
        lang_items = [it for it in silent_incon if it["language"] == lang]
        tp = sum(1 for it in lang_items if it["b1_detected"])
        fn = sum(1 for it in lang_items if not it["b1_detected"])
        rec = (tp / len(lang_items)) if lang_items else 0.0
        per_lang_silent[lang] = {
            "total": len(lang_items),
            "detected": tp,
            "missed": fn,
            "recall": round(rec, 4),
        }

    return {
        "counts": {
            "total_dev": len(items),
            "consistent": len(consistent_items),
            "inconsistent_total": len(inconsistent_items),
            "inconsistent_deterministic": len(deterministic_incon),
            "inconsistent_silent": len(silent_incon),
        },
        "default_severity_detection": {
            "deterministic_flagged": det_flagged_by_rules,
            "deterministic_total": len(deterministic_incon),
            "deterministic_ratio": det_ratio,
            "silent_flagged": silent_flagged_by_rules,
            "silent_total": len(silent_incon),
        },
        "baselines": {
            "b0": {
                "all": b0_all,
                "deterministic": b0_det,
                "silent": b0_silent,
                "false_positives": b0_fp,
            },
            "b1": {
                "all": b1_all,
                "deterministic": b1_det,
                "silent": b1_silent,
                "false_positives": b1_fp,
            },
        },
        "hard_subset": {
            "ids": hard_subset,
            "size": len(hard_subset),
        },
        "silent_breakdown": {
            "by_class": per_class_silent,
            "by_language": per_lang_silent,
        },
    }


def print_evaluation_report(results: dict[str, Any]) -> None:
    """Print formatted evaluation report."""
    counts = results["counts"]
    def_sev = results["default_severity_detection"]
    b0 = results["baselines"]["b0"]
    b1 = results["baselines"]["b1"]
    hard = results["hard_subset"]
    by_class = results["silent_breakdown"]["by_class"]
    by_lang = results["silent_breakdown"]["by_language"]

    print("=" * 72)
    print("SEGEL BASELINE EVALUATION REPORT (DEV SPLIT ONLY)")
    print("=" * 72)
    print(f"Total DEV Items: {counts['total_dev']}")
    print(f"  - Consistent:             {counts['consistent']}")
    print(f"  - Inconsistent Total:     {counts['inconsistent_total']}")
    print(f"    * Deterministic:        {counts['inconsistent_deterministic']}")
    print(f"    * Silent (AI-relevant): {counts['inconsistent_silent']}")
    print()

    print("-" * 72)
    print("1. DETERMINISTIC DEFAULT-SEVERITY RULES (Purpose-Agnostic)")
    print("-" * 72)
    det_ratio = def_sev["deterministic_ratio"] * 100
    print(
        f"Deterministic items flagged by default severity: "
        f"{def_sev['deterministic_flagged']}/{def_sev['deterministic_total']} ({det_ratio:.1f}%)"
    )
    print(
        f"Silent items flagged by default severity:        "
        f"{def_sev['silent_flagged']}/{def_sev['silent_total']} (0.0%)"
    )
    print()

    print("-" * 72)
    print("2. BASELINE B0 (No Expectation Check) & B1 (Keyword Baseline)")
    print("-" * 72)
    header = (
        f"{'Subset':<22} | {'Method':<6} | {'TP':<3} | {'FN':<3} | {'FP':<3} | "
        f"{'TN':<3} | {'Precision':<9} | {'Recall':<7} | {'F1':<6}"
    )
    print(header)
    print("-" * 72)

    subsets = [
        ("(i) All Inconsistent", "all"),
        ("(ii) Deterministic", "deterministic"),
        ("(iii) Silent", "silent"),
    ]
    for label, key in subsets:
        b0_m = b0[key]
        b1_m = b1[key]
        row_b0 = (
            f"{label:<22} | {'B0':<6} | {b0_m['tp']:<3} | {b0_m['fn']:<3} | "
            f"{b0_m['fp']:<3} | {b0_m['tn']:<3} | {b0_m['precision']:<9.4f} | "
            f"{b0_m['recall']:<7.4f} | {b0_m['f1']:<6.4f}"
        )
        row_b1 = (
            f"{'':<22} | {'B1':<6} | {b1_m['tp']:<3} | {b1_m['fn']:<3} | "
            f"{b1_m['fp']:<3} | {b1_m['tn']:<3} | {b1_m['precision']:<9.4f} | "
            f"{b1_m['recall']:<7.4f} | {b1_m['f1']:<6.4f}"
        )
        print(row_b0)
        print(row_b1)
        print("-" * 72)

    print()
    print("-" * 72)
    print("3. FALSE POSITIVES ON CONSISTENT ITEMS")
    print("-" * 72)
    print(
        f"B0 False Positives on Consistent Items: "
        f"{b0['false_positives']} / {counts['consistent']}"
    )
    print(
        f"B1 False Positives on Consistent Items: "
        f"{b1['false_positives']} / {counts['consistent']} (Target: 0)"
    )
    print()

    print("-" * 72)
    print("4. HARD SUBSET (Silent Inconsistent Items Missed by B1)")
    print("-" * 72)
    silent_tot = counts["inconsistent_silent"]
    hard_ratio = hard["size"] / silent_tot * 100 if silent_tot else 0.0
    print(f"Hard Subset Size: {hard['size']} / {silent_tot} ({hard_ratio:.1f}%)")
    print(f"Hard Subset IDs:  {hard['ids']}")
    print()

    print("-" * 72)
    print("5. SILENT ITEMS BREAKDOWN BY PURPOSE CLASS")
    print("-" * 72)
    print(f"{'Class':<8} | {'Total':<6} | {'Detected':<9} | {'Missed':<7} | {'Recall':<7}")
    print("-" * 45)
    for cls, data in sorted(by_class.items()):
        rec_pct = data["recall"] * 100
        print(
            f"{cls:<8} | {data['total']:<6} | {data['detected']:<9} | "
            f"{data['missed']:<7} | {rec_pct:>5.1f}%"
        )
    print()

    print("-" * 72)
    print("6. SILENT ITEMS BREAKDOWN BY LANGUAGE")
    print("-" * 72)
    print(f"{'Language':<10} | {'Total':<6} | {'Detected':<9} | {'Missed':<7} | {'Recall':<7}")
    print("-" * 45)
    for lang, data in sorted(by_lang.items()):
        rec_pct = data["recall"] * 100
        print(
            f"{lang:<10} | {data['total']:<6} | {data['detected']:<9} | "
            f"{data['missed']:<7} | {rec_pct:>5.1f}%"
        )
    print("=" * 72)


def main() -> int:
    """CLI entry point."""
    parser = argparse.ArgumentParser(description="Evaluate B0 and B1 on DEV corpus split.")
    parser.add_argument(
        "--corpus-dir",
        type=Path,
        default=WORKSPACE_ROOT / "lab/ai_corpus",
        help="Path to AI corpus directory (default: lab/ai_corpus)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output raw JSON evaluation metrics",
    )
    args = parser.parse_args()

    results = evaluate_dev_split(args.corpus_dir)
    if args.json:
        print(json.dumps(results, indent=2))
    else:
        print_evaluation_report(results)

    return 0


if __name__ == "__main__":
    sys.exit(main())
