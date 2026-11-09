# Specification vs Implementation Deviations

This document catalogues every known drift between the specifications (PRD v2.0, TAS, MDB) and the codebase implementation. Per project rules, deviations are explicitly recorded here and governed by the architectural decisions in `docs/ai_decisions.md`.

---

## DEV-01: Predicate Type URN Scheme

- **Specification**: TAS specifies the URN scheme `urn:segel:inspect:v1` for the inspection attestation predicate.
- **Codebase**: `src/segel_core/schemas/attestation.py` defines `INSPECT_PREDICATE_TYPE = "https://segel.dev/attestation/inspect/v1"`.
- **Drift**: Code uses an HTTPS URL scheme (`https://segel.dev/attestation/{type}/v1`) across all predicate types (`origin`, `inspect`, `approve`, `record`, `test`) rather than URN format `urn:segel:...`.
- **Governing Decision**: Decision D4. Flat fields and existing predicate URI schemes are retained; no predicate version bump.
- **Impact**: All downstream verifiers (`src/segel_core/verification/passport.py`, `src/ledger/ledger.py`) match `https://segel.dev/attestation/inspect/v1`. Changing this string would invalidate existing test assertions and envelopes.

---

## DEV-02: DSSE Envelope payloadType for Attestations

- **Specification**: TAS §7.2 specifies the standard in-toto Statement envelope payloadType `application/vnd.in-toto+json` (per in-toto ITE-2).
- **Codebase**: `src/inspector/inspector.py` and `src/segel_core/schemas/attestation.py` use `application/vnd.segel.inspect+json` (and `application/vnd.segel.{stamp}+json` for other stamps).
- **Drift**: Custom MIME types are used per stamp instead of the uniform `application/vnd.in-toto+json` envelope type wrapping an in-toto v1 Statement.
- **Governing Decision**: Decision D4 / TAS accommodation. Existing DSSE payload types are maintained to prevent schema mismatch rejections (`SCHEMA_UNKNOWN`).
- **Impact**: Verifiers assert exact match against `application/vnd.segel.inspect+json`. Preserved across all test suites.

---

## DEV-03: Capability Taxonomy and Identifier Format

- **Specification**: TAS and PRD define capability taxonomy `K01..K10` with instance numbers (e.g., `K01#1`, `K02#1`).
- **Codebase**: `src/inspector/inspector.py` uses semantic snake_case identifiers: `network_listen`, `file_write`, `external_connect`, `credential_reference`, `privilege_escalation`.
- **Drift**: Code uses descriptive names rather than `K01..K10` enumeration codes.
- **Governing Decision**: Decision D2. Keep existing kind names (`network_listen`, `file_write`, `external_connect`, `credential_reference`, `privilege_escalation`) and add `dns_allowlist_change`, `outbound_rule_added`, `account_added`, `privilege_granted`, `logging_changed`, `logging_disabled`, `service_enabled`, `service_disabled`, `scheduled_task_added`, `trust_anchor_added`, `broad_change`. Instance IDs follow `<kind>#<n>`. Documentation follows code; `K01..K10` is not renamed into code.
- **Impact**: Retains compatibility with existing tests checking capability dictionaries while supporting instance tracking.

---

## DEV-04: Runtime Python Version

- **Specification**: PRD v2.0 §9.1 and §14.1 specify Python 3.12 as the target execution environment.
- **Codebase / Host**: The active virtual environment runs Python 3.14.6 (`.venv/Scripts/python.exe`). `pyproject.toml` configures ruff and mypy targets to `py312`.
- **Drift**: Host runtime is Python 3.14 rather than 3.12.
- **Governing Decision**: D-002 and runtime baseline accommodation. Code avoids 3.14-only syntax and remains compatible with 3.12, but tests execute under 3.14.6.
- **Impact**: Pytest-asyncio displays deprecation warnings for `asyncio_default_fixture_loop_scope` under Python 3.14. RFC 8032 test vectors require output-matching rather than intermediate public key comparison (documented in `docs/DECISIONS.md:D-002`).

---

## DEV-05: Baseline v1 Configuration File Format

- **Specification**: TAS specifies YAML format (`.yaml` / `.yml`) for Baseline v1 configuration payloads.
- **Codebase**: `src/receiver/adapter/baseline.py` parses baseline configurations as JSON using Python stdlib `json`.
- **Drift**: Configuration payload is JSON rather than YAML.
- **Governing Decision**: Decision D3. Baseline v1 format uses JSON parsed with stdlib `json`, with duplicate keys rejected; not YAML.
- **Impact**: Eliminates a third-party YAML parser dependency (such as PyYAML), enforces deterministic canonical serialization, and avoids YAML parsing ambiguities.

---

## DEV-06: Inspect Predicate AI Fields Structure

