# AI Assistance & Authorship Transparency Disclosure

In compliance with competition transparency standards and responsible AI engineering principles, this document discloses the division of responsibilities between human engineering oversight and the AI coding agent in the development of SEGEL.

---

## 1. Overview & Transparency Statement

- **Development Tool**: Google Antigravity (Advanced Agentic Coding, DeepMind).
- **Primary Authorship Model**: An autonomous AI coding agent wrote and modified source code, automated test suites, documentation files, and evaluation scripts under continuous, granular human engineering direction, architectural specifications, and interactive review.
- **Human Authority**: All architectural choices, cryptographic constraints, pre-registered evaluation decisions (`docs/ai_decisions.md`), security boundary definitions, and acceptance of commits were directed and reviewed by human engineers.

---

## 2. Division of Responsibilities

### 2.1 Human Engineering Responsibilities
1. **Architectural Specification & Requirements**: Formulated system specifications in PRD v2.0, Technical Architecture Specification (TAS), and Master Demonstration Blueprint (MDB).
2. **Pre-Registered Design Decisions**: Fixed decisions D1 through D22 prior to implementation, establishing strict invariants (e.g., severity capping, prompt freezing, key isolation, fail-closed handling).
3. **Task Scoping & Workflow Control**: Defined granular prompt tasks, constrained modifications to specific functional units, and prohibited unauthorized external dependencies.
4. **Code & Diff Review**: Examined diffs, verified adherence to security boundaries, inspected test execution results, and authorized git commits.
5. **Specification Drift Resolution**: Governed specification vs. implementation deviations (`docs/deviations.md`), ensuring discrepancies were explicitly documented rather than silently resolved.

### 2.2 AI Coding Assistant Responsibilities
1. **Code Implementation**: Authored Python modules in `src/` conforming to Pydantic v2 schemas, cryptographic protocols (RFC 8032, DSSE, RFC 6962), and modular architecture.
2. **Test-First Development**: Authored failing tests first for every new functional behavior, demonstrated the red test run, implemented minimal code to pass, and demonstrated the green test run.
3. **Mutation Testing**: Conducted mutation verification across acceptance tests within isolated, throw-away git worktrees to prove test sensitivity.
4. **Automated Evaluation Scripts**: Implemented and executed baseline evaluation pipelines (`scripts/ai_eval/`) for deterministic baselines (B0, B1, B1b) and the local AI model (`qwen3:4b`).
5. **Documentation & Traceability**: Drafted guides, cross-reference tables, and API documentation directly reflecting the codebase state without hallucinated metrics.

---

## 3. Security Invariants & Boundaries Enforced During AI Generation

Throughout all AI-assisted coding turns, the following strict behavioral invariants were enforced:

1. **No Custom Cryptography**: All cryptographic operations rely strictly on standard algorithms (`cryptography` library implementation of RFC 8032 Ed25519, SHA-256, DSSE).
2. **Fail-Closed by Design**: All error conditions, schema discrepancies, timeout events, or cryptographic mismatches terminate execution with stable error codes and zero state mutation.
3. **Frozen Test Splits**: Corpus files designated as frozen (`docs/ai_corpus_freeze.txt` and `TEST-*.json`) were strictly read-only and never modified to accommodate model behaviors.
4. **Zero Key Exposure**: AI subprocesses operate in scrubbed environments with no access to private signing keys, credentials, or tokens.
5. **Non-Authoritative AI Output**: AI inference output is strictly advisory, capped at severity `warn`, and can never override deterministic gates, escalate to `reject`, or lower a finding.
6. **No Memorized Metrics**: All numerical figures, counts, and evaluation metrics reported in documentation were extracted directly from script-generated output files.
