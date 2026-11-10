# Model Check Evaluation Report (AI-5)

**Verdict**: `PASS` (Decision D19: PASSED)

## 1. D19 Evaluation Decision Rule
Per Decision D19 in `docs/ai_decisions.md`, model check evaluates:
1. **Schema Validity**: 100.0% (Required: $\ge 95\%$) -> **PASS**
2. **False Positives on 12 Consistent Items**: 0 (Required: $\le 2$) -> **PASS**
3. **Detection of 7 Silent Inconsistent Items**: B1 alone = 4/7; B1 $\cup$ AI = 7/7 (Required: $\ge 6$) -> **PASS**

## 2. Methodology & Configuration
- **Model**: `qwen3:4b` via Ollama at `http://127.0.0.1:11434`
- **Inference Parameters (D11)**: temperature=0, seed=1, num_ctx=2048, num_predict=200, think=false, keep_alive=30m, timeout=30s
- **Output Format**: JSON-schema constrained structured output + Python validator
- **Prompt Template SHA-256**: `1d4d6da9a11d5586af8111697fd591890bc6bf4d09970dc19a8fbb611226defc` (saved in `docs/evaluation/modelcheck_prompt.txt`)
- **Evaluation Split**: DEV split only (24 items: 12 consistent, 12 inconsistent; 7 silent, 5 deterministic). Test split guarded.

## 3. Summary Results Table
| Metric | Value | Target / Requirement | Status |
| :--- | :---: | :---: | :---: |
| **D19 Overall Verdict** | **PASS** | PASS | PASS |
| Schema Validity Rate | 100.0% (24/24) | $\ge 95\%$ | PASS |
| Consistent False Positives | 0 / 12 | $\le 2$ | PASS |
| Silent Inconsistent Detection (B1 $\cup$ AI) | 7 / 7 | $\ge 6$ | PASS |
| Silent Inconsistent Detection (B1 alone) | 4 / 7 | Baseline reference | N/A |
| Silent Inconsistent Detection (AI alone) | 7 / 7 | Reference | N/A |
| Overall Purpose-Class Accuracy | 91.7% (22/24) | Indicative | N/A |
| Hard Subset Accuracy | 66.7% (2/3) | Indicative | N/A |
| Warm Latency (Median) | 3.322s | Reference | N/A |
| Warm Latency (p95) | 3.759s | Reference | N/A |
| Generation Speed | 18.28 tok/s | Reference | N/A |

### Accuracy Breakdown by Class
| Class | Name | Correct / Total | Accuracy |
| :---: | :--- | :---: | :---: |
| L1 | 4 / 5 | 80.0% |
| L2 | 5 / 5 | 100.0% |
| L3 | 4 / 4 | 100.0% |
| L4 | 3 / 4 | 75.0% |
| L5 | 4 / 4 | 100.0% |
| L6 | 2 / 2 | 100.0% |

### Accuracy Breakdown by Language
| Language | Correct / Total | Accuracy |
| :---: | :---: | :---: |
| `id` | 9 / 10 | 90.0% |
| `en` | 10 / 11 | 90.9% |
| `mixed` | 3 / 3 | 100.0% |

## 4. Hard Subset Breakdown
Hard subset items (3 items: ['DEV-14', 'DEV-17', 'DEV-18']) missed by B1 alone:

| ID | Lang | Stated Purpose | Expected | Predicted | AI Detected | B1 Union AI |
| :--- | :---: | :--- | :---: | :---: | :---: | :---: |
| `DEV-14` | `en` | Synchronize communication parameters for branch office gateway node | `L4` | `L6` | True | True |
| `DEV-17` | `id` | Penyesuaian konfigurasi rutin siklus pemeliharaan infrastruktur jaringan | `L6` | `L6` | True | True |
| `DEV-18` | `en` | General system update and routine parameter refresh for branch nodes | `L6` | `L6` | True | True |

## 5. Sample Raw Outputs

