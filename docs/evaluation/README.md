# SEGEL AI Evaluation Index and Methodology

This directory contains empirical artifacts, raw records, prompts, and evaluation reports for the AI Inspector (`qwen3:4b`) evaluation suite.

---

## 1. Frozen Artifact Hashes

Hashes computed by script directly from freeze files:

| Target | File Path | File SHA-256 | Internal Target Digest |
| :--- | :--- | :--- | :--- |
| **Corpus Freeze File** | `docs/ai_corpus_freeze.txt` | `fe7e3f6e94efb2ae3ff922a5fba6765cb11b2183e4f881242184fca4c832b97a` | `dd57f76aa49f175d770dba2fca101d1e8b0f3f76bc8d4fd0c8151ff687d5f5ac` (test split concatenation) |
| **Prompt Freeze File** | `docs/ai_prompt_freeze.txt` | `2758f2ea31b8f51d830adcfa8156e1c667da66be19084a7148464f1e5339f597` | `1d4d6da9a11d5586af8111697fd591890bc6bf4d09970dc19a8fbb611226defc` (modelcheck prompt template) |

---

## 2. Evaluation Files Index

| File | Description | Generating Script | Generation Command |
| :--- | :--- | :--- | :--- |
| [`ai_report.md`](ai_report.md) | Official test-split evaluation report comparing B0, B1, B1b, AI alone, and B2. | `scripts/ai_eval/eval_test_split.py` | `SEGEL_ALLOW_TEST_EVAL=1 python scripts/ai_eval/eval_test_split.py` |
| [`testcheck_raw.jsonl`](testcheck_raw.jsonl) | Raw evaluation records for all 36 test split items (inputs, predictions, findings, latency). | `scripts/ai_eval/eval_test_split.py` | `SEGEL_ALLOW_TEST_EVAL=1 python scripts/ai_eval/eval_test_split.py` |
| [`latency.md`](latency.md) | Per-item latency distribution, tokens/s, >30s outliers, and failed item breakdown. | `scripts/ai_eval/generate_ai9a_docs.py` | `python scripts/ai_eval/generate_ai9a_docs.py` |
| [`injection_results.txt`](injection_results.txt) | Adversarial prompt injection results (12 cases across 4 attack categories). | `scripts/ai_eval/eval_injections.py` | `python scripts/ai_eval/eval_injections.py` |
| [`modelcheck_raw.jsonl`](modelcheck_raw.jsonl) | Raw evaluation records for all 24 DEV split items. | `scripts/ai_eval/modelcheck.py` | `python scripts/ai_eval/modelcheck.py` |
| [`modelcheck_summary.txt`](modelcheck_summary.txt) | High-level summary metrics for DEV split run. | `scripts/ai_eval/modelcheck.py` | `python scripts/ai_eval/modelcheck.py` |
| [`modelcheck_prompt.txt`](modelcheck_prompt.txt) | Exact system prompt and user template sent to `qwen3:4b`. | `scripts/ai_eval/modelcheck.py` | `python scripts/ai_eval/modelcheck.py` |
| [`modelcheck_table.tsv`](modelcheck_table.tsv) | TSV summary table of DEV split classifications and baseline detections. | `scripts/ai_eval/modelcheck_report.py` | `python scripts/ai_eval/modelcheck_report.py` |
| [`modelcheck_b1b.txt`](modelcheck_b1b.txt) | Detailed baseline B1b analysis on the DEV split. | `scripts/ai_eval/modelcheck_report.py` | `python scripts/ai_eval/modelcheck_report.py` |
| [`modelcheck.md`](modelcheck.md) | Markdown report of DEV split evaluation. | `scripts/ai_eval/modelcheck.py` | `python scripts/ai_eval/modelcheck.py` |
| [`prompt_history.md`](prompt_history.md) | Audit trail of prompt iterations and freeze confirmation. | Manual / Audit record | Authored during AI-4c audit pass |
| [`README.md`](README.md) | This index document. | `scripts/ai_eval/generate_ai9a_docs.py` | `python scripts/ai_eval/generate_ai9a_docs.py` |
