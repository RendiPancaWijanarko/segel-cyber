# Prompt and Corpus Touch History (AI-5b)

This document provides an exhaustive, honest record of every prompt text, few-shot exemplar choice, and ad-hoc script that touched or inspected the Development (`DEV-*.json`) and Exemplar (`EX-*.json`) corpus items prior to the official model-check evaluation run in commit `7702cdf` (`AI-5: model check`).

Per the reporting rules, all interactions are documented transparently without omissions. Zero test-split items (`TEST-*.json`) were ever loaded, queried, or included in any prompt.

---

## 1. Git Commit History Touching Corpus and Evaluation Scripts

| Commit | Date | Title / Description | Corpus / Evaluation Impact |
| :--- | :---: | :--- | :--- |
| `88614b2` | 2026-11-09 | `AI-3: corpus (unfrozen)` | Created initial corpus via `scripts/ai_eval/generate_corpus.py`: 6 exemplars (`EX-01..06`), 24 DEV items (`DEV-01..24`), 36 TEST items (`TEST-01..36`). Initial validation via `verify_corpus.py`. |
| `cfb84e2` | 2026-11-09 | `AI-3c: corpus corrections and freeze` | Rebalanced inconsistent items per Decision D9b (silent vs deterministic split). Regenerated DEV and TEST items; EX items remained unchanged. Computed and froze SHA-256 hashes of test split into `docs/ai_corpus_freeze.txt`. |
| `82aa874` | 2026-11-09 | `AI-4: evaluation harness for B0 and B1 baselines on dev split` | Authored `scripts/ai_eval/eval_baselines.py`. Read all 24 DEV items to compute B0 and B1 baseline metrics; identified 3 hard items missed by B1 (`DEV-14`, `DEV-17`, `DEV-18`). Exemplars were not evaluated. |
| `5223a92` | 2026-11-09 | `AI-4b: test-split guard in scripts/ai_eval` | Authored `scripts/ai_eval/guard.py`. Added permission and integrity gates preventing test split access without `SEGEL_ALLOW_TEST_EVAL=1` and matching freeze hashes. Wired into `verify_corpus.py`, `eval_baselines.py`, and `generate_corpus.py`. |
| `7702cdf` | 2026-11-10 | `AI-5: model check` | Official model check execution (`scripts/ai_eval/modelcheck.py`). Evaluated `qwen3:4b` on all 24 DEV items; generated `docs/evaluation/modelcheck_raw.jsonl`, `modelcheck_summary.txt`, `modelcheck.md`, and `modelcheck_prompt.txt`. |

---

## 2. Ad-Hoc Scripts Touching DEV / EX Items Prior to Official Model Check

Between commits `8fccfee` and `7702cdf`, the following ad-hoc scripts were created, executed, and subsequently cleaned up:

### Script 1: `scripts/ai_eval/inspect_dev.py`
- **Location**: `scripts/ai_eval/inspect_dev.py` (temporary, deleted before commit `7702cdf`).
- **Purpose**: Verify data structures, baseline diffs, B1 keyword classifications, and detection status across all 24 DEV items before writing `modelcheck.py`.
- **Items Touched**: All 24 DEV items (`DEV-01` through `DEV-24`). Exemplars were not touched. Model was **not** called.
- **Content Summary**:
  ```python
  import sys
  from pathlib import Path
  sys.path.insert(0, "src")
  sys.path.insert(0, ".")
  from inspector.baseline import BaselineV1
  from inspector.policy.expectations import classify_purpose_b1, derive_findings
  from scripts.ai_eval.guard import guard_read_corpus_file
  from scripts.ai_eval.verify_corpus import compute_diff_capabilities

  for f in sorted(Path("lab/ai_corpus").glob("DEV-*.json")):
      d = guard_read_corpus_file(f)
      prev = BaselineV1.model_validate(d["previous_baseline"])
      curr = BaselineV1.model_validate(d["candidate_baseline"])
      diff = sorted(compute_diff_capabilities(prev, curr))
      b1_class = classify_purpose_b1(d["purpose"])
      b1_findings = derive_findings(b1_class, diff)
      print(d["id"], d["language"], d["expected_purpose_class"], d["label"], b1_class, len(b1_findings) > 0, diff, d["purpose"])
  ```
- **Lifecycle**: Executed once via `.venv/Scripts/python.exe`, verified output, then removed via `Remove-Item scripts/ai_eval/inspect_dev.py`.

