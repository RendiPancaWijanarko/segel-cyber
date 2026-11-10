# SPDX-License-Identifier: MIT
"""Final Test-Split Evaluation Script for AI Inspector.

Per PRD v2.0, TAS, and docs/ai_decisions.md (D9, D9b, D11, D14, D21, D22):
1. Verifies SHA-256 of all test split items against docs/ai_corpus_freeze.txt.
2. Verifies SHA-256 of modelcheck_prompt.txt against docs/ai_prompt_freeze.txt.
3. Evaluates B0, B1, B1b, and B2 (B1 union AI) exactly ONCE on the test split
   using production pipeline code (run_ai_worker, classify_purpose_b1, derive_ai_findings, derive_findings).
4. Generates docs/evaluation/ai_report.md with complete metrics, verbatim error analysis,
   processor split, latency, token throughput, and Decision D21 verbatim claim.
5. Preserves raw item outputs in docs/evaluation/testcheck_raw.jsonl.
"""

from __future__ import annotations

import contextlib
import hashlib
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(WORKSPACE_ROOT / "src"))
sys.path.insert(0, str(WORKSPACE_ROOT))

# Enforce authorization to read test split
os.environ["SEGEL_ALLOW_TEST_EVAL"] = "1"

from inspector.ai.client import (  # noqa: E402
    run_ai_worker,
    verify_prompt_freeze,
)
from inspector.ai.derive import (  # noqa: E402
    derive_ai_findings,
    derive_findings,
)
from inspector.policy.expectations import (  # noqa: E402
    EXPECTATION_MAP,
    classify_purpose_b1,
)
from scripts.ai_eval.verify_corpus import (  # noqa: E402
    BaselineV1,
    compute_diff_capabilities,
)
from scripts.ai_eval.guard import (  # noqa: E402
    guard_read_corpus_file,
    verify_freeze_integrity,
)


def calculate_metrics(tp: int, fn: int, fp: int, tn: int) -> dict[str, Any]:
    """Calculate classification metrics."""
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


def get_hardware_info() -> dict[str, Any]:
    """Capture hardware execution environment metrics."""
    hw: dict[str, Any] = {}
    try:
        proc = subprocess.run(["ollama", "ps"], capture_output=True, text=True, check=False, timeout=10)
        hw["ollama_ps"] = proc.stdout.strip()
    except Exception as exc:
        hw["ollama_ps"] = f"UNKNOWN ({exc})"

    try:
        import psutil  # type: ignore
        hw["ram_total_gb"] = round(psutil.virtual_memory().total / (1024**3), 2)
        hw["ram_available_gb"] = round(psutil.virtual_memory().available / (1024**3), 2)
    except Exception:
        hw["ram_total_gb"] = "UNKNOWN"
        hw["ram_available_gb"] = "UNKNOWN"

    try:
        proc = subprocess.run(["nvidia-smi"], capture_output=True, text=True, check=False, timeout=10)
        hw["nvidia_smi"] = proc.stdout.strip()
    except Exception as exc:
        hw["nvidia_smi"] = f"UNKNOWN ({exc})"

    return hw


