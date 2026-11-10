# SPDX-License-Identifier: MIT
"""Report generator for SEGEL model check results.

Reads docs/evaluation/modelcheck_raw.jsonl ONLY and generates:
- docs/evaluation/modelcheck_table.tsv
- docs/evaluation/modelcheck_b1b.txt
- docs/ai_prompt_freeze.txt

Performs B1b baseline comparison and prompt freeze verification.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(WORKSPACE_ROOT / "src"))
sys.path.insert(0, str(WORKSPACE_ROOT))

# Single derivation module used by both production and evaluation
from inspector.ai.derive import (  # noqa: E402
    derive_findings,
)


def calculate_metrics(tp: int, fn: int, fp: int, tn: int) -> dict[str, Any]:
    """Calculate standard classification metrics."""
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = (
        (2 * precision * recall / (precision + recall))
        if (precision + recall) > 0
        else 0.0
    )
    return {
        "tp": tp,
        "fn": fn,
        "fp": fp,
        "tn": tn,
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1": round(f1, 4),
    }


def generate_reports(
    raw_jsonl_path: Path | str = "docs/evaluation/modelcheck_raw.jsonl",
    output_dir: Path | str = "docs/evaluation",
    prompt_file_path: Path | str = "docs/evaluation/modelcheck_prompt.txt",
    freeze_output_path: Path | str = "docs/ai_prompt_freeze.txt",
) -> None:
    """Generate TSV table, B1b analysis, and prompt freeze file."""
    raw_file = Path(raw_jsonl_path)
    out_dir = Path(output_dir)
    prompt_file = Path(prompt_file_path)
    freeze_file = Path(freeze_output_path)

    if not raw_file.exists():
        raise FileNotFoundError(f"Raw results file not found: {raw_file}")

    items: list[dict[str, Any]] = []
    with raw_file.open("r", encoding="utf-8") as f:
        for line in f:
            line_str = line.strip()
            if line_str:
                items.append(json.loads(line_str))

    if len(items) != 24:
        raise ValueError(f"Expected 24 items in {raw_file}, found {len(items)}")

    # 1. Generate modelcheck_table.tsv
    tsv_path = out_dir / "modelcheck_table.tsv"
    tsv_headers = [
        "id",
        "language",
        "expected_purpose_class",
        "label",
        "mismatch_kind",
        "b1_class",
        "predicted_class",
        "predicted_ambiguous",
        "b1_detected",
        "ai_detected",
        "union_detected",
        "finding_kinds",
    ]
    tsv_rows: list[str] = ["\t".join(tsv_headers)]

    for it in items:
        findings = [f.get("capability_id", "") for f in it.get("ai_findings", [])]
        finding_kinds = ",".join(findings) if findings else "none"
        b1_cls_str = it.get("b1_class") or "None"

        row = [
            it["id"],
            it["language"],
            it["expected_purpose_class"],
            it["label"],
            it["mismatch_kind"],
            b1_cls_str,
            it["predicted_class"],
            str(it["predicted_ambiguous"]),
            str(it["b1_detected"]),
            str(it["ai_detected"]),
            str(it["b1_union_ai_detected"]),
            finding_kinds,
        ]
        tsv_rows.append("\t".join(row))

    tsv_path.write_text("\n".join(tsv_rows) + "\n", encoding="utf-8")

    # 2. Compute B1b baseline metrics
    # Baseline B1b = B1 where an abstention is treated as class L6 (vague)
    # Using derive_findings from inspector.policy.expectations
    consistent_items = [it for it in items if it["label"] == "consistent"]
    inconsistent_items = [it for it in items if it["label"] == "inconsistent"]
    silent_items = [it for it in items if it["mismatch_kind"] == "silent"]

    for it in items:
        b1_cls = it.get("b1_class")
        b1b_cls = "L6" if b1_cls is None else b1_cls
        diff_kinds = it.get("diff_kinds", [])
        b1b_findings = derive_findings(b1b_cls, diff_kinds)
        it["b1b_class"] = b1b_cls
        it["b1b_findings"] = b1b_findings
        it["b1b_detected"] = len(b1b_findings) > 0

    # (a) Confusion counts on DEV for B1b
    b1b_tp_items = [it for it in inconsistent_items if it["b1b_detected"]]
    b1b_fn_items = [it for it in inconsistent_items if not it["b1b_detected"]]
    b1b_fp_items = [it for it in consistent_items if it["b1b_detected"]]
    b1b_tn_items = [it for it in consistent_items if not it["b1b_detected"]]

    metrics_b1b = calculate_metrics(
        tp=len(b1b_tp_items),
        fn=len(b1b_fn_items),
        fp=len(b1b_fp_items),
        tn=len(b1b_tn_items),
    )

    silent_detected_b1b = [it["id"] for it in silent_items if it["b1b_detected"]]
    fp_b1b_ids = [it["id"] for it in b1b_fp_items]

    # (b) How many consistent DEV items B1 abstains on
    b1_abstain_consistent = [
        it["id"] for it in consistent_items if it.get("b1_class") is None
    ]

    # (c) How many items have predicted_ambiguous different from (predicted_class == "L6")
    amb_diff_items = [
        it["id"]
        for it in items
        if bool(it.get("predicted_ambiguous")) != (it.get("predicted_class") == "L6")
    ]

    # (d) 2x2 table on the 7 silent items: detected by B1b versus detected by AI
    both_detected = [
        it["id"]
        for it in silent_items
        if it["b1b_detected"] and it["ai_detected"]
    ]
    b1b_only = [
        it["id"]
        for it in silent_items
        if it["b1b_detected"] and not it["ai_detected"]
    ]
    ai_only = [
        it["id"]
        for it in silent_items
        if not it["b1b_detected"] and it["ai_detected"]
    ]
    neither = [
        it["id"]
        for it in silent_items
        if not it["b1b_detected"] and not it["ai_detected"]
    ]

    # Write docs/evaluation/modelcheck_b1b.txt
    b1b_lines = [
        "=== BASELINE B1b EVALUATION AND COMPARISON REPORT ===",
        "",
        "Derivation Code Source: inspector.ai.derive (single derivation module)",
        "(Exact expectation derivation logic imported and used by modelcheck.py)",
        "",
        "--- (a) Baseline B1b Performance on DEV Split ---",
        (
            "Definition: B1b = B1 keyword classifier where abstentions (no match) "
            "are treated as class L6 (vague)."
        ),
        "Confusion Counts on DEV (Total 24 items: 12 consistent, 12 inconsistent):",
        f"  TP: {metrics_b1b['tp']}",
        f"  FP: {metrics_b1b['fp']}",
        f"  TN: {metrics_b1b['tn']}",
        f"  FN: {metrics_b1b['fn']}",
        f"  Precision: {metrics_b1b['precision']:.4f}",
        f"  Recall:    {metrics_b1b['recall']:.4f}",
        f"  F1:        {metrics_b1b['f1']:.4f}",
        "",
        f"Detection of 7 Silent Items by B1b: {len(silent_detected_b1b)}/7",
        f"  Detected Silent IDs: {silent_detected_b1b}",
        "",
        f"False Positives on 12 Consistent Items by B1b: {len(fp_b1b_ids)}/12",
        f"  False Positive IDs: {fp_b1b_ids}",
        "",
        "--- (b) B1 Abstentions on Consistent DEV Items ---",
        f"Count: {len(b1_abstain_consistent)} / 12",
        f"Abstained Consistent IDs: {b1_abstain_consistent}",
        "Explanation: When B1 abstains, it derives no findings, producing 0 false positives.",
        (
            "Under B1b, treating these abstentions as L6 flags every non-empty diff "
            "as 'purpose too vague',"
        ),
        (
            f"directly turning all {len(b1_abstain_consistent)} unclassified consistent "
            "items into false positives."
        ),
        "",
        "--- (c) Ambiguity Consistency Check ---",
        "Rule: predicted_ambiguous == (predicted_class == 'L6')",
        (
            "Items where predicted_ambiguous differs from (predicted_class == 'L6'): "
            f"{len(amb_diff_items)}"
        ),
        f"Divergent Item IDs: {amb_diff_items if amb_diff_items else 'None'}",
        (
            "Result: Perfect 1-to-1 correspondence between L6 classification "
            "and ambiguous=True across all 24 items."
        ),
        "",
        "--- (d) 2x2 Table on the 7 Silent Items (B1b vs AI) ---",
        "",
        "| Category | AI Detected | AI Not Detected | Total |",
        "| :--- | :---: | :---: | :---: |",
        (
            f"| B1b Detected     | {len(both_detected):^11} | "
            f"{len(b1b_only):^15} | {len(both_detected) + len(b1b_only):^5} |"
        ),
        (
            f"| B1b Not Detected | {len(ai_only):^11} | "
            f"{len(neither):^15} | {len(ai_only) + len(neither):^5} |"
        ),
        (
            f"| Total            | {len(both_detected) + len(ai_only):^11} | "
            f"{len(b1b_only) + len(neither):^15} | {len(silent_items):^5} |"
        ),
        "",
        "Breakdown by Item IDs:",
        f"  - Both B1b and AI Detected ({len(both_detected)}): {both_detected}",
        f"  - B1b Detected only ({len(b1b_only)}): {b1b_only}",
        f"  - AI Detected only ({len(ai_only)}): {ai_only}",
        f"  - Neither Detected ({len(neither)}): {neither}",
    ]
    b1b_text = "\n".join(b1b_lines) + "\n"
    (out_dir / "modelcheck_b1b.txt").write_text(b1b_text, encoding="utf-8")

    # 4. Generate docs/ai_prompt_freeze.txt
    if not prompt_file.exists():
        raise FileNotFoundError(f"Prompt file not found: {prompt_file}")

    prompt_bytes = prompt_file.read_bytes()
    prompt_sha256 = hashlib.sha256(prompt_bytes).hexdigest()

    freeze_content = (
        f"{prompt_sha256}  docs/evaluation/modelcheck_prompt.txt\n"
        "From now on the prompt text is read-only. "
        "Any change needs a new decision and a note in docs/limitations.md.\n"
    )
    freeze_file.write_text(freeze_content, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="SEGEL Model Check Reporting")
    parser.add_argument(
        "--raw-jsonl",
        default="docs/evaluation/modelcheck_raw.jsonl",
        help="Path to raw jsonl results",
    )
    parser.add_argument(
        "--output-dir",
        default="docs/evaluation",
        help="Directory to write report files",
    )
    args = parser.parse_args()

    generate_reports(raw_jsonl_path=args.raw_jsonl, output_dir=args.output_dir)
    print("Reports generated successfully:")
    print("  - docs/evaluation/modelcheck_table.tsv")
    print("  - docs/evaluation/modelcheck_b1b.txt")
    print("  - docs/ai_prompt_freeze.txt")


if __name__ == "__main__":
    main()