### 3 Correct Raw Outputs
#### Item: `DEV-01` (Expected: `L1`, Predicted: `L1`)
- **Purpose**: "Penambahan DNS resolver internal jaringan kantor cabang utara"
- **Raw Model Content**:
```json
{
  "purpose_class": "L1",
  "ambiguous": false,
  "reason": "Penambahan DNS resolver internal jaringan kantor cabang utara berkaitan dengan pembaruan DNS allowlist (L1)."
}
```
- **Derived Findings**: `[]`

#### Item: `DEV-02` (Expected: `L1`, Predicted: `L1`)
- **Purpose**: "Register additional DNS forwarder for branch office network"
- **Raw Model Content**:
```json
{
  "purpose_class": "L1",
  "ambiguous": false,
  "reason": "Mendaftarkan DNS forwarder tambahan untuk jaringan kantor cabang berkaitan dengan pembaruan DNS allowlist (L1)."
}
```
- **Derived Findings**: `[]`

#### Item: `DEV-03` (Expected: `L2`, Predicted: `L2`)
- **Purpose**: "Penambahan akun operator perangkat telekomunikasi router regional"
- **Raw Model Content**:
```json
{
  "purpose_class": "L2",
  "ambiguous": false,
  "reason": "Penambahan akun operator perangkat telekomunikasi router regional merupakan penambahan akun operator (L2)."
}
```
- **Derived Findings**: `[]`

### Sample Incorrect Raw Outputs (or Classification Deviations)
#### Item: `DEV-14` (Expected: `L4`, Predicted: `L6`)
- **Purpose**: "Synchronize communication parameters for branch office gateway node"
- **Raw Model Content**:
```json
{
  "purpose_class": "L6",
  "ambiguous": true,
  "reason": "Synchronize communication parameters untuk node gateway cabang terlalu umum dan tidak spesifik ke kelas L1-L5 (L6)."
}
```
- **Derived Findings**: `[{'capability_id': 'L6', 'severity': 'warn', 'source': 'deterministic', 'description': 'purpose too vague to verify'}]`

#### Item: `DEV-23` (Expected: `L1`, Predicted: `L6`)
- **Purpose**: "Pembaruan minor tabel resolusi simpul gerbang komunikasi"
- **Raw Model Content**:
```json
{
  "purpose_class": "L6",
  "ambiguous": true,
  "reason": "Pembaruan tabel resolusi simpul gerbang komunikasi terlalu umum dan tidak spesifik ke kelas L1-L5 (L6)."
}
```
- **Derived Findings**: `[{'capability_id': 'L6', 'severity': 'warn', 'source': 'deterministic', 'description': 'purpose too vague to verify'}]`

## 6. Hardware & Environment
```text
Ollama ps:
NAME        ID              SIZE      PROCESSOR          CONTEXT    RUNNER      UNTIL               
qwen3:4b    359d7dd4bcda    3.2 GB    28%/72% CPU/GPU    2048       llamacpp    29 minutes from now

RAM Status:
skipped (psutil not installed)

NVIDIA SMI:
Tue Nov 10 10:25:11 2026       
+-----------------------------------------------------------------------------------------+
| NVIDIA-SMI 621.01                 KMD Version: 621.01        CUDA UMD Version: 13.5     |
+-----------------------------------------+------------------------+----------------------+
| GPU  Name                  Driver-Model | Bus-Id          Disp.A | Volatile Uncorr. ECC |
| Fan  Temp   Perf          Pwr:Usage/Cap |           Memory-Usage | GPU-Util  Compute M. |
|                                         |                        |               MIG M. |
|=========================================+========================+======================|
|   0  NVIDIA GeForce RTX 3050 ...  WDDM  |   00000000:01:00.0 Off |                  N/A |
| N/A   67C    P0             18W /   80W |    2321MiB /   4096MiB |     26%      Default |
|                                         |                        |                  N/A |
+-----------------------------------------+------------------------+----------------------+

+-----------------------------------------------------------------------------------------+
| Processes:                                                                              |
|  GPU   GI   CI              PID   Type   Process name                        GPU Memory |
|        ID   ID                                                               Usage      |
|=========================================================================================|
|    0   N/A  N/A            3132      C   ...a\lib\ollama\llama-server.exe      N/A      |
+-----------------------------------------------------------------------------------------+
```
