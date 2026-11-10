# AI Inspector Integration State

This document tracks progress, test suite counts, open items, and next steps for the SEGEL AI Inspector integration (`feature/ai-inspector`).

---

## Current Status

- **Phase**: AI-7 (Purpose Sanitization, WARN Acknowledgement, and Release Desk UI)
- **Branch**: `feature/ai-inspector`
- **Date**: 2026-11-10
- **Last Commit**: in progress

---

## Test Suite Baseline

Full test suite execution evidence:
- **Command**: `.venv/Scripts/python.exe -m pytest`
- **Platform**: Windows 10/11 (win32), Python 3.14.6, pytest-9.2.0, pluggy-1.7.0
- **Total Tests**: 383 passed, 0 failed, 0 errors, 1 warning (8.54 seconds)
- **Category Counts**:
  - `tests/adversarial/`: 68 passed
  - `tests/gaps/`: 18 passed
  - `tests/integration/`: 6 passed
  - `tests/unit/`: 291 passed (including 61 in `test_inspector.py`, 6 in `test_ai_eval_guard.py`)
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
- [x] Neutralized domain-specific content: removed all military references in favor of generic IT wording.
- [x] Checked that no two purposes share the same first four words.
- [x] Removed keyword evasion percentage and documented: "keyword evasion is measured in AI-4 against the independently written docs/b1_keywords.md".
- [x] Regenerated `docs/ai_corpus_review_summary.md` from script option `scripts/ai_eval/verify_corpus.py --summary docs/ai_corpus_review_summary.md`.
- [x] Ran ruff check on `scripts/ai_eval/` (`All checks passed!`) and full test suite (328 passed, 0 failed).
- [x] Clean sweep search for "C:\", "Users\", and "file://" with zero hits across `docs/` and `scripts/`.
- [x] Generated `docs/ai_corpus_freeze.txt` containing SHA-256 hashes of test-split items and byte concatenation.

### AI-2b: Regex Identifier Boundaries & False-Match Prevention
- [x] Added identifier boundaries `(?<![a-zA-Z0-9_])` to all 17 regex patterns across the 5 capability kinds in `src/inspector/inspector.py:CAPABILITY_RULES`.
- [x] Maintained structured baseline extractor (`src/inspector/baseline.py`) completely untouched.
- [x] Tests first: authored `TestRegexIdentifierBoundaries` in `tests/unit/test_inspector.py` asserting that substring words (`import:`, `support:`, `report:`, `pseudo:`, `oauth:`, `nameserver:`, `csrftoken:`, `author:`, `antiforgerytoken:`, `teleport:`, `webserver:`, `desudo:`, `app_sudo:`, `app_port:`) produce 0 capabilities, and asserting intended positive controls with boundaries (`port:`, `server:`, `listen:`, `bind_address:`, `log_file:`, `output_path:`, `write_dir:`, `data_dir:`, `upstream:`, `remote_host:`, `proxy:`, `api_url:`, `auth:`, `token:`, `password:`, `secret:`, `api_key:`, `sudo:`, `run_as_root:`, `privileged:`).
- [x] Showed the red run (10 failed assertions due to false matches on unbounded regexes).
- [x] Applied negative lookbehind identifier boundaries in `CAPABILITY_RULES`; showed green run (58 passed in `tests/unit/test_inspector.py`).
- [x] Ran full test suite: 374 passed, 0 failed (37 new tests, 0 existing tests affected or broken).
- [x] Checked with `ruff check` (0 errors) on modified files.

