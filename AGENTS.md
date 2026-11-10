RULES
Source of truth: PRD v2.0, TAS, MDB (docs/prd if present) and docs/ai_decisions.md. If code and docs disagree, record it in docs/deviations.md; never silently choose.
Scope: only the task in the current prompt. No extra features, refactors, or dependencies. Stop and report before adding any dependency.
Security: no custom cryptography; fail closed with stable error codes and no state change; ignore DSSE keyid and count distinct authorised keys; strict base64; no wall-clock use in security decisions;
AI output is advisory and capped at severity warn; the AI never signs, never holds or sees keys, never deploys; no secrets in logs, tests, fixtures, or docs.
Testing: tests first for every new behaviour (show the red run); never edit a test to make it pass unless the prompt allows it and you justify it in docs/ai_state.md;
frozen files (docs/ai_corpus_freeze.txt and the corpus test split once frozen) are read-only; run the full suite after every unit; show command output as evidence.
Honesty: never write "secure", "verified", "guaranteed", "zero defect", or "100% compliant"; state what a named test shows, or name the limitation. Report raw counts and negative results.
Hygiene: relative paths only in docs; no absolute local paths, usernames, tokens, or file:// links; commit per logical unit with message "<ID>: <what>"; never force-push or rewrite history.
Network: the only network access allowed is HTTP to 127.0.0.1:11434 (local Ollama). No downloads and no package installs unless I say so.
Every task ends with a block titled REPORT FOR REVIEW containing exactly what the prompt asks for, then `git status` and `git diff --stat`.
