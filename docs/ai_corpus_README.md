# SEGEL AI Purpose and Expectation Corpus

This directory (`lab/ai_corpus/`) contains the evaluation dataset for the SEGEL AI Purpose Classifier and Consistency Verifier, structured in accordance with `docs/ai_decisions.md` (Decisions D9, D9b, D14, D15, and D17).

---

## 1. Provenance and Generation Notice

This corpus was authored with AI assistance and programmatically generated and validated by `scripts/ai_eval/generate_corpus.py` and `scripts/ai_eval/verify_corpus.py`. No model under test (specifically, no local Ollama model instance) was used to generate or label any item in this corpus. Domain-specific content has been neutralized using generic IT infrastructure terminology.

---

## 2. Dataset Structure & Stratification

The corpus comprises **66 JSON documents**:
- **6 Few-Shot Exemplars** (`split: "exemplar"`): Reference examples for in-context prompt templates, covering Indonesian paraphrasing, English, and vague purposes.
- **60 Evaluation Items**:
  - **30 Consistent Items**: 6 items per purpose class (L1 through L5) with unambiguous purpose descriptions and strictly matching candidate deltas (12 in dev, 18 in test).
  - **30 Inconsistent Items** (rebalanced per Decision D9b):
    - `hidden_extra_impact` (12 items: 4 dev, 8 test; all `mismatch_kind: "silent"`): Purpose claims a narrow capability, but candidate adds undeclared pass-severity capabilities.
    - `vague_or_misleading_purpose` (6 items: 3 dev, 3 test; all `mismatch_kind: "silent"`): Vague L6 purposes or misleading purposes claiming one class while diff introduces pass-severity capabilities of another.
    - `privilege_escalation` (4 items: 2 dev, 2 test; `mismatch_kind: "deterministic"`): Purpose claims standard operator account, but candidate grants administrative or root privileges (`privilege_granted`).
    - `control_weakening` (4 items: 1 dev, 3 test; `mismatch_kind: "deterministic"`): Purpose claims logging adjustment, but candidate disables logging or injects unauthorized trust anchors.
    - `over_broad_change` (4 items: 2 dev, 2 test; `mismatch_kind: "deterministic"`): Purpose claims a small change, but 8 or more entries differ from predecessor baseline, triggering `broad_change`.

### Split Stratification
- **Dev Split**: 24 items (12 consistent, 12 inconsistent; 7 silent, 5 deterministic)
- **Test Split**: 36 items (18 consistent, 18 inconsistent; 11 silent, 7 deterministic)

### Language Distribution
- **Indonesian (`id`)**: 28 items
- **English (`en`)**: 26 items
- **Mixed (`mixed`)**: 12 items

Keyword evasion is measured in AI-4 against the independently written docs/b1_keywords.md.

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
- `mismatch_kind` (`str`): Computed category (`"none"`, `"silent"`, or `"deterministic"`).
- `notes` (`str`): Descriptive review notes.

---

## 4. Ground Truth Verification

To re-run deterministic validation across all 66 corpus items:
```powershell
python scripts/ai_eval/verify_corpus.py
```
This script recomputes candidate-minus-previous capability deltas via `inspector.baseline.diff_capabilities`, validates `mismatch_kind` per taxonomy severities, and asserts exact agreement with `EXPECTATION_MAP` in `docs/ai_purpose_classes.md`.

---

## 5. Methodological Limitations & Policy Rules (AI-4b)

1. **Single-Purpose Policy**: Corpus labels follow a strict single-purpose policy: a declared change class is expected to touch only its own canonical capability kind per `EXPECTATION_MAP`. A release whose purpose states log-destination configuration that also introduces an outbound firewall rule is labelled `inconsistent`, although bundling such changes may be legitimate in operational environments.
2. **Assistant Authorship**: The corpus items, the B1 keyword taxonomy lists (`docs/b1_keywords.md`), and the prompt templates were authored by the same assistant. Generic IT vocabulary and independent derivation were applied to mitigate bias, but this shared provenance remains an evaluated limitation.
3. **Small Sample Size on Dev**: The development split contains only 7 silent inconsistent items and 3 hard items missed by B1 (`DEV-14`, `DEV-17`, `DEV-18`). Performance figures on the dev split are indicative rather than statistically exhaustive.
4. **Deterministic Subset Redundancy**: Items categorized under `mismatch_kind: "deterministic"` contain capabilities that trigger default-severity inspection rules (`warn` or `reject`) regardless of the stated release purpose. The silent subset represents the primary benchmark for AI expectation verification.