### AI-4: Deterministic Expectations, B1 Keyword Classifier & Dev Baseline Evaluation
- [x] Authored `docs/b1_keywords.md` defining generic security keyword taxonomies for L1..L5 in Indonesian and English, with documented assistant authorship limitation.
- [x] Added `EXPECTATION_MAP` to `src/inspector/policy/expectations.py` mapping L1..L5 to canonical capabilities and L6 to empty set.
- [x] Implemented `derive_findings(purpose_class, capabilities) -> list[InspectFinding]` emitting `warn` for capabilities outside expected set, and "purpose too vague to verify" for L6.
- [x] Implemented `classify_purpose_b1(purpose) -> str | None` using compiled regex patterns with word boundaries (`\b`); returns L1..L5 on exact single match, abstains (`None`) on 0 or multiple matches; never returns L6.
- [x] Integrated expectation check into `inspect_release` in `src/inspector/inspector.py` for B1's predicted class.
- [x] Authored 9 unit tests in `tests/unit/test_expectations_and_b1.py` covering single match, abstain on ambiguous/no match, expectation check on L1..L5 and L6, and full `inspect_release` integration.
- [x] Proved with full test suite (337 passed, 0 failed) that zero existing test changes verdict.
- [x] Authored evaluation harness `scripts/ai_eval/eval_baselines.py` evaluating B0 and B1 strictly on DEV split.
- [x] Evaluated B0 (0% recall on silent items, 100% on deterministic items via default severity rules) and B1 (57.1% recall on silent items, 0 FP on consistent items).
- [x] Identified hard subset on DEV: `DEV-14`, `DEV-17`, `DEV-18` (size 3, 42.9% of silent items).
- [x] Checked code quality with `ruff check scripts/ai_eval/eval_baselines.py` (0 errors).

### AI-4b: Test-Split Guard & Audit (Unit 1)
- [x] Authored `scripts/ai_eval/guard.py` enforcing strict test-split isolation: all scripts under `scripts/ai_eval` refuse access to `TEST-*.json` unless `SEGEL_ALLOW_TEST_EVAL=1` is set AND SHA-256 hashes match `docs/ai_corpus_freeze.txt`.
- [x] Defaults to exemplar and dev only (30 items total).
- [x] Integrated guard into `verify_corpus.py` (added `--include-test` flag), `eval_baselines.py`, and `generate_corpus.py`.
- [x] Tests first: authored `tests/unit/test_ai_eval_guard.py` (6 tests: default disallows test split, raises `PermissionError` without env, `get_corpus_files` returns 30 items, freeze integrity checked on current repo, access permitted with env and freeze, access denied if hash mismatches).
- [x] Showed red run (`ModuleNotFoundError: No module named 'scripts.ai_eval.guard'`), then green run (6 passed). Full test suite: 380 passed, 0 failed.

### AI-4b: Regex Identifier Boundary Update (Unit 2)
- [x] Updated regex lookbehind in `src/inspector/inspector.py:CAPABILITY_RULES` from `(?<![a-zA-Z0-9_])` to `(?<![a-zA-Z0-9])`, permitting `_`, `-`, and `.` to precede keywords (e.g. `app_port`, `listen_port`, `ssh-port`, `http.port`, `app_sudo`).
- [x] Added code comment: a missed key is worse than a false positive in this fail-closed component.
- [x] Converted negative controls `app_port: 8080` and `app_sudo: false` into positive controls, and added `listen_port: 22`, `ssh-port: 22`, `http.port: 80`. Kept all 12 genuine substring negative controls (`import`, `support`, `report`, `pseudo`, `oauth`, `nameserver`, `csrftoken`, `author`, `antiforgerytoken`, `teleport`, `webserver`, `desudo`).
- [x] Showed red run (3 failed assertions on un-updated boundary), then green run (61 passed in `tests/unit/test_inspector.py`). Full test suite: 383 passed, 0 failed.

### AI-4b: Methodological Limitations, README & Decision D19 (Unit 3)
- [x] Added Section 5 in `docs/limitations.md` and `docs/ai_corpus_README.md`:
  - (a) Single-purpose policy: declared change class expected to touch only its own canonical capability; bundles labelled inconsistent even if operationally legitimate.
  - (b) Common assistant authorship: corpus, B1 keyword taxonomy, and prompt templates authored by the same assistant.
  - (c) Dev small-N sample: 7 silent items, 3 hard items; results are indicative.
  - (d) Deterministic-subset items caught by default-severity rules (`warn`/`reject`) regardless of purpose.
