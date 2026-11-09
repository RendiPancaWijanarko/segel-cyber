# SEGEL AI Purpose and Expectation Corpus

This directory (`lab/ai_corpus/`) contains the evaluation dataset for the SEGEL AI Purpose Classifier and Consistency Verifier, structured in accordance with `docs/ai_decisions.md` (Decisions D9, D14, D15, and D17).

---

## 1. Provenance and Generation Notice

This corpus was authored with AI assistance and programmatically checked and validated by the verification script `scripts/ai_eval/verify_corpus.py`. No model under test (specifically, no local Ollama model instance) was used to generate or label any item in this corpus.

---

## 2. Dataset Structure & Stratification

The corpus comprises **66 JSON documents**:
- **6 Few-Shot Exemplars** (`split: "exemplar"`): Reference examples for in-context prompt templates, covering Indonesian paraphrasing, English, and vague purposes.
- **60 Evaluation Items**:
  - **30 Consistent Items**: 6 items per purpose class (L1 through L5) with unambiguous purpose descriptions and strictly matching candidate deltas.
  - **30 Inconsistent Items**: 6 items across each of the 5 inconsistency failure modes:
    - `hidden_extra_impact`: Purpose claims a narrow capability, but candidate adds undeclared network or administrative capabilities.
    - `privilege_escalation`: Purpose claims standard operator account, but candidate grants administrative or root privileges (`privilege_granted`).
    - `control_weakening`: Purpose claims logging adjustment, but candidate disables logging or injects unauthorized trust anchors.
    - `vague_or_misleading_purpose`: Vague L6 purposes with security-relevant capabilities (3 items) or misleading purposes claiming L5 hardening while enabling services or adding tasks (3 items).
    - `over_broad_change`: Purpose claims a small change, but 8 or more entries differ from predecessor baseline, triggering `broad_change`.

### Split Stratification
- **Dev Split**: 24 items (12 consistent, 12 inconsistent)
- **Test Split**: 36 items (18 consistent, 18 inconsistent)

### Language Distribution
- **Indonesian (`id`)**: 27 items
- **English (`en`)**: 22 items
- **Mixed (`mixed`)**: 17 items
- **Keyword Evasion**: 16 out of 30 inconsistent items (53.3%) employ operational euphemisms and paraphrases, avoiding obvious class keywords to evaluate model comprehension.

---

## 3. Schema per Item

Each item file adheres to the following JSON schema:
- `id` (`str`): Unique identifier (`EX-01`..`EX-06`, `DEV-01`..`DEV-24`, `TEST-01`..`TEST-36`).
- `split` (`str`): `"exemplar"`, `"dev"`, or `"test"`.
- `language` (`str`): `"id"`, `"en"`, or `"mixed"`.
- `purpose` (`str`): Stated release purpose (max 300 characters, no control characters).
- `previous_baseline` (`dict`): Predecessor Baseline v1 JSON configuration.
- `candidate_baseline` (`dict`): Candidate Baseline v1 JSON configuration.
- `expected_purpose_class` (`str`): Canonical class (`"L1"`..`"L6"`).
- `label` (`str`): Ground-truth label (`"consistent"` or `"inconsistent"`).
- `inconsistency_class` (`str | null`): Inconsistency classification category or `null`.
- `notes` (`str`): Descriptive review notes.

---

## 4. Ground Truth Verification

To re-run deterministic validation across all 66 corpus items:
```powershell
python scripts/ai_eval/verify_corpus.py
```
This script recomputes candidate-minus-previous capability deltas via `inspector.baseline.diff_capabilities` and asserts exact agreement with `EXPECTATION_MAP` in `docs/ai_purpose_classes.md`.
