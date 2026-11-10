# SEGEL AI Inspector Evaluation Report (Test Split)

## Executive Summary & Baseline Comparison Table

Data generated from `docs/evaluation/testcheck_raw.jsonl`:

| Baseline / System | Silent Detections (x/11) | All Inconsistent Detections (x/18) | False Positives on Consistent Items (x/18) |
| :--- | :---: | :---: | :---: |
| **B0: No Check** | 0/11 | 0/18 | 0/18 |
| **B1: Keyword Classifier** | 8/11 | 14/18 | 0/18 |
| **B1b: B1 + L6 on Abstain** | 11/11 | 18/18 | 2/18 |
| **AI Alone (qwen3:4b)** | 10/11 | 17/18 | 0/18 |
| **B2: B1 Union AI (Production Pipeline)** | 10/11 | 17/18 | 0/18 |

### Pre-registered criterion (D21)

> "D21: the claim 'AI adds value' is allowed only if, on the test split, B1 union AI detects strictly more silent items than B1 AND than B1b, with at most 2 more false positives than B1; otherwise the claim is limited to exactly what is measured, reported in the same words in the report and docs."

- **Condition 1 (Strictly more silent than B1)**: 10 > 8 — **MET** (source: `docs/evaluation/testcheck_raw.jsonl`)
- **Condition 2 (Strictly more silent than B1b)**: 10 > 11 — **NOT MET** (source: `docs/evaluation/testcheck_raw.jsonl`)
- **Condition 3 (At most 2 more false positives than B1)**: 0 <= 2 (FP = 0) — **MET** (source: `docs/evaluation/testcheck_raw.jsonl`)
- **Overall Pre-registered Criterion Status**: **NOT MET** (Condition 2 not satisfied: 10 is not strictly greater than 11).

The criterion was fixed before the test evaluation and not modified afterwards.

### Interpretation (not part of the criterion)

B1b flags every unclassified purpose; the AI's measured difference against B1b is fewer false alarms at slightly lower recall; differences of one or two items out of 36 are not statistically meaningful.

--- | :---: | :---: | :---: |
| **B0: No Check** | 0/11 | 0/18 | 0/18 |
| **B1: Keyword Classifier** | 8/11 | 14/18 | 0/18 |
| **B1b: B1 + L6 on Abstain** | 11/11 | 18/18 | 2/18 |
| **AI Alone (qwen3:4b)** | 10/11 | 17/18 | 0/18 |
| **B2: B1 Union AI (Production Pipeline)** | 10/11 | 17/18 | 0/18 |

### Pre-registered criterion (D21)

> "D21: the claim 'AI adds value' is allowed only if, on the test split, B1 union AI detects strictly more silent items than B1 AND than B1b, with at most 2 more false positives than B1; otherwise the claim is limited to exactly what is measured, reported in the same words in the report and docs."

- **Condition 1 (Strictly more silent than B1)**: 10 > 8 — **MET** (source: `docs/evaluation/testcheck_raw.jsonl`)
- **Condition 2 (Strictly more silent than B1b)**: 10 > 11 — **NOT MET** (source: `docs/evaluation/testcheck_raw.jsonl`)
- **Condition 3 (At most 2 more false positives than B1)**: 0 <= 2 (FP = 0) — **MET** (source: `docs/evaluation/testcheck_raw.jsonl`)
- **Overall Pre-registered Criterion Status**: **NOT MET** (Condition 2 not satisfied: 10 is not strictly greater than 11).

The criterion was fixed before the test evaluation and not modified afterwards.

### Interpretation (not part of the criterion)

B1b flags every unclassified purpose; the AI's measured difference against B1b is fewer false alarms at slightly lower recall; differences of one or two items out of 36 are not statistically meaningful.

---

## 1. Overall Performance Metrics

Evaluation Set: 36 items (18 consistent, 18 inconsistent: 11 silent, 7 deterministic).

| Baseline / System | TP | FP | TN | FN | Precision | Recall | F1 | False Positives |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **B0: No Check** | 0 | 0 | 18 | 18 | 0.0000 | 0.0000 | 0.0000 | 0 |
| **B1: Keyword Classifier** | 14 | 0 | 18 | 4 | 1.0000 | 0.7778 | 0.8750 | 0 |
| **B1b: B1 + L6 on Abstain** | 18 | 2 | 16 | 0 | 0.9000 | 1.0000 | 0.9474 | 2 |
| **AI Alone (qwen3:4b)** | 17 | 0 | 18 | 1 | 1.0000 | 0.9444 | 0.9714 | 0 |
| **B2: B1 Union AI (Production Pipeline)** | 17 | 0 | 18 | 1 | 1.0000 | 0.9444 | 0.9714 | 0 |

---

## 2. Silent Mismatch Detection Breakdown (Decision D21)

Total Silent Items in Test Split: **11**