- [x] Appended Decision D19 to `docs/ai_decisions.md`: model-check PASS rule (schema validity >= 95%, false positives <= 2 of 12 consistent DEV items, B1 union AI detects >= 6 of 7 silent DEV items).

### AI-5: Model Check Evaluation on DEV Split
- [x] Implemented `scripts/ai_eval/modelcheck.py` evaluating `qwen3:4b` via loopback Ollama (`http://127.0.0.1:11434`) on DEV split only.
- [x] Configured D11 inference parameters: temperature 0, seed 1, num_ctx 2048, num_predict 200, think=false, keep_alive 30m, timeout 30s.
- [x] Applied JSON-schema constrained structured output + Python validator for `{"purpose_class", "ambiguous", "reason"}`.
- [x] Code derivation: `derive_findings` produces expectation-mismatch warnings; reason is advisory only.
- [x] Decision D19 Evaluation Verdict: **PASS**:
  - (1) Schema validity: 100.0% (24/24) (threshold >= 95%).
  - (2) False positives on 12 consistent DEV items: 0 / 12 (threshold <= 2).
  - (3) Silent DEV items detected: B1 alone = 4/7, B1 union AI = 7/7 (threshold >= 6).
- [x] Performance: Overall accuracy 91.7% (22/24), hard subset accuracy 66.7% (2/3), median warm latency 3.322s, p95 3.759s, 18.28 tok/s.
- [x] Saved exact evaluation artifacts in `docs/evaluation/`: `modelcheck_summary.txt`, `modelcheck_raw.jsonl`, `modelcheck_prompt.txt` (SHA-256: `1d4d6da9a11d5586af8111697fd591890bc6bf4d09970dc19a8fbb611226defc`), `modelcheck.md`.

### AI-5b: Model Check Reporting, B1b Baseline, Prompt History and Freeze
- [x] Implemented `scripts/ai_eval/modelcheck_report.py` reading ONLY `docs/evaluation/modelcheck_raw.jsonl`.
- [x] Generated `docs/evaluation/modelcheck_table.tsv` with 24 DEV item predictions, classifications, and finding kinds.
- [x] Generated `docs/evaluation/modelcheck_b1b.txt` evaluating Baseline B1b (abstention as L6):
  - B1b achieves 7/7 silent detection but produces 2 false positives on consistent items (`DEV-06`, `DEV-08`) where B1 abstained.
  - In comparison, AI correctly classifies `DEV-06` (L3) and `DEV-08` (L4), producing 0 false positives while maintaining 7/7 silent detection.
  - Confirmed agreement between `predicted_ambiguous` and `(predicted_class == 'L6')` (0 divergences).
- [x] Authored `docs/evaluation/prompt_history.md` detailing every git commit, ad-hoc script (`inspect_dev.py`, scratch `test_prompt.py`), prompt text, and few-shot selection touching DEV or EX items before the official run.
- [x] Generated `docs/ai_prompt_freeze.txt` with prompt SHA-256 (`1d4d6da9a11d5586af8111697fd591890bc6bf4d09970dc19a8fbb611226defc`) freezing prompt text.
- [x] Appended Decisions D20, D21, D22 to `docs/ai_decisions.md`.

