# SPDX-License-Identifier: MIT
"""Model check evaluation script for SEGEL release purpose inspection.

Evaluates qwen3:4b via loopback Ollama (http://127.0.0.1:11434) on the DEV split
per docs/ai_decisions.md (D11, D13, D14, D17, D19).
"""

from __future__ import annotations

import argparse
import contextlib
import hashlib
import json
import statistics
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(WORKSPACE_ROOT / "src"))
sys.path.insert(0, str(WORKSPACE_ROOT))

from inspector.ai.derive import (  # noqa: E402
    derive_ai_findings,
    derive_findings,
)
from inspector.baseline import BaselineV1  # noqa: E402
from inspector.policy.expectations import (  # noqa: E402
    classify_purpose_b1,
)
from scripts.ai_eval.guard import (  # noqa: E402
    get_corpus_files,
    guard_read_corpus_file,
)
from scripts.ai_eval.verify_corpus import (  # noqa: E402
    compute_diff_capabilities,
)

OLLAMA_BASE_URL = "http://127.0.0.1:11434"
MODEL_NAME = "qwen3:4b"

JSON_SCHEMA = {
    "type": "object",
    "properties": {
        "purpose_class": {
            "type": "string",
            "enum": ["L1", "L2", "L3", "L4", "L5", "L6"],
        },
        "ambiguous": {"type": "boolean"},
        "reason": {"type": "string"},
    },
    "required": ["purpose_class", "ambiguous", "reason"],
    "additionalProperties": False,
}

PROMPT_SYSTEM = (
    "You are a security release purpose classifier for the SEGEL release verification pipeline.\n"
    "Your task is to classify the declared release purpose into exactly one purpose class\n"
    "(L1 through L6), determine if it is ambiguous, and provide a brief Indonesian reason.\n\n"
    "The classes are:\n"
    "- L1 (DNS allowlist update): Updates, additions, or replacements of allowed DNS server\n"
    "  addresses or domain resolution endpoints (e.g., DNS resolver, forwarder, nameserver).\n"
    "- L2 (Operator account change): Creation, update, or provisioning of standard operator or\n"
    "  administrative maintenance user accounts (e.g., operator account, technician, profile).\n"
    "- L3 (Non-weakening logging adjustment): Configuration changes to logging destinations,\n"
    "  audit log targets, or logging parameters that do not disable logging (e.g., syslog).\n"
    "- L4 (Network rule addition): Outbound network firewall rule additions, upstream host\n"
    "  declarations, or egress routing updates (e.g., outbound firewall rule, egress port).\n"
    "- L5 (Hardening by disabling services): Hardening or attack-surface reduction actions\n"
    "  by explicitly disabling unneeded services or daemons (e.g., disable legacy services).\n"
    "- L6 (Vague or other): General, vague, ambiguous, or unclassified purposes that do not fall\n"
    "  cleanly into L1 through L5, or routine maintenance / parameter refresh without a domain.\n\n"
    "Guidelines:\n"
    "1. If the purpose clearly specifies an intended operational change matching one of L1..L5,\n"
    '   choose that class and set "ambiguous": false.\n'
    "2. If the purpose is broad, vague, routine maintenance, parameter refresh, or does not\n"
    '   clearly name a specific L1..L5 domain, choose "L6" and set "ambiguous": true.\n'
    '3. Provide a concise Indonesian reason in "reason".\n\n'
    "Few-shot Exemplars:\n"
    'Purpose: "Pembaruan alamat server resolusi nama domain kantor cabang"\n'
    'Output: {"purpose_class": "L1", "ambiguous": false, "reason": "Pembaruan alamat server '
    'resolusi nama domain berkaitan dengan pembaruan DNS allowlist (L1)."}\n\n'
    'Purpose: "Add outbound firewall egress rule for telemetry aggregation endpoint"\n'
    'Output: {"purpose_class": "L4", "ambiguous": false, "reason": "Menambahkan aturan egress '
    'firewall keluar merupakan penambahan aturan jaringan outbound (L4)."}\n\n'
    'Purpose: "Pembaruan berkala parameter sistem informasi gateway node"\n'
    'Output: {"purpose_class": "L6", "ambiguous": true, "reason": "Tujuan pembaruan parameter '
    'sistem informasi terlalu umum dan tidak spesifik ke kelas L1-L5 (L6)."}\n'
)