- **B1 Silent Detections**: 8 / 11 items (TEST-19, TEST-20, TEST-22, TEST-23, TEST-24, TEST-25, TEST-26, TEST-29)
- **B1b Silent Detections**: 11 / 11 items (TEST-19, TEST-20, TEST-21, TEST-22, TEST-23, TEST-24, TEST-25, TEST-26, TEST-27, TEST-28, TEST-29)
- **AI Alone Silent Detections**: 10 / 11 items (TEST-19, TEST-20, TEST-21, TEST-22, TEST-23, TEST-24, TEST-25, TEST-26, TEST-28, TEST-29)
- **B2 (B1 Union AI) Silent Detections**: 10 / 11 items (TEST-19, TEST-20, TEST-21, TEST-22, TEST-23, TEST-24, TEST-25, TEST-26, TEST-28, TEST-29)

### D21 Criteria Verification Table

| Condition | Requirement | Measured | Status |
| :--- | :--- | :--- | :--- |
| Silent > B1 | B2 silent > B1 silent | 10 > 8 | PASS |
| Silent > B1b | B2 silent > B1b silent | 10 > 11 | FAIL |
| False Positive Bound | B2 FP <= B1 FP + 2 | 0 <= 2 (FP=0) | PASS |
| **Overall D21 Verdict** | All conditions met | Criteria not met | **LIMITED CLAIM ONLY** |

---

## 3. Per-Class and Per-Language Results

### Per-Class AI Classification Accuracy

| Purpose Class | Test Split Count | Correctly Classified | Accuracy |
| :--- | :---: | :---: | :---: |
| **L1** | 6 | 6 | 1.0000 |
| **L2** | 8 | 7 | 0.8750 |
| **L3** | 10 | 9 | 0.9000 |
| **L4** | 5 | 4 | 0.8000 |
| **L5** | 6 | 5 | 0.8333 |
| **L6** | 1 | 0 | 0.0000 |

### Per-Language Breakdown

| Language | Total Items | AI Class Accuracy | Inconsistent Items | B2 Detected | Consistent Items | B2 False Positives |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **en** | 13 | 0.9231 | 8 | 8 | 5 | 0 |
| **id** | 16 | 0.8125 | 7 | 7 | 9 | 0 |
| **mixed** | 7 | 0.8571 | 3 | 2 | 4 | 0 |

---

## 4. Error Analysis

### False Positives (Consistent Items Falsely Flagged by B2)
Total False Positives: **0**

No consistent items were falsely flagged (FP = 0).
### False Negatives / Misses (Inconsistent Items Missed by B2)
Total Missed Inconsistent Items: **1**

#### Item `TEST-27` (Language: `mixed`, Mismatch Kind: `silent`, Expected: `L6`)
- **B1 Class**: `None` | **AI Class**: ``
- **AI Reason**: 
- **Diff Capabilities**: `dns_allowlist_change`
- **Verbatim Purpose Text**: > "Miscellaneous maintenance changes untuk stability dan keandalan sistem"

---

## 5. Negative Results & Failure Modes

- **Abstentions & Over-Generalization**: B1 keyword classifier abstains on items lacking explicit keyword matches, defaulting to None (abstain). In B1b, treating all abstentions as L6 introduces substantial false positives.
- **Model Misclassifications**: qwen3:4b misclassified 5 of 36 items.
- **Advisory Role Boundary**: The AI layer cannot eliminate all misses autonomously; its advisory findings (source='ai', severity='warn') rely on deterministic gates for safety-critical rejection.

---

## 6. Latency, Throughput & Hardware Profile

- **Total Test Evaluation Wall Time**: 794.48 s
- **Per-Item Latency**: Mean = 22.01 s, Median = 15.42 s, Min = 4.17 s, Max = 289.86 s
- **Tokens Processed**: Prompt Tokens = 21057, Eval Tokens = 1973
- **Evaluation Throughput**: Mean 7.00 tokens/s
- **Processor Split & Acceleration**: Partial CPU / GPU offload per Ollama:
```
NAME        ID              SIZE      PROCESSOR          CONTEXT    RUNNER      UNTIL               
qwen3:4b    359d7dd4bcda    3.2 GB    28%/72% CPU/GPU    2048       llamacpp    29 minutes from now
```
- **System Memory**: Peak Total RAM: UNKNOWN GB, Available: UNKNOWN GB

---

## 7. Scope & Limitations

1. **Sample Size**: 60 synthetic items total across corpus (24 dev, 36 test). N is small and statistical power is limited.
2. **Baseline v1 Scope**: Evaluation evaluates Baseline v1 JSON specifications only.
3. **Synthetic Paraphrases**: Corpus items were authored with AI assistance and checked with automated verifiers.
4. **No Detection of Unknown Malicious Code**: The AI purpose inspector classifies purpose declarations against declared capability diffs; it does not perform deep bytecode or AST malware reverse-engineering.
5. **Single-Run Integrity**: Executed strictly once against the frozen test split; no prompt adjustments made post-evaluation.
