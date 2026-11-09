DECISIONS
D1 Execution: AI runs in a separate subprocess worker (`python -m inspector.ai.worker`) with a scrubbed environment and never receives keys; it talks only to loopback Ollama. The Desk process still holds the other demo keys (documented limitation).
D2 Capabilities: keep existing kind names (network_listen, file_write, external_connect, credential_reference, privilege_escalation); add dns_allowlist_change, outbound_rule_added, account_added, privilege_granted, logging_changed,
   logging_disabled, service_enabled, service_disabled, scheduled_task_added, trust_anchor_added, broad_change. Instance IDs are `<kind>#<n>`. Docs follow code (K01..K10 is not renamed into code).
D3 Baseline v1 format: JSON parsed with stdlib json, duplicate keys rejected; not YAML. Record as a deviation.
D4 Inspect predicate: keep flat fields; add ai_model_digest and ai_error_code; no predicate version bump.
D5 AI authority: AI-derived findings have severity warn at most; AI can never produce REJECT or lower a verdict; AI findings are recorded exactly as produced (never overwritten). Fix the two defects in the merge logic of src/inspector/inspector.py.
D6 The deterministic expectation check (keyword classifier B1 + expectation map) is part of the deterministic verdict and abstains when no class is found. AI-derived findings are unioned on top, so AI can only add.
D7 ai_status: skipped = AI disabled by configuration; failed = enabled but error, timeout, or invalid output. Verdict is unaffected. AI_FAILED is informational.
D8 WARN acknowledgement: Desk and approver require acknowledging every WARN finding and sign acknowledgement_digest. Policy flag require_warn_acknowledgement (default false; true in the demo policy) makes ledger and Receiver verify it.
D9 Corpus: 6 few-shot exemplars plus 60 evaluation items (30 consistent, 30 inconsistent), split 24 dev / 36 test. Raw counts only; small-N limitation stated.
D10 Time boxes: AI feature freeze on Wednesday 11 November. If the model check fails, switch to Plan B. Anything unfinished becomes a documented limitation.
D11 Model: `qwen3:4b` via Ollama at 127.0.0.1:11434, think=false, temperature 0, seed 1, num_ctx 2048, num_predict 200, keep_alive 30m, request timeout 30 s, JSON-schema structured output plus our own validator.
   No ensemble, no second model. Weights are never committed; NOTICE records name, digest, and licence (Apache-2.0 as reported by the model card; to be verified).
D12 Latency: partial CPU offload on the 4 GB GPU is acceptable. The call is synchronous with a 30 s timeout; a timeout gives ai_status failed.
D13 Model task: classify the purpose into L1..L6, plus an ambiguous flag and a short Indonesian reason. Code derives unexpected capabilities, consistency, and findings from the expectation map.
   The model is never asked for them; its reason is shown as advisory text only.
D14 Prompt: contains definitions of L1..L6 and 3 few-shot exemplars from the exemplar set (one Indonesian paraphrase, one English, one vague/L6). The template lives in a file whose SHA-256 is recorded in ai_prompt_digest.
D15 Vague purposes: L6 = vague or other. L6 plus any capability yields a deterministic WARN "purpose too vague to verify".
D16 Sanitisation: reject control characters in manifest purpose at creation; strip them again in the AI input builder; cap length at 300; escape in templates.
D17 Classes: L1 DNS allowlist update (expects dns_allowlist_change); L2 operator account change (account_added); L3 non-weakening logging adjustment (logging_changed);
   L4 network rule addition (outbound_rule_added); L5 hardening by disabling services (service_disabled); L6 vague or other (nothing expected).
   privilege_granted, logging_disabled, trust_anchor_added, service_enabled, scheduled_task_added and broad_change are never expected by any class.
D18 UI: all other UI work is frozen. Only the AI panel, the ai_status banner, the acknowledgement control, and a "competition prototype, not an official product" disclaimer are allowed.
D9b: evaluation set stays 60 items (30 consistent, 30 inconsistent; dev 24, test 36) but inconsistent items are rebalanced so that most test AI value (silent mismatches); controls for the deterministic layer are kept.
D19 Model-check PASS rule: PASS iff (1) schema validity >= 95%, (2) false positives <= 2 of the 12 consistent DEV items, (3) B1 union AI detects at least 6 of the 7 silent DEV items (B1 alone detects 4). "Detected" = at least one expectation-mismatch finding after code derivation.