### AI-6: AI Inspector Integration, Worker Isolation, and Merge Logic Fixes
- [x] Authored comprehensive adversarial and isolation test suite first in `tests/unit/test_ai_inspector.py` using `ScriptedFakeLLM`:
  - AT-016: Invalid class values or schema outside L1..L6 discarded with `ai_status="failed"` and distinct error code (`INVALID_CLASS`/`INVALID_SCHEMA`), verdict unchanged.
  - AT-017: Model claim of safety does not downgrade deterministic `REJECT`.
  - AT-018: Subprocess timeout, malformed JSON after one retry, and connection refused produce `ai_status="failed"` with distinct error codes (`TIMEOUT`, `MALFORMED_JSON`, `CONNECTION_REFUSED`), verdict unchanged.
  - AT-019: Prompt injection text in purpose cannot lower verdicts, produce `REJECT`, or exceed severity `warn`.
  - Derivation: Findings come strictly from expectation map; reasons never influence decisions; cite capability instance IDs (`<kind>#<n>`); vague-L6 rule cites every capability instance with `"purpose too vague to verify (AI class L6)"`.
  - Union & Merge: B1 findings never removed by AI output; Defect 1 (overwriting AI finding severity to match `REJECT`) and Defect 2 (escalating verdict to `REJECT` on AI output) tested and fixed.
  - Worker Isolation: Fresh-interpreter import asserts `sys.modules` contains no `release_desk`, `demo_infra`, `approver`, or key-handling modules; worker environment scrubbed of all key material; loopback endpoint gating rejects non-loopback hosts.
  - Equivalence: Production derivation reproduces exact `ai_detected` flags across all 24 DEV items in `docs/evaluation/modelcheck_raw.jsonl`.
  - Live AI: End-to-end inspection test tested against live Ollama (`qwen3:4b`).
- [x] Implemented `src/inspector/ai/derive.py` as single derivation module for production release inspection and evaluation scripts; refactored `scripts/ai_eval/modelcheck.py` and `scripts/ai_eval/modelcheck_report.py`.
- [x] Implemented `src/inspector/ai/worker.py` as isolated subprocess CLI (`python -m inspector.ai.worker`) with JSON-schema structured output, `think: False`, and loopback gating.
- [x] Implemented `src/inspector/ai/client.py` orchestrating worker lifecycle: purpose sanitization (strip control chars, collapse whitespace, cap 300), prompt freeze verification against `docs/ai_prompt_freeze.txt`, scrubbed environment, parent timeout process tree kill, and schema validation with 1 retry.
- [x] Added `ai_error_code` and `ai_model_digest` to `InspectPredicate` in `src/segel_core/schemas/attestation.py` and `InspectionResult` in `src/inspector/inspector.py`.
- [x] Added AI configuration to `src/segel_core/config.py`: `SEGEL_AI_ENABLED` (0), `SEGEL_AI_ENDPOINT` (`http://127.0.0.1:11434`), `SEGEL_AI_MODEL` (`qwen3:4b`), `SEGEL_AI_TIMEOUT_S` (30.0).
- [x] Fixed merge defects in `src/inspector/inspector.py` via `_merge_findings_and_verdict` and documented in `docs/deviations.md` (DEV-13).
- [x] Full test suite: 398 passed across all unit, adversarial, gap, and integration tests.

---

### AI-7: Purpose Sanitization, WARN Acknowledgement, and Release Desk UI
- [x] Manifest purpose control character rejection: Added Pydantic field validator in `src/segel_core/schemas/manifest.py` rejecting ASCII and Unicode control characters (`[\x00-\x1f\x7f-\x9f]`) at manifest creation. Added HTTP 400 rejection in Release Desk `/release/create`. Defense-in-depth sanitization in `src/builder/builder.py`.
- [x] Canonical acknowledgement digest: Implemented `compute_acknowledgement_digest()` in `src/segel_core/canonical.py` computing SHA-256 over canonical sorted unique finding IDs. Extended `ApprovalRequest` and `create_approval_payload()` to carry `acknowledgement_digest`.
- [x] Policy enforcement: Added `require_warn_acknowledgement` (default False, True in demo policy) to `VerificationPolicy`. Ledger gate (`_verify_candidate_evidence`) and Receiver verifier (`verify_passport`) reject empty or mismatching digests with `ErrorCode.DIGEST_MISMATCH` when verdict is WARN.
- [x] Release Desk UI: Added separate labelled "AI advisory" panel in `release_detail.html` displaying predicted purpose class and advisory reason; status banners for failed and skipped states; no confidence percentages; all variables escaped.
- [x] WARN acknowledgement UI: Added WARN findings acknowledgement card in `release_detail.html` displaying acknowledgement digest and acknowledged finding IDs.
- [x] Disclaimer: Added `"Competition prototype for Kartika Cyber Hackathon 2026, not an official product"` to shared layout footer in `src/release_desk/templates/base.html`.
- [x] Documented limitations: Added section 6 in `docs/limitations.md` regarding headless browser screenshot.
- [x] Resolved deviations: Updated `docs/deviations.md` marking DEV-08 and DEV-09 as resolved in AI-7.

