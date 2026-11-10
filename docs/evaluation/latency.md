# SEGEL AI Evaluation Latency and Throughput Statistics

## 1. Overview and Source Files

This document records empirical per-item duration and token throughput statistics computed directly from raw evaluation records:
- Development Split: `docs/evaluation/modelcheck_raw.jsonl` (N = 24)
- Test Split: `docs/evaluation/testcheck_raw.jsonl` (N = 36)

---

## 2. Per-Item Duration Statistics

| Evaluation Split | Items Evaluated | Mean Duration (s) | Median Duration (s) | 95th Percentile (s) | Max Duration (s) | Source File |
| :--- | :---: | :---: | :---: | :---: | :---: | :--- |
| **Development (DEV)** | 24 | 3.33 | 3.32 | 3.8 | 4.12 | `docs/evaluation/modelcheck_raw.jsonl` |
| **Test (TEST)** | 36 | 22.01 | 15.35 | 40.63 | 289.86 | `docs/evaluation/testcheck_raw.jsonl` |

---

## 3. Items Above 30 Seconds

| Item ID | Split | Duration (s) | Cause | Source File |
| :--- | :--- | :---: | :--- | :--- |
| `TEST-10` | TEST | 35.2827 | UNKNOWN | `docs/evaluation/testcheck_raw.jsonl` |
| `TEST-26` | TEST | 289.8571 | UNKNOWN | `docs/evaluation/testcheck_raw.jsonl` |
| `TEST-27` | TEST | 56.6882 | UNKNOWN | `docs/evaluation/testcheck_raw.jsonl` |

---

## 4. Items with AI Status Failed or Invalid Schema

| Item ID | Split | Status | Error Code | Schema Valid | Cause | Source File |
| :--- | :--- | :--- | :--- | :---: | :--- | :--- |
| `TEST-27` | TEST | `failed` | `TIMEOUT` |  | UNKNOWN | `docs/evaluation/testcheck_raw.jsonl` |

---

## 5. Token Generation Throughput (Tokens per Second)

| Evaluation Split | Mean Throughput (tokens/s) | Median Throughput (tokens/s) | Hardware Offload Context | Source File |
| :--- | :---: | :---: | :--- | :--- |
| **Development (DEV)** | 18.28 | 18.14 | Local Ollama qwen3:4b | `docs/evaluation/modelcheck_raw.jsonl` |
| **Test (TEST)** | 7.0 | 4.09 | Local Ollama qwen3:4b (28%/72% CPU/GPU VRAM offload) | `docs/evaluation/testcheck_raw.jsonl` |