### Script 2: Conversation Scratch Script `test_prompt.py`
- **Location**: `<appDataDir>/brain/<conversation-id>/scratch/test_prompt.py`.
- **Purpose**: Test Ollama `qwen3:4b` inference with JSON-schema structured output (`think: false`, `temperature: 0`, `seed: 1`) on candidate prompt template against a subset of DEV items.
- **Items Touched**: 6 sample DEV items:
  - `DEV-01` (Consistent, L1, Indonesian)
  - `DEV-06` (Consistent, L3, English)
  - `DEV-08` (Consistent, L4, English)
  - `DEV-14` (Inconsistent silent, expected L4, English)
  - `DEV-17` (Inconsistent silent, expected L6, Indonesian)
  - `DEV-18` (Inconsistent silent, expected L6, English)
- **Model Responses on Scratch Run**:
  - `DEV-01`: predicted `L1`, ambiguous `False` (Correct)
  - `DEV-06`: predicted `L3`, ambiguous `False` (Correct)
  - `DEV-08`: predicted `L4`, ambiguous `False` (Correct)
  - `DEV-14`: predicted `L6`, ambiguous `True` (Classified as vague; derived finding flagged release as inconsistent)
  - `DEV-17`: predicted `L6`, ambiguous `True` (Correct)
  - `DEV-18`: predicted `L6`, ambiguous `True` (Correct)
- **Lifecycle**: Preserved in conversation scratch directory for auditing; not committed to repository.

---

## 3. Few-Shot Exemplar Selection History

Decision D14 requires the prompt to include 3 few-shot exemplars from the exemplar set (`EX-*.json`): one Indonesian paraphrase, one English, and one vague/L6.

### Candidates Available in `lab/ai_corpus/`:
1. `EX-01`: Indonesian (`id`), Class `L1`, Purpose: *"Pembaruan alamat server resolusi nama domain kantor cabang"*.
2. `EX-02`: English (`en`), Class `L4`, Purpose: *"Add outbound firewall egress rule for telemetry aggregation endpoint"*.
3. `EX-03`: Mixed (`mixed`), Class `L6`, Purpose: *"Pembaruan berkala parameter sistem informasi gateway node"*.
4. `EX-04`: Mixed (`mixed`), Class `L2`, Purpose: *"Provisioning akun operator baru untuk technical support jaringan intranet"*.
5. `EX-05`: Indonesian (`id`), Class `L3`, Purpose: *"Pengalihan tujuan log audit gateway wilayah ke server terpusat"*.
6. `EX-06`: English (`en`), Class `L5`, Purpose: *"Hardening node by disabling unused telnet and finger services"*.

### Selected Exemplars:
- **Indonesian Paraphrase**: `EX-01` (paraphrases DNS resolution without using English keywords).
- **English**: `EX-02` (standard outbound firewall egress rule).
- **Vague / L6**: `EX-03` (general system parameter refresh without domain specificity).

### Rejected / Unused Alternates:
- `EX-04`, `EX-05`, `EX-06` were not used in prompts to satisfy the 3-exemplar budget.
- **Zero other combinations were tested**. The selected trio was chosen prior to testing, used in `test_prompt.py`, and adopted directly into `modelcheck.py`.

---

## 4. Prompt Text Evolution and Official Freeze

### Prompt Evolution:
- **Draft 1 (Scratch test)**: System prompt defined L1..L6 per `docs/ai_purpose_classes.md`, guidelines 1-3, and the 3 few-shot exemplars (EX-01, EX-02, EX-03).
- **Official Prompt (Revision 0)**: Formatted as `PROMPT_SYSTEM` and `PROMPT_USER_TEMPLATE` in `scripts/ai_eval/modelcheck.py`. Saved verbatim to `docs/evaluation/modelcheck_prompt.txt`.
- **Revisions during official run**: **None (0 revisions)**. The official model-check run passed all Decision D19 criteria on its first attempt (100% schema validity, 0 false positives, 7/7 silent detection).

### SHA-256 Digest Verification:
- **Prompt file**: `docs/evaluation/modelcheck_prompt.txt`
- **Normalized SHA-256 (LF)**: `1d4d6da9a11d5586af8111697fd591890bc6bf4d09970dc19a8fbb611226defc`
- **Freeze Status**: Recorded in `docs/ai_prompt_freeze.txt`. The prompt text is now read-only.