### AI-8: Test-Split Evaluation and Adversarial Injection Suite
- [x] Test-split evaluation executed strictly once per D21 across all 36 test items; evaluated baselines B0, B1, B1b, AI alone, and B2; results recorded in `docs/evaluation/testcheck_raw.jsonl` and `docs/evaluation/ai_report.md`.
- [x] Adversarial injection suite: 12 cases evaluated across 4 categories (direct override, persona hijack, context manipulation, obfuscated payload) in `tests/adversarial/test_injection_suite.py` and `scripts/ai_eval/eval_injections.py`; results recorded in `docs/evaluation/injection_results.txt`.

### AI-9a: Claims Audit, Latency Reporting, and Index Documentation
- [x] Replaced headline with script-generated baseline table and pre-registered criterion (D21) in `docs/evaluation/ai_report.md`.
- [x] Generated `docs/evaluation/latency.md` detailing per-item latency, TPS, and >30s outliers.
- [x] Generated `docs/evaluation/README.md` indexing all evaluation artifacts and freeze file hashes.
- [x] Clean-room install procedure clarified in `docs/limitations.md`.
- [x] Sweep of marketing hype words and claim boundaries across `docs/`, `README.md`, `NOTICE`.

### AI-9b: Acceptance Tests and Mutation Testing
- [x] Authored `TestAI9bAcceptance` in `tests/unit/test_ai_inspector.py`:
  - 1. Validator strictness: 8 cases (extra property, missing key, reason of 161 characters, ambiguous string 'false', lowercase class 'l1', class 'L7', empty content, non-object JSON) produce `ai_status="failed"` with distinct error codes (`INVALID_SCHEMA`, `INVALID_CLASS`, `MALFORMED_JSON`) and unchanged deterministic verdicts (`PASS` and `REJECT`).
  - 2. Runtime prompt digest: Untouched prompt matches freeze SHA-256 (`1d4d6da9a11d5586af8111697fd591890bc6bf4d09970dc19a8fbb611226defc`); tampered prompt template copy fails with `PROMPT_FROZEN_MISMATCH`.
  - 3. Timeout enforcement: `SEGEL_AI_TIMEOUT_S=1` against 3.0s sleeping FakeLLM triggers timeout within 1.28s, returns `ai_status="failed"` (`TIMEOUT`), preserves deterministic verdict, and leaves 0 leftover child processes.
  - 4. Disabled flag: `SEGEL_AI_ENABLED=0` produces `ai_status="skipped"`, spawns 0 worker subprocesses, and renders the `"AI Advisory Skipped"` alert banner in the template context.
- [x] Showed red run (2 failures: missing `prompt_file` parameter in `inspect_release` and missing `SEGEL_AI_PROMPT_FILE` support).
- [x] Implemented `prompt_file` and `freeze_file` resolution in `src/inspector/inspector.py:inspect_release`.
- [x] Showed green run (11/11 passed in `TestAI9bAcceptance`).
- [x] Executed mutation testing across all 4 acceptance areas in a throw-away git worktree (`../segel-mutate-ai9b`). Full suite: 433 passed, 0 failed.

---

## Final Status

- All P0 and AI implementation milestones (AI-0 through AI-9b) complete, tested, and mutation-checked.