PROMPT_USER_TEMPLATE = 'Classify the following release purpose:\n"{purpose}"\n'


def check_ollama_health() -> bool:
    """Verify Ollama is reachable and MODEL_NAME is loaded."""
    url = f"{OLLAMA_BASE_URL}/api/tags"
    try:
        req = urllib.request.Request(url, method="GET")  # noqa: S310
        with urllib.request.urlopen(req, timeout=10) as resp:  # noqa: S310
            data = json.loads(resp.read().decode("utf-8"))
            models = [m.get("name") for m in data.get("models", [])]
            matched = any(
                m == MODEL_NAME or (m and m.startswith(f"{MODEL_NAME}:"))
                for m in models
            )
            if not matched:
                print(
                    f"ERROR: Model '{MODEL_NAME}' not found in Ollama models: {models}",
                    file=sys.stderr,
                )
                return False
            return True
    except Exception as exc:
        print(f"ERROR: Failed to reach Ollama at {url}: {exc}", file=sys.stderr)
        return False


def validate_schema(raw_content: str) -> tuple[bool, dict[str, Any] | None, str | None]:
    """Validate JSON output against JSON_SCHEMA."""
    try:
        data = json.loads(raw_content)
    except Exception as exc:
        return False, None, f"JSON parse error: {exc}"

    if not isinstance(data, dict):
        return False, None, "Output is not a JSON object"

    for field in ["purpose_class", "ambiguous", "reason"]:
        if field not in data:
            return False, None, f"Missing required field: {field}"

    if data["purpose_class"] not in {"L1", "L2", "L3", "L4", "L5", "L6"}:
        return False, None, f"Invalid purpose_class: {data['purpose_class']}"

    if not isinstance(data["ambiguous"], bool):
        return False, None, f"ambiguous is not boolean: {type(data['ambiguous'])}"

    if not isinstance(data["reason"], str):
        return False, None, f"reason is not string: {type(data['reason'])}"

    return True, data, None


