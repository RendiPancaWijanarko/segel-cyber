# AI Inspector Integration State

This document tracks progress, test suite counts, open items, and next steps for the SEGEL AI Inspector integration (`feature/ai-inspector`).

---

## Current Status

- **Phase**: AI-0 (Rules, Decisions, Deviations)
- **Branch**: `feature/ai-inspector`
- **Date**: 2026-11-09
- **Last Commit**: `d1199d7` (base before AI-0 commit)

---

## Test Suite Baseline

Full test suite execution evidence:
- **Command**: `.venv/Scripts/python.exe -m pytest`
- **Platform**: Windows 10/11 (win32), Python 3.14.6, pytest-9.2.0, pluggy-1.7.0
- **Total Tests**: 310 passed, 0 failed, 0 errors, 1 warning (14.12 seconds)
- **Category Counts**:
  - `tests/adversarial/`: 68 passed
  - `tests/gaps/`: 18 passed
  - `tests/integration/`: 6 passed
  - `tests/unit/`: 218 passed
- **Warnings**: 1 (`PytestCollectionWarning` on `TestPredicate` in `src/segel_core/schemas/attestation.py:345`)

---

## Finished Items (AI-0)

- [x] Created `feature/ai-inspector` branch from current HEAD (`d1199d7`).
- [x] Created `AGENTS.md` at repository root containing verbatim project rules.
- [x] Created `docs/ai_decisions.md` containing verbatim architectural decisions D1 through D18.
- [x] Created `docs/deviations.md` detailing 12 specification-vs-implementation drifts (including predicate URN, payloadType, capability names, Python 3.14 vs 3.12, Baseline v1 JSON vs YAML, flat AI predicate fields vs nested block, purpose sanitization, WARN acknowledgement, and key separation).
- [x] Initialized progress tracker `docs/ai_state.md` with test metrics and phase boundaries.
- [x] Executed full test suite with raw counts and runtime documented.
- [x] Preserved `src/` and `tests/` without modifications in this setup step.
- [x] Completed HYG pass:
  - Documented `httpx2` status and confirmed removal from `pyproject.toml`.
  - Added `psutil>=6.0.0` lower bound to `pyproject.toml` dev extras.
  - Reported runtime versions (3.14.6 in .venv vs 3.12 target) and proposed migration plan.
  - Docs hygiene: audited relative paths and rewritten absolute claims across docs (`PROGRESS.md`, `audit.md`, `SECURITY_MODEL.md`, `hardening_state.md`, `limitations.md`).
  - NOTICE inventory: listed UI assets/references, added Ollama and `qwen3:4b` entries.
  - Subprocess hygiene: replaced `shell=True` with list arguments in `scripts/mutation_runner.py` and resolved ruff issues.
  - Test suite re-run: 310 passed, 0 failed, 1 warning in 8.03s.

---

## Open Items

- [ ] **AI-1: Worker Subprocess & Transport**:
  - Implement isolated worker (`python -m inspector.ai.worker`).
  - Scrub environment variables; zero key parameters passed.
  - Implement synchronous loopback HTTP client to Ollama (`127.0.0.1:11434`) with 30s timeout.
  - Graceful fallback when Ollama is unavailable (`ai_status="skipped"` or `"failed"`).
- [ ] **AI-2: Taxonomy & Classification Engine**:
  - Purpose classification L1..L6 with ambiguity flag and Indonesian reason.
  - Deterministic expectation map and B1 keyword fallback.
  - Capability kind additions (11 new kinds) with `<kind>#<n>` instance IDs.
  - Manifest purpose input sanitization (reject control characters, length cap 300).
- [ ] **AI-3: Predicate Schemas & Merge Logic**:
  - Add `ai_model_digest` and `ai_error_code` to `InspectPredicate` (flat fields, no version bump).
  - Fix merge logic defects in `src/inspector/inspector.py` (cap AI severity at `warn`, never escalate to `REJECT`, never overwrite AI findings).
- [ ] **AI-4: WARN Acknowledgement**:
  - Add `require_warn_acknowledgement` policy flag.
  - Implement and validate `acknowledgement_digest` in `ApprovePredicate`, Ledger, and Receiver.
- [ ] **AI-5: Corpus & Evaluation**:
  - Construct 6 few-shot exemplars and 60 evaluation items (30 consistent, 30 inconsistent).
  - Split 24 dev / 36 test; freeze and record hash in `docs/ai_corpus_freeze.txt`.
- [ ] **AI-6: Release Desk UI**:
  - AI advisory panel on release detail page.
  - `ai_status` banner, acknowledgement control, and competition prototype disclaimer.

---

## Next Step

- Proceed with **AI-1**: Implement the isolated worker subprocess (`src/inspector/ai/worker.py`), scrubbed environment execution, and loopback Ollama client with fallback handling.