- **Specification**: TAS specifies a nested `ai` object block (`ai: { status, model_id, prompt_digest, model_digest, findings }`) inside the Inspect predicate.
- **Codebase**: `src/segel_core/schemas/attestation.py` defines flat fields directly on `InspectPredicate`: `ai_findings`, `ai_status`, `ai_model_id`, `ai_prompt_digest`.
- **Drift**: AI fields are flat attributes on `InspectPredicate` rather than a nested sub-object.
- **Governing Decision**: Decision D4. Keep flat fields; add `ai_model_digest` and `ai_error_code`; no predicate version bump.
- **Impact**: Avoids breaking passport verifiers and Ledger FR-051 admission checks that access flat fields.

---

## DEV-07: Predecessor Manifest Diffing

- **Specification**: PRD v2.0 FR-014 requires comparing release payloads against predecessor manifests to identify delta modifications.
- **Codebase**: `src/inspector/inspector.py` inspects files present in the current release payload standalone, without loading or diffing against prior sequence manifests.
- **Drift**: Predecessor diffing is omitted; each sequence evaluates only its own file set.
- **Governing Decision**: Documented limitation (`docs/limitations.md`). Sequence 1+ releases evaluate standalone payloads.
- **Impact**: Capabilities reflect current release archive contents rather than delta relative to previous version.

---

## DEV-08: Manifest Purpose Control Character Sanitization

- **Specification**: PRD v2.0 FR-012 and SEC-013 require strict input sanitization of release purpose strings.
- **Codebase**: `src/segel_core/schemas/manifest.py` limits `purpose` to `max_length=300` but does not reject ASCII control characters (`\x00-\x1f`, `\x7f`).
- **Drift**: Schema accepts control characters if within the 300-character limit.
- **Governing Decision**: Decision D16. Reject control characters in manifest purpose at creation; strip them again in the AI input builder; cap length at 300; escape in templates.
- **Impact**: Prevents prompt injection, escape-sequence smuggling, and log injection attacks.

---

## DEV-09: WARN Finding Acknowledgement Enforcement

- **Specification**: PRD v2.0 FR-035 specifies that WARN findings require explicit acknowledgement signed by approvers before deployment.
- **Codebase**: `ApprovePredicate.acknowledgement_digest` is defined in `src/segel_core/schemas/attestation.py` with default `""`, but `src/approver/approver.py` does not populate it, and verifiers do not mandate it.
- **Drift**: WARN acknowledgement digest is optional and unpopulated in existing release flows.
- **Governing Decision**: Decision D8. Desk and approver require acknowledging every WARN finding and signing `acknowledgement_digest`. Policy flag `require_warn_acknowledgement` (default false; true in demo policy) makes Ledger and Receiver check it.
- **Impact**: Establishes a verifiable chain from advisory findings through human approval to deployment.

---

## DEV-10: Trust Root Transition Chain Validation

- **Specification**: PRD v2.0 SEC-035 mandates that new trust roots must be signed by an M-of-N threshold of both the previous root keys and the new root keys.
- **Codebase**: `src/segel_core/verification/trust.py` checks root version monotonically increasing, but multi-root transition signature chains are not evaluated.
- **Drift**: Dynamic in-band root key rollover with dual-threshold validation is not implemented.
- **Governing Decision**: Hardening limitation (`docs/limitations.md`). Root trust is provisioned statically out-of-band for the MVP.
- **Impact**: Key compromise requires manual out-of-band trust root redistribution.

---

## DEV-11: Key Separation in Demo Web Process

- **Specification**: PRD v2.0 SEC-004 mandates strict role-based key separation across independent processes.
- **Codebase**: While approver signing was separated into `StandaloneApproverSigner`, the Release Desk process still holds `author_key`, `builder_key`, `inspector_key`, `ledger_key`, and `witness_key` in `DemoKeyBundle` heap memory (`src/release_desk/app.py`).
- **Drift**: Multiple signing roles share a single web service memory boundary in the demo harness.
- **Governing Decision**: Decision D1. AI runs in a separate subprocess worker (`python -m inspector.ai.worker`) with a scrubbed environment and never receives keys; it talks only to loopback Ollama. The Desk process still holds the other demo keys (documented limitation).
- **Impact**: AI execution has zero access to signing keys, even if the model produces unexpected outputs or is compromised by malicious prompts.

---

## DEV-12: Receiver Concurrency Deployment Locking

- **Specification**: PRD v2.0 FR-072 requires persistent state and deployment operations to be crash-safe and race-free.
- **Codebase**: `src/receiver/receiver.py` writes state atomically via rename, but does not acquire a file lock on `<deploy_root>/.lock` during staging and apply operations.
- **Drift**: Concurrent invocations of `Receiver.verify_and_deploy` on the same unit could race during staging and backup phases.
- **Governing Decision**: Documented in `docs/audit.md:238`. Deployments are intended for sequential single-operator execution in the MVP.
- **Impact**: Parallel deployment commands on the same host must be prevented by operational discipline or wrapper scripts.
