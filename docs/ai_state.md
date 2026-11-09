# AI Inspector Integration State

This document tracks progress, test suite counts, open items, and next steps for the SEGEL AI Inspector integration (`feature/ai-inspector`).

---

## Current Status

- **Phase**: AI-3c (Purpose Corpus Corrections, D9b Rebalancing, and Freeze)
- **Branch**: `feature/ai-inspector`
- **Date**: 2026-11-09
- **Last Commit**: `88614b2` ("AI-3: corpus (unfrozen)")

---

## Test Suite Baseline

Full test suite execution evidence:
- **Command**: `.venv/Scripts/python.exe -m pytest`
- **Platform**: Windows 10/11 (win32), Python 3.14.6, pytest-9.2.0, pluggy-1.7.0
- **Total Tests**: 328 passed, 0 failed, 0 errors, 1 warning (7.99 seconds)
- **Category Counts**:
  - `tests/adversarial/`: 68 passed
  - `tests/gaps/`: 18 passed
  - `tests/integration/`: 6 passed
  - `tests/unit/`: 236 passed
- **Warnings**: 1 (`PytestCollectionWarning` on `TestPredicate` in `src/segel_core/schemas/attestation.py:345`)

---

## Finished Items

### AI-0: Rules, Decisions, Deviations & HYG
- [x] Created `feature/ai-inspector` branch from current HEAD (`d1199d7`).
- [x] Created `AGENTS.md` at repository root containing verbatim project rules.
- [x] Created `docs/ai_decisions.md` containing verbatim architectural decisions D1 through D18.
- [x] Created `docs/deviations.md` detailing 12 specification-vs-implementation drifts.
- [x] Completed HYG pass: `httpx2` removed, `psutil` lower bound added, docs claims rewritten, NOTICE updated, list-argument subprocess in mutation runner.

### AI-2 (Part 1): Capability Taxonomy & Baseline v1 Structured Extraction
- [x] Authored `docs/capability_taxonomy.md` covering all 16 capability kinds, parameters, default severities, and instance ID format `<kind>#<n>`.
- [x] Defined Baseline v1 JSON Pydantic model (`extra="forbid"`) in `src/inspector/baseline.py`: `firewall.outbound_allowed[]`, `dns_allowlist[]`, `services{enabled[],disabled[]}`, `accounts[{name,privilege}]`, `logging{enabled,destination}`, `scheduled_tasks[]`, `trust_anchors[]`.
- [x] Implemented `parse_baseline_v1` using stdlib `json.loads` with `object_pairs_hook=reject_duplicate_keys`.
- [x] Implemented `extract_capabilities_structured(files)` and `diff_capabilities(previous, current)` (identifying new, changed, and removed entries).
- [x] Implemented `broad_change` detection triggering when 8 or more entries differ from predecessor.
- [x] Maintained regex pattern matching fallback in `extract_capabilities(files)` so all existing tests remain green.
- [x] Authored 18 tests in `tests/unit/test_baseline_and_taxonomy.py` covering positive/negative per kind, duplicate keys, huge values, determinism, instance ID format, and predecessor diffing (showed red run, then green). Suite expanded from 310 to 328 tests.

### AI-3c: Purpose Corpus Corrections, D9b Rebalancing, and Freeze
- [x] Appended Decision D9b to `docs/ai_decisions.md` (rebalanced inconsistent items to maximize AI value with silent mismatches while maintaining deterministic controls).
- [x] Added computed field `mismatch_kind` (`"none"`, `"silent"`, `"deterministic"`) to all items, computed from taxonomy severity rules in `verify_corpus.py` and `generate_corpus.py`.
- [x] Programmatically rebalanced corpus via `scripts/ai_eval/generate_corpus.py`:
  - Dev inconsistent (12): hidden_extra_impact 4 (`silent`), vague_or_misleading_purpose 3 (`silent`), privilege_escalation 2 (`deterministic`), control_weakening 1 (`deterministic`), over_broad_change 2 (`deterministic`). (7 silent, 5 deterministic).
  - Test inconsistent (18): hidden_extra_impact 8 (`silent`), vague_or_misleading_purpose 3 (`silent`), privilege_escalation 2 (`deterministic`), control_weakening 3 (`deterministic`), over_broad_change 2 (`deterministic`). (11 silent, 7 deterministic).
  - Consistent items maintained: 12 dev, 18 test (exactly 6 each for L1..L5). Exemplars: 6.
- [x] Neutralized domain-specific content: removed all military references (rudal, battlefield, puskodal, garnisun, etc.) in favor of generic IT wording (node, gateway, branch office, telemetry, operator).
- [x] Verified that no two purposes share the same first four words.
- [x] Removed keyword evasion percentage and documented: "keyword evasion is measured in AI-4 against the independently written docs/b1_keywords.md".
- [x] Regenerated `docs/ai_corpus_review_summary.md` from script option `scripts/ai_eval/verify_corpus.py --summary docs/ai_corpus_review_summary.md`.
- [x] Ran ruff check on `scripts/ai_eval/` (`All checks passed!`) and full test suite (328 passed, 0 failed).
- [x] Clean sweep search for "C:\", "Users\", and "file://" with zero hits across `docs/` and `scripts/`.
- [x] Generated `docs/ai_corpus_freeze.txt` containing SHA-256 hashes of test-split items and byte concatenation.

---

## Open Items

- [ ] **AI-1: Worker Subprocess & Transport**:
  - Implement isolated worker (`python -m inspector.ai.worker`).
  - Scrub environment variables; zero key parameters passed.
  - Implement synchronous loopback HTTP client to Ollama (`127.0.0.1:11434`) with 30s timeout.
  - Graceful fallback when Ollama is unavailable (`ai_status="skipped"` or `"failed"`).
- [ ] **AI-2 (Part 2): Purpose Classification & Expectation Checking Engine**:
  - Purpose classification L1..L6 with ambiguity flag and Indonesian reason.
  - Deterministic expectation map and B1 keyword fallback.
  - Manifest purpose input sanitization (reject control characters, length cap 300).
- [ ] **AI-4: Predicate Schemas & Merge Logic**:
  - Add `ai_model_digest` and `ai_error_code` to `InspectPredicate` (flat fields, no version bump).
  - Fix merge logic defects in `src/inspector/inspector.py` (cap AI severity at `warn`, never escalate to `REJECT`, never overwrite AI findings).
- [ ] **AI-5: WARN Acknowledgement**:
  - Add `require_warn_acknowledgement` policy flag.
  - Implement and validate `acknowledgement_digest` in `ApprovePredicate`, Ledger, and Receiver.
- [ ] **AI-6: Corpus Freeze & Evaluation Runner**:
  - Freeze corpus and record SHA-256 hashes in `docs/ai_corpus_freeze.txt`.
  - Implement evaluation runner against Ollama / mock worker.
- [ ] **AI-7: Release Desk UI**:
  - AI advisory panel on release detail page.
  - `ai_status` banner, acknowledgement control, and competition prototype disclaimer.

---

## Next Step

- Proceed with **AI-1**: Implement isolated worker subprocess (`src/inspector/ai/worker.py`), scrubbed environment execution, and loopback Ollama client with fallback handling.