def query_ollama(
    system_prompt: str,
    user_prompt: str,
    timeout: float = 30.0,
) -> dict[str, Any]:
    """Call Ollama /api/chat with D11 configuration."""
    url = f"{OLLAMA_BASE_URL}/api/chat"
    payload = {
        "model": MODEL_NAME,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "stream": False,
        "format": JSON_SCHEMA,
        "options": {
            "temperature": 0,
            "seed": 1,
            "num_ctx": 2048,
            "num_predict": 200,
        },
        "think": False,
        "keep_alive": "30m",
    }
    req = urllib.request.Request(  # noqa: S310
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310
        data = json.loads(resp.read().decode("utf-8"))
        if not isinstance(data, dict):
            raise ValueError("Ollama response is not a JSON dictionary")
        return data


def get_hardware_metrics() -> dict[str, Any]:
    """Capture ollama ps, psutil RAM, and nvidia-smi."""
    hw: dict[str, Any] = {}

    # ollama ps
    try:
        proc = subprocess.run(
            ["ollama", "ps"],  # noqa: S607
            capture_output=True,
            text=True,
            check=False,
            timeout=10,
        )
        hw["ollama_ps"] = proc.stdout.strip()
    except Exception as exc:
        hw["ollama_ps"] = f"UNKNOWN ({exc})"

    # peak RAM via psutil
    try:
        import psutil  # type: ignore

        hw["ram_total_gb"] = round(psutil.virtual_memory().total / (1024**3), 2)
        hw["ram_available_gb"] = round(
            psutil.virtual_memory().available / (1024**3), 2
        )
        hw["ram_status"] = "psutil installed"
    except ImportError:
        hw["ram_status"] = "skipped (psutil not installed)"

    # nvidia-smi
    try:
        proc = subprocess.run(
            ["nvidia-smi"],  # noqa: S607
            capture_output=True,
            text=True,
            check=False,
            timeout=10,
        )
        hw["nvidia_smi"] = proc.stdout.strip()
    except Exception as exc:
        hw["nvidia_smi"] = f"UNKNOWN ({exc})"

    return hw


def run_modelcheck(
    output_dir: Path | str = "docs/evaluation",
) -> dict[str, Any]:
    """Run model check evaluation on DEV split."""
    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    if not check_ollama_health():
        raise RuntimeError(f"Ollama health check failed for model {MODEL_NAME}")

    # Save exact prompt text
    prompt_file = out_path / "modelcheck_prompt.txt"
    full_prompt_text = (
        f"=== SYSTEM PROMPT ===\n{PROMPT_SYSTEM}\n\n"
        f"=== USER PROMPT TEMPLATE ===\n{PROMPT_USER_TEMPLATE}\n"
    )
    prompt_file.write_text(full_prompt_text, encoding="utf-8")
    prompt_sha256 = hashlib.sha256(full_prompt_text.encode("utf-8")).hexdigest()

    # Get DEV split files
    corpus_dir = WORKSPACE_ROOT / "lab" / "ai_corpus"
    corpus_files = get_corpus_files(corpus_dir, include_test=False)
    dev_files = [f for f in corpus_files if f.name.startswith("DEV-")]
    if len(dev_files) != 24:
        raise ValueError(f"Expected 24 DEV files, found {len(dev_files)}")

    # 1 warm-up call to prime Ollama context
    with contextlib.suppress(Exception):
        query_ollama(
            PROMPT_SYSTEM,
            PROMPT_USER_TEMPLATE.format(purpose="Warmup ping query"),
            timeout=30.0,
        )

    raw_items: list[dict[str, Any]] = []
    latencies: list[float] = []
    tok_speeds: list[float] = []

    for fpath in dev_files:
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

        user_content = PROMPT_USER_TEMPLATE.format(purpose=purpose)

        t_start = time.perf_counter()
        resp = query_ollama(PROMPT_SYSTEM, user_content, timeout=30.0)
        t_duration = time.perf_counter() - t_start
        latencies.append(t_duration)

        eval_count = resp.get("eval_count", 0)
        eval_duration = resp.get("eval_duration", 1)
        tok_speed = eval_count / (eval_duration / 1e9) if eval_duration > 0 else 0.0
        if tok_speed > 0:
            tok_speeds.append(tok_speed)

        msg_content = resp.get("message", {}).get("content", "")
        valid, parsed, err_msg = validate_schema(msg_content)

        ai_class = parsed.get("purpose_class") if (valid and parsed) else None
        ai_ambiguous = parsed.get("ambiguous") if (valid and parsed) else None
        ai_reason = parsed.get("reason") if (valid and parsed) else None

        # Code derivation for findings via single derivation module
        ai_findings = derive_ai_findings(ai_class, diff_kinds)
        ai_detected = len(ai_findings) > 0

        # Baseline B1
        b1_class = classify_purpose_b1(purpose)
        b1_findings = derive_findings(b1_class, diff_kinds)
        b1_detected = len(b1_findings) > 0

        b1_union_ai_detected = b1_detected or ai_detected

        raw_items.append({
            "id": item_id,
            "split": data["split"],
            "language": lang,
            "purpose": purpose,
            "expected_purpose_class": exp_class,
            "label": label,
            "mismatch_kind": mismatch_kind,
            "diff_kinds": sorted(diff_kinds),
            "raw_response": resp,
            "msg_content": msg_content,
            "schema_valid": valid,
            "schema_error": err_msg,
            "predicted_class": ai_class,
            "predicted_ambiguous": ai_ambiguous,
            "predicted_reason": ai_reason,
            "ai_findings": [f.model_dump() for f in ai_findings],
            "ai_detected": ai_detected,
            "b1_class": b1_class,
            "b1_detected": b1_detected,
            "b1_union_ai_detected": b1_union_ai_detected,
            "duration_s": round(t_duration, 4),
            "eval_count": eval_count,
            "tok_per_sec": round(tok_speed, 2),
        })

    # Save raw jsonl
    raw_file = out_path / "modelcheck_raw.jsonl"
    with raw_file.open("w", encoding="utf-8") as rf:
        for it in raw_items:
            rf.write(json.dumps(it, ensure_ascii=False) + "\n")

    # Metrics calculation
    total_count = len(raw_items)
    valid_count = sum(1 for it in raw_items if it["schema_valid"])
    schema_validity_rate = (valid_count / total_count) if total_count > 0 else 0.0

    # Purpose class accuracy overall
    correct_class_count = sum(
        1 for it in raw_items if it["predicted_class"] == it["expected_purpose_class"]
    )
    accuracy_overall = correct_class_count / total_count if total_count > 0 else 0.0

    # Accuracy per class
    classes = ["L1", "L2", "L3", "L4", "L5", "L6"]
    acc_per_class: dict[str, dict[str, Any]] = {}
    for c in classes:
        sub = [it for it in raw_items if it["expected_purpose_class"] == c]
        corr = sum(1 for it in sub if it["predicted_class"] == c)
        tot = len(sub)
        acc_per_class[c] = {
            "correct": corr,
            "total": tot,
            "accuracy": round(corr / tot, 4) if tot > 0 else 0.0,
        }

    # Accuracy per language
    languages = ["id", "en", "mixed"]
    acc_per_lang: dict[str, dict[str, Any]] = {}
    for lg in languages:
        sub = [it for it in raw_items if it["language"] == lg]
        corr = sum(1 for it in sub if it["predicted_class"] == it["expected_purpose_class"])
        tot = len(sub)
        acc_per_lang[lg] = {
            "correct": corr,
            "total": tot,
            "accuracy": round(corr / tot, 4) if tot > 0 else 0.0,
        }

    # Hard subset: DEV-14, DEV-17, DEV-18 plus any silent item B1 misses
    silent_items = [it for it in raw_items if it["mismatch_kind"] == "silent"]
    hard_ids = sorted(
        {"DEV-14", "DEV-17", "DEV-18"}
        | {it["id"] for it in silent_items if not it["b1_detected"]}
    )
    hard_sub = [it for it in raw_items if it["id"] in hard_ids]
    hard_correct = sum(
        1 for it in hard_sub if it["predicted_class"] == it["expected_purpose_class"]
    )
    hard_accuracy = (
        round(hard_correct / len(hard_sub), 4) if hard_sub else 0.0
    )

    # Silent DEV items detection
    # B1 alone vs B1 union AI
    silent_b1_alone = sum(1 for it in silent_items if it["b1_detected"])
    silent_b1_union_ai = sum(1 for it in silent_items if it["b1_union_ai_detected"])
    silent_ai_alone = sum(1 for it in silent_items if it["ai_detected"])

    # Consistent DEV items (12 items)
    consistent_items = [it for it in raw_items if it["label"] == "consistent"]
    fp_consistent = [it for it in consistent_items if it["ai_detected"]]
    fp_count = len(fp_consistent)

    # Latencies & tokens
    warm_median_lat = round(statistics.median(latencies), 3) if latencies else 0.0
    if len(latencies) >= 2:
        sorted_lats = sorted(latencies)
        idx_95 = int(0.95 * (len(sorted_lats) - 1))
        p95_lat = round(sorted_lats[idx_95], 3)
    else:
        p95_lat = warm_median_lat

    avg_tok_s = round(statistics.mean(tok_speeds), 2) if tok_speeds else 0.0

    # Hardware metrics
    hw_info = get_hardware_metrics()

    # D19 Decision Evaluation
    d19_cond1 = schema_validity_rate >= 0.95
    d19_cond2 = fp_count <= 2
    d19_cond3 = silent_b1_union_ai >= 6

    overall_pass = d19_cond1 and d19_cond2 and d19_cond3
    verdict_str = "PASS" if overall_pass else "FAIL"

    summary_file = out_path / "modelcheck_summary.txt"
    summary_lines = [
        f"VERDICT: {verdict_str}",
        f"D19 Decision Rule: {'PASSED' if overall_pass else 'FAILED'}",
        (
            f"  (1) Schema validity >= 95%: {schema_validity_rate * 100:.1f}% "
            f"({valid_count}/{total_count}) -> {d19_cond1}"
        ),
        (
            f"  (2) False positives on 12 consistent items <= 2: {fp_count}/12 "
            f"-> {d19_cond2}"
        ),
        (
            f"  (3) B1 union AI detects >= 6 of 7 silent items: {silent_b1_union_ai}/7 "
            f"(B1 alone: {silent_b1_alone}/7) -> {d19_cond3}"
        ),
        "",
        f"Prompt File: {prompt_file.name}",
        f"Prompt SHA-256: {prompt_sha256}",
        "",
        "=== PERFORMANCE METRICS ===",
        f"Total DEV Items: {total_count}",
        (
            f"Overall Purpose Accuracy: {accuracy_overall * 100:.1f}% "
            f"({correct_class_count}/{total_count})"
        ),
        (
            f"Hard Subset ({len(hard_sub)} items: {hard_ids}) Accuracy: "
            f"{hard_accuracy * 100:.1f}% ({hard_correct}/{len(hard_sub)})"
        ),
        "",
        "--- Accuracy by Class ---",
    ]
    for c in classes:
        ci = acc_per_class[c]
        summary_lines.append(
            f"  {c}: {ci['accuracy'] * 100:.1f}% ({ci['correct']}/{ci['total']})"
        )

    summary_lines.extend([
        "",
        "--- Accuracy by Language ---",
    ])
    for lg in languages:
        li = acc_per_lang[lg]
        summary_lines.append(
            f"  {lg:5}: {li['accuracy'] * 100:.1f}% ({li['correct']}/{li['total']})"
        )

    summary_lines.extend([
        "",
        "=== SILENT DEV ITEMS DETECTION (Total 7) ===",
        f"B1 alone detected:     {silent_b1_alone}/7",
        f"AI alone detected:     {silent_ai_alone}/7",
        f"B1 union AI detected:  {silent_b1_union_ai}/7",
        "",
        "=== CONSISTENT ITEMS FALSE POSITIVES (Total 12) ===",
        f"False Positives Count: {fp_count}/12",
    ])
    if fp_consistent:
        for fpi in fp_consistent:
            summary_lines.append(

                    f"  FP: {fpi['id']} (exp={fpi['expected_purpose_class']}, "
                    f"got={fpi['predicted_class']}) findings={fpi['ai_findings']}"

            )
    else:
        summary_lines.append("  (None: 0 false positives)")

    summary_lines.extend([
        "",
        "=== TIMING & HARDWARE ===",
        f"Warm Latency (Median): {warm_median_lat}s",
        f"Warm Latency (p95):    {p95_lat}s",
        f"Tokens per Second:     {avg_tok_s}",
        f"RAM Status:            {hw_info.get('ram_status')}",
        f"Ollama ps Status:      {hw_info.get('ollama_ps')}",
    ])

    summary_text = "\n".join(summary_lines) + "\n"
    summary_file.write_text(summary_text, encoding="utf-8")

    # Generate modelcheck.md
    md_file = out_path / "modelcheck.md"
    correct_items = [
        it for it in raw_items if it["predicted_class"] == it["expected_purpose_class"]
    ]
    wrong_items = [
        it for it in raw_items if it["predicted_class"] != it["expected_purpose_class"]
    ]

    md_lines = [
        "# Model Check Evaluation Report (AI-5)",
        "",
        f"**Verdict**: `{verdict_str}` (Decision D19: {'PASSED' if overall_pass else 'FAILED'})",
        "",
        "## 1. D19 Evaluation Decision Rule",
        "Per Decision D19 in `docs/ai_decisions.md`, model check evaluates:",
        (
            f"1. **Schema Validity**: {schema_validity_rate * 100:.1f}% "
            f"(Required: $\\ge 95\\%$) -> **{'PASS' if d19_cond1 else 'FAIL'}**"
        ),
        (
            f"2. **False Positives on 12 Consistent Items**: {fp_count} "
            f"(Required: $\\le 2$) -> **{'PASS' if d19_cond2 else 'FAIL'}**"
        ),
        (
            f"3. **Detection of 7 Silent Inconsistent Items**: B1 alone = {silent_b1_alone}/7; "
            f"B1 $\\cup$ AI = {silent_b1_union_ai}/7 (Required: $\\ge 6$) -> "
            f"**{'PASS' if d19_cond3 else 'FAIL'}**"
        ),
        "",
        "## 2. Methodology & Configuration",
        f"- **Model**: `{MODEL_NAME}` via Ollama at `{OLLAMA_BASE_URL}`",
        (
            "- **Inference Parameters (D11)**: temperature=0, seed=1, num_ctx=2048, "
            "num_predict=200, think=false, keep_alive=30m, timeout=30s"
        ),
        "- **Output Format**: JSON-schema constrained structured output + Python validator",
        (
            f"- **Prompt Template SHA-256**: `{prompt_sha256}` "
            "(saved in `docs/evaluation/modelcheck_prompt.txt`)"
        ),
        (
            "- **Evaluation Split**: DEV split only (24 items: 12 consistent, 12 inconsistent; "
            "7 silent, 5 deterministic). Test split guarded."
        ),
        "",
        "## 3. Summary Results Table",
        "| Metric | Value | Target / Requirement | Status |",
        "| :--- | :---: | :---: | :---: |",
        (
            f"| **D19 Overall Verdict** | **{verdict_str}** | PASS | "
            f"{'PASS' if overall_pass else 'FAIL'} |"
        ),
        (
            f"| Schema Validity Rate | {schema_validity_rate * 100:.1f}% "
            f"({valid_count}/{total_count}) | $\\ge 95\\%$ | "
            f"{'PASS' if d19_cond1 else 'FAIL'} |"
        ),
        (
            f"| Consistent False Positives | {fp_count} / 12 | $\\le 2$ | "
            f"{'PASS' if d19_cond2 else 'FAIL'} |"
        ),
        (
            f"| Silent Inconsistent Detection (B1 $\\cup$ AI) | {silent_b1_union_ai} / 7 | "
            f"$\\ge 6$ | {'PASS' if d19_cond3 else 'FAIL'} |"
        ),
        (
            f"| Silent Inconsistent Detection (B1 alone) | {silent_b1_alone} / 7 | "
            "Baseline reference | N/A |"
        ),
        (
            f"| Silent Inconsistent Detection (AI alone) | {silent_ai_alone} / 7 | "
            "Reference | N/A |"
        ),
        (
            f"| Overall Purpose-Class Accuracy | {accuracy_overall * 100:.1f}% "
            f"({correct_class_count}/{total_count}) | Indicative | N/A |"
        ),
        (
            f"| Hard Subset Accuracy | {hard_accuracy * 100:.1f}% "
            f"({hard_correct}/{len(hard_sub)}) | Indicative | N/A |"
        ),
        f"| Warm Latency (Median) | {warm_median_lat}s | Reference | N/A |",
        f"| Warm Latency (p95) | {p95_lat}s | Reference | N/A |",
        f"| Generation Speed | {avg_tok_s} tok/s | Reference | N/A |",
        "",
        "### Accuracy Breakdown by Class",
        "| Class | Name | Correct / Total | Accuracy |",
        "| :---: | :--- | :---: | :---: |",
    ]
    for c in classes:
        ci = acc_per_class[c]
        md_lines.append(f"| {c} | {ci['correct']} / {ci['total']} | {ci['accuracy'] * 100:.1f}% |")

    md_lines.extend([
        "",
        "### Accuracy Breakdown by Language",
        "| Language | Correct / Total | Accuracy |",
        "| :---: | :---: | :---: |",
    ])
    for lg in languages:
        li = acc_per_lang[lg]
        md_lines.append(
            f"| `{lg}` | {li['correct']} / {li['total']} | {li['accuracy'] * 100:.1f}% |"
        )

    md_lines.extend([
        "",
        "## 4. Hard Subset Breakdown",
        f"Hard subset items ({len(hard_sub)} items: {hard_ids}) missed by B1 alone:",
        "",
        "| ID | Lang | Stated Purpose | Expected | Predicted | AI Detected | B1 Union AI |",
        "| :--- | :---: | :--- | :---: | :---: | :---: | :---: |",
    ])
    for it in hard_sub:
        md_lines.append(

                f"| `{it['id']}` | `{it['language']}` | {it['purpose']} | "
                f"`{it['expected_purpose_class']}` | `{it['predicted_class']}` | "
                f"{it['ai_detected']} | {it['b1_union_ai_detected']} |"

        )

    md_lines.extend([
        "",
        "## 5. Sample Raw Outputs",
        "",
        "### 3 Correct Raw Outputs",
    ])
    for it in correct_items[:3]:
        md_lines.extend([
            (
                f"#### Item: `{it['id']}` (Expected: `{it['expected_purpose_class']}`, "
                f"Predicted: `{it['predicted_class']}`)"
            ),
            f"- **Purpose**: \"{it['purpose']}\"",
            "- **Raw Model Content**:",
            "```json",
            it["msg_content"],
            "```",
            f"- **Derived Findings**: `{it['ai_findings']}`",
            "",
        ])

    md_lines.append("### Sample Incorrect Raw Outputs (or Classification Deviations)")
    if wrong_items:
        for it in wrong_items[:3]:
            md_lines.extend([
                (
                    f"#### Item: `{it['id']}` (Expected: `{it['expected_purpose_class']}`, "
                    f"Predicted: `{it['predicted_class']}`)"
                ),
                f"- **Purpose**: \"{it['purpose']}\"",
                "- **Raw Model Content**:",
                "```json",
                it["msg_content"],
                "```",
                f"- **Derived Findings**: `{it['ai_findings']}`",
                "",
            ])
    else:
        md_lines.append("*(Zero misclassifications occurred: 24/24 exact class matches)*\n")

    md_lines.extend([
        "## 6. Hardware & Environment",
        "```text",
        f"Ollama ps:\n{hw_info.get('ollama_ps')}",
        "",
        f"RAM Status:\n{hw_info.get('ram_status')}",
        "",
        f"NVIDIA SMI:\n{hw_info.get('nvidia_smi')}",
        "```",
    ])

    md_file.write_text("\n".join(md_lines) + "\n", encoding="utf-8")

    return {
        "verdict": verdict_str,
        "pass": overall_pass,
        "schema_validity_rate": schema_validity_rate,
        "fp_count": fp_count,
        "silent_b1_alone": silent_b1_alone,
        "silent_b1_union_ai": silent_b1_union_ai,
        "accuracy_overall": accuracy_overall,
        "prompt_sha256": prompt_sha256,
        "raw_items": raw_items,
        "summary_file": str(summary_file),
        "raw_file": str(raw_file),
        "md_file": str(md_file),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="SEGEL AI Model Check")
    parser.add_argument(
        "--output-dir",
        default="docs/evaluation",
        help="Directory to save evaluation artifacts",
    )
    args = parser.parse_args()

    print("========================================================================")
    print("STARTING SEGEL AI MODEL CHECK (DEV SPLIT ONLY)")
    print("========================================================================")

    res = run_modelcheck(args.output_dir)

    print(f"VERDICT: {res['verdict']}")
    print(f"Schema validity: {res['schema_validity_rate'] * 100:.1f}%")
    print(f"False positives on consistent DEV items: {res['fp_count']}/12")
    print(
        f"Silent DEV detection: B1 alone = {res['silent_b1_alone']}/7, "
        f"B1 union AI = {res['silent_b1_union_ai']}/7"
    )
    print(f"Overall purpose accuracy: {res['accuracy_overall'] * 100:.1f}%")
    print(f"Prompt SHA-256: {res['prompt_sha256']}")
    print(f"Summary written to: {res['summary_file']}")
    print(f"Raw outputs written to: {res['raw_file']}")
    print(f"Markdown report written to: {res['md_file']}")
    print("========================================================================")

    if not res["pass"]:
        sys.exit(1)


if __name__ == "__main__":
    main()