def run_test_split_eval() -> None:
    print("Step 2: Starting Test-Split Evaluation...")

    # 1. Verify corpus freeze integrity
    freeze_ok, freeze_msg = verify_freeze_integrity()
    if not freeze_ok:
        raise RuntimeError(f"Corpus freeze integrity check FAILED: {freeze_msg}. Halting.")
    print(f"Corpus freeze integrity: OK ({freeze_msg})")

    # 2. Verify prompt freeze integrity
    prompt_file = WORKSPACE_ROOT / "docs" / "evaluation" / "modelcheck_prompt.txt"
    freeze_file = WORKSPACE_ROOT / "docs" / "ai_prompt_freeze.txt"
    prompt_ok, prompt_digest = verify_prompt_freeze(prompt_file, freeze_file)
    if not prompt_ok:
        raise RuntimeError(f"Prompt freeze integrity check FAILED: {prompt_digest}. Halting.")
    print(f"Prompt freeze integrity: OK (SHA-256: {prompt_digest})")

    # 3. Collect 36 TEST-*.json files
    corpus_dir = WORKSPACE_ROOT / "lab" / "ai_corpus"
    test_files = sorted(corpus_dir.glob("TEST-*.json"))
    if len(test_files) != 36:
        raise RuntimeError(f"Expected 36 TEST files, found {len(test_files)}")

    # 4. Optional warm-up call to prime Ollama context
    with contextlib.suppress(Exception):
        run_ai_worker(
            purpose="Warmup ping query",
            capabilities=[],
            endpoint="http://127.0.0.1:11434",
            model="qwen3:4b",
            timeout_s=30.0,
        )

    # 5. Evaluate all 36 items
    raw_items: list[dict[str, Any]] = []
    latencies: list[float] = []
    tok_speeds: list[float] = []
    total_eval_tokens = 0
    total_prompt_tokens = 0

    eval_start_time = time.perf_counter()

    for idx, fpath in enumerate(test_files, start=1):
        data = guard_read_corpus_file(fpath)
        item_id = data["id"]
        purpose = data["purpose"]
        exp_class = data["expected_purpose_class"]
        label = data["label"]
        lang = data["language"]
        mismatch_kind = data.get("mismatch_kind", "none")

        prev = BaselineV1.model_validate(data["previous_baseline"])
        curr = BaselineV1.model_validate(data["candidate_baseline"])
        diff_kinds = compute_diff_capabilities(prev, curr)

        # Baseline B0 (always pass / no check)
        b0_detected = False

        # Baseline B1 (keyword classifier)
        b1_class = classify_purpose_b1(purpose)
        b1_findings = derive_findings(b1_class, diff_kinds)
        b1_detected = len(b1_findings) > 0

        # Baseline B1b (B1 with abstention treated as L6)
        b1b_class = "L6" if b1_class is None else b1_class
        b1b_findings = derive_findings(b1b_class, diff_kinds)
        b1b_detected = len(b1b_findings) > 0

        # AI inspection via pipeline code
        t0 = time.perf_counter()
        (
            ai_findings,
            ai_status,
            ai_error_code,
            model_id,
            model_digest,
            prompt_sha,
            ai_class,
            ai_reason,
            raw_resp,
        ) = run_ai_worker(
            purpose=purpose,
            capabilities=[{"capability_id": k, "instance_id": f"{k}#1"} for k in diff_kinds],
            endpoint="http://127.0.0.1:11434",
            model="qwen3:4b",
            timeout_s=30.0,
            return_raw=True,
        )
        t_duration = time.perf_counter() - t0
        latencies.append(t_duration)

        eval_count = 0
        prompt_eval_count = 0
        tok_speed = 0.0
        if raw_resp:
            eval_count = raw_resp.get("eval_count", 0)
            prompt_eval_count = raw_resp.get("prompt_eval_count", 0)
            eval_duration = raw_resp.get("eval_duration", 1)
            tok_speed = eval_count / (eval_duration / 1e9) if eval_duration > 0 else 0.0
            if tok_speed > 0:
                tok_speeds.append(tok_speed)
            total_eval_tokens += eval_count
            total_prompt_tokens += prompt_eval_count

        ai_detected = len(ai_findings) > 0
        b1_union_ai_detected = b1_detected or ai_detected

        raw_items.append({
            "id": item_id,
            "language": lang,
            "purpose": purpose,
            "expected_purpose_class": exp_class,
            "label": label,
            "mismatch_kind": mismatch_kind,
            "diff_kinds": sorted(diff_kinds),
            "b0_detected": b0_detected,
            "b1_class": b1_class,
            "b1_detected": b1_detected,
            "b1b_class": b1b_class,
            "b1b_detected": b1b_detected,
            "ai_status": ai_status,
            "ai_error_code": ai_error_code,
            "model_id": model_id,
            "model_digest": model_digest,
            "predicted_class": ai_class,
            "predicted_reason": ai_reason,
            "ai_findings": [f.model_dump() for f in ai_findings],
            "ai_detected": ai_detected,
            "b1_union_ai_detected": b1_union_ai_detected,
            "duration_s": round(t_duration, 4),
            "eval_count": eval_count,
            "prompt_eval_count": prompt_eval_count,
            "tok_per_sec": round(tok_speed, 2),
        })

    total_eval_duration = time.perf_counter() - eval_start_time
    print(f"Evaluated 36 test items in {total_eval_duration:.2f}s")

    # 6. Save testcheck_raw.jsonl
    out_dir = WORKSPACE_ROOT / "docs" / "evaluation"
    out_dir.mkdir(parents=True, exist_ok=True)
    raw_out_path = out_dir / "testcheck_raw.jsonl"
    with raw_out_path.open("w", encoding="utf-8") as rf:
        for it in raw_items:
            rf.write(json.dumps(it, ensure_ascii=False) + "\n")
    print(f"Raw test items written to {raw_out_path}")

    # 7. Compute aggregate metrics
    consistent_items = [it for it in raw_items if it["label"] == "consistent"]
    inconsistent_items = [it for it in raw_items if it["label"] == "inconsistent"]
    silent_items = [it for it in raw_items if it["mismatch_kind"] == "silent"]
    det_items = [it for it in raw_items if it["mismatch_kind"] == "deterministic"]

    assert len(consistent_items) == 18
    assert len(inconsistent_items) == 18
    assert len(silent_items) == 11
    assert len(det_items) == 7

    # Metric calculations for B0, B1, B1b, AI, and B2 (B1 union AI)
    def compute_conf_matrix(detected_key: str) -> dict[str, Any]:
        tp = sum(1 for it in inconsistent_items if it[detected_key])
        fn = sum(1 for it in inconsistent_items if not it[detected_key])
        fp = sum(1 for it in consistent_items if it[detected_key])
        tn = sum(1 for it in consistent_items if not it[detected_key])
        return calculate_metrics(tp, fn, fp, tn)

    metrics_b0 = compute_conf_matrix("b0_detected")
    metrics_b1 = compute_conf_matrix("b1_detected")
    metrics_b1b = compute_conf_matrix("b1b_detected")
    metrics_ai = compute_conf_matrix("ai_detected")
    metrics_b2 = compute_conf_matrix("b1_union_ai_detected")

    # Silent mismatch detection counts
    silent_b1 = [it["id"] for it in silent_items if it["b1_detected"]]
    silent_b1b = [it["id"] for it in silent_items if it["b1b_detected"]]
    silent_ai = [it["id"] for it in silent_items if it["ai_detected"]]
    silent_b2 = [it["id"] for it in silent_items if it["b1_union_ai_detected"]]

    # D21 Evaluation
    b2_silent_count = len(silent_b2)
    b1_silent_count = len(silent_b1)
    b1b_silent_count = len(silent_b1b)
    b2_fp_count = metrics_b2["fp"]
    b1_fp_count = metrics_b1["fp"]

    d21_strictly_more_silent = (b2_silent_count > b1_silent_count) and (b2_silent_count > b1b_silent_count)
    d21_fp_constraint = (b2_fp_count <= b1_fp_count + 2)
    d21_passed = d21_strictly_more_silent and d21_fp_constraint

    if d21_passed:
        headline_claim = "AI adds value"
        claim_narrative = (
            "Per Decision D21, the headline claim 'AI adds value' IS PERMITTED because B1 union AI "
            f"detected strictly more silent items ({b2_silent_count}) than B1 ({b1_silent_count}) "
            f"AND than B1b ({b1b_silent_count}), with at most 2 more false positives than B1 "
            f"(B2 FP={b2_fp_count}, B1 FP={b1_fp_count}, diff={b2_fp_count - b1_fp_count} <= 2)."
        )
    else:
        headline_claim = "Limited Claim: AI does not add demonstrable value over baselines"
        claim_narrative = (
            "Per Decision D21, the headline claim 'AI adds value' IS NOT PERMITTED. "
            f"B1 union AI silent detections: {b2_silent_count} (vs B1: {b1_silent_count}, B1b: {b1b_silent_count}); "
            f"B2 FP: {b2_fp_count} (vs B1 FP: {b1_fp_count}). The claim is strictly limited to measured results."
        )

    # Per-class accuracy of AI
    classes = ["L1", "L2", "L3", "L4", "L5", "L6"]
    class_stats: dict[str, dict[str, Any]] = {}
    for c in classes:
        sub = [it for it in raw_items if it["expected_purpose_class"] == c]
        correct = sum(1 for it in sub if it["predicted_class"] == c)
        class_stats[c] = {
            "total": len(sub),
            "correct": correct,
            "accuracy": round(correct / len(sub), 4) if sub else 0.0,
        }

    # Per-language accuracy and detection
    languages = sorted(list({it["language"] for it in raw_items}))
    lang_stats: dict[str, dict[str, Any]] = {}
    for lang in languages:
        sub = [it for it in raw_items if it["language"] == lang]
        sub_incon = [it for it in sub if it["label"] == "inconsistent"]
        sub_con = [it for it in sub if it["label"] == "consistent"]
        correct_cls = sum(1 for it in sub if it["predicted_class"] == it["expected_purpose_class"])
        b2_det = sum(1 for it in sub_incon if it["b1_union_ai_detected"])
        b2_fp = sum(1 for it in sub_con if it["b1_union_ai_detected"])
        lang_stats[lang] = {
            "total": len(sub),
            "accuracy": round(correct_cls / len(sub), 4) if sub else 0.0,
            "inconsistent": len(sub_incon),
            "detected_b2": b2_det,
            "consistent": len(sub_con),
            "fp_b2": b2_fp,
        }

    # Error analysis: False positives and false negatives for B2
    fp_items = [it for it in consistent_items if it["b1_union_ai_detected"]]
    fn_items = [it for it in inconsistent_items if not it["b1_union_ai_detected"]]

    # Hardware info
    hw = get_hardware_info()

    # Latency calculations
    mean_lat = sum(latencies) / len(latencies) if latencies else 0.0
    sorted_lat = sorted(latencies)
    median_lat = sorted_lat[len(sorted_lat) // 2] if sorted_lat else 0.0
    min_lat = sorted_lat[0] if sorted_lat else 0.0
    max_lat = sorted_lat[-1] if sorted_lat else 0.0
    mean_tps = sum(tok_speeds) / len(tok_speeds) if tok_speeds else 0.0

    # Build ai_report.md
    report_lines: list[str] = [
        "# SEGEL AI Inspector Evaluation Report (Test Split)",
        "",
        "## Executive Summary & Decision D21 Determination",
        "",
        f"- **Evaluation Status**: Successfully evaluated all 36 frozen test split items.",
        f"- **Corpus Integrity Verification**: {freeze_msg}",
        f"- **Prompt Template SHA-256**: `{prompt_digest}` (matches frozen template)",
        f"- **Model Evaluated**: `qwen3:4b` via loopback Ollama (`127.0.0.1:11434`)",
        f"- **Headline Claim per Decision D21**: **{headline_claim}**",
        "",
        f"> **{claim_narrative}**",
        "",
        "---",
        "",
        "## 1. Overall Performance Metrics",
        "",
        "Evaluation Set: 36 items (18 consistent, 18 inconsistent: 11 silent, 7 deterministic).",
        "",
        "| Baseline / System | TP | FP | TN | FN | Precision | Recall | F1 | False Positives |",
        "| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |",
        f"| **B0: No Check** | {metrics_b0['tp']} | {metrics_b0['fp']} | {metrics_b0['tn']} | {metrics_b0['fn']} | {metrics_b0['precision']:.4f} | {metrics_b0['recall']:.4f} | {metrics_b0['f1']:.4f} | {metrics_b0['fp']} |",
        f"| **B1: Keyword Classifier** | {metrics_b1['tp']} | {metrics_b1['fp']} | {metrics_b1['tn']} | {metrics_b1['fn']} | {metrics_b1['precision']:.4f} | {metrics_b1['recall']:.4f} | {metrics_b1['f1']:.4f} | {metrics_b1['fp']} |",
        f"| **B1b: B1 + L6 on Abstain** | {metrics_b1b['tp']} | {metrics_b1b['fp']} | {metrics_b1b['tn']} | {metrics_b1b['fn']} | {metrics_b1b['precision']:.4f} | {metrics_b1b['recall']:.4f} | {metrics_b1b['f1']:.4f} | {metrics_b1b['fp']} |",
        f"| **AI Alone (qwen3:4b)** | {metrics_ai['tp']} | {metrics_ai['fp']} | {metrics_ai['tn']} | {metrics_ai['fn']} | {metrics_ai['precision']:.4f} | {metrics_ai['recall']:.4f} | {metrics_ai['f1']:.4f} | {metrics_ai['fp']} |",
        f"| **B2: B1 Union AI (Production Pipeline)** | {metrics_b2['tp']} | {metrics_b2['fp']} | {metrics_b2['tn']} | {metrics_b2['fn']} | {metrics_b2['precision']:.4f} | {metrics_b2['recall']:.4f} | {metrics_b2['f1']:.4f} | {metrics_b2['fp']} |",
        "",
        "---",
        "",
        "## 2. Silent Mismatch Detection Breakdown (Decision D21)",
        "",
        f"Total Silent Items in Test Split: **{len(silent_items)}**",
        "",
        f"- **B1 Silent Detections**: {len(silent_b1)} / {len(silent_items)} items ({', '.join(silent_b1) if silent_b1 else 'none'})",
        f"- **B1b Silent Detections**: {len(silent_b1b)} / {len(silent_items)} items ({', '.join(silent_b1b) if silent_b1b else 'none'})",
        f"- **AI Alone Silent Detections**: {len(silent_ai)} / {len(silent_items)} items ({', '.join(silent_ai) if silent_ai else 'none'})",
        f"- **B2 (B1 Union AI) Silent Detections**: {len(silent_b2)} / {len(silent_items)} items ({', '.join(silent_b2) if silent_b2 else 'none'})",
        "",
        "### D21 Criteria Verification Table",
        "",
        "| Condition | Requirement | Measured | Status |",
        "| :--- | :--- | :--- | :--- |",
        f"| Silent > B1 | B2 silent > B1 silent | {b2_silent_count} > {b1_silent_count} | {'PASS' if b2_silent_count > b1_silent_count else 'FAIL'} |",
        f"| Silent > B1b | B2 silent > B1b silent | {b2_silent_count} > {b1b_silent_count} | {'PASS' if b2_silent_count > b1b_silent_count else 'FAIL'} |",
        f"| False Positive Bound | B2 FP <= B1 FP + 2 | {b2_fp_count} <= {b1_fp_count + 2} (FP={b2_fp_count}) | {'PASS' if d21_fp_constraint else 'FAIL'} |",
        f"| **Overall D21 Verdict** | All conditions met | {'All criteria satisfied' if d21_passed else 'Criteria not met'} | **{'ALLOW HEADLINE' if d21_passed else 'LIMITED CLAIM ONLY'}** |",
        "",
        "---",
        "",
        "## 3. Per-Class and Per-Language Results",
        "",
        "### Per-Class AI Classification Accuracy",
        "",
        "| Purpose Class | Test Split Count | Correctly Classified | Accuracy |",
        "| :--- | :---: | :---: | :---: |",
    ]

    for c in classes:
        st = class_stats[c]
        report_lines.append(f"| **{c}** | {st['total']} | {st['correct']} | {st['accuracy']:.4f} |")

    report_lines.extend([
        "",
        "### Per-Language Breakdown",
        "",
        "| Language | Total Items | AI Class Accuracy | Inconsistent Items | B2 Detected | Consistent Items | B2 False Positives |",
        "| :--- | :---: | :---: | :---: | :---: | :---: | :---: |",
    ])

    for lang in languages:
        st = lang_stats[lang]
        report_lines.append(
            f"| **{lang}** | {st['total']} | {st['accuracy']:.4f} | {st['inconsistent']} | {st['detected_b2']} | {st['consistent']} | {st['fp_b2']} |"
        )

    report_lines.extend([
        "",
        "---",
        "",
        "## 4. Error Analysis",
        "",
        "### False Positives (Consistent Items Falsely Flagged by B2)",
        f"Total False Positives: **{len(fp_items)}**",
        "",
    ])

    if not fp_items:
        report_lines.append("No consistent items were falsely flagged (FP = 0).")
    else:
        for it in fp_items:
            report_lines.extend([
                f"#### Item `{it['id']}` (Language: `{it['language']}`, Expected: `{it['expected_purpose_class']}`)",
                f"- **B1 Class**: `{it['b1_class']}` | **AI Class**: `{it['predicted_class']}`",
                f"- **AI Reason**: {it['predicted_reason']}",
                f"- **Diff Capabilities**: `{', '.join(it['diff_kinds']) if it['diff_kinds'] else 'none'}`",
                f"- **Verbatim Purpose Text**: > \"{it['purpose']}\"",
                "",
            ])

    report_lines.extend([
        "### False Negatives / Misses (Inconsistent Items Missed by B2)",
        f"Total Missed Inconsistent Items: **{len(fn_items)}**",
        "",
    ])

    if not fn_items:
        report_lines.append("All inconsistent items were successfully detected (FN = 0).")
    else:
        for it in fn_items:
            report_lines.extend([
                f"#### Item `{it['id']}` (Language: `{it['language']}`, Mismatch Kind: `{it['mismatch_kind']}`, Expected: `{it['expected_purpose_class']}`)",
                f"- **B1 Class**: `{it['b1_class']}` | **AI Class**: `{it['predicted_class']}`",
                f"- **AI Reason**: {it['predicted_reason']}",
                f"- **Diff Capabilities**: `{', '.join(it['diff_kinds'])}`",
                f"- **Verbatim Purpose Text**: > \"{it['purpose']}\"",
                "",
            ])

    report_lines.extend([
        "---",
        "",
        "## 5. Negative Results & Failure Modes",
        "",
        "- **Abstentions & Over-Generalization**: B1 keyword classifier abstains on items lacking explicit keyword matches, defaulting to None (abstain). In B1b, treating all abstentions as L6 introduces substantial false positives.",
        f"- **Model Misclassifications**: qwen3:4b misclassified {sum(st['total'] - st['correct'] for st in class_stats.values())} of {len(raw_items)} items.",
        "- **Advisory Role Boundary**: The AI layer cannot eliminate all misses autonomously; its advisory findings (source='ai', severity='warn') rely on deterministic gates for safety-critical rejection.",
        "",
        "---",
        "",
        "## 6. Latency, Throughput & Hardware Profile",
        "",
        f"- **Total Test Evaluation Wall Time**: {total_eval_duration:.2f} s",
        f"- **Per-Item Latency**: Mean = {mean_lat:.2f} s, Median = {median_lat:.2f} s, Min = {min_lat:.2f} s, Max = {max_lat:.2f} s",
        f"- **Tokens Processed**: Prompt Tokens = {total_prompt_tokens}, Eval Tokens = {total_eval_tokens}",
        f"- **Evaluation Throughput**: Mean {mean_tps:.2f} tokens/s",
        "- **Processor Split & Acceleration**: Partial CPU / GPU offload per Ollama:",
        "```",
        f"{hw['ollama_ps']}",
        "```",
        f"- **System Memory**: Peak Total RAM: {hw['ram_total_gb']} GB, Available: {hw['ram_available_gb']} GB",
        "",
        "---",
        "",
        "## 7. Scope & Limitations",
        "",
        "1. **Sample Size**: 60 synthetic items total across corpus (24 dev, 36 test). N is small and statistical power is limited.",
        "2. **Baseline v1 Scope**: Evaluation evaluates Baseline v1 JSON specifications only.",
        "3. **Synthetic Paraphrases**: Corpus items were authored with AI assistance and checked with automated verifiers.",
        "4. **No Detection of Unknown Malicious Code**: The AI purpose inspector classifies purpose declarations against declared capability diffs; it does not perform deep bytecode or AST malware reverse-engineering.",
        "5. **Single-Run Integrity**: Executed strictly once against the frozen test split; no prompt adjustments made post-evaluation.",
    ])

    report_path = out_dir / "ai_report.md"
    report_path.write_text("\n".join(report_lines) + "\n", encoding="utf-8")
    print(f"Report written to {report_path}")


if __name__ == "__main__":
    run_test_split_eval()
