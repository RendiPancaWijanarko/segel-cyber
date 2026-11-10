# SEGEL Architecture & System Specification

> **Sistem Edar Gelar Elektronik Lapis-ganda** — Hardened Configuration & Release Distribution Platform
> Conforming to PRD v2.0, Technical Architecture Specification (TAS), and Recorded Decisions.

---

## 1. High-Level Architecture

SEGEL implements a **security-core-first modular monolith** architecture. Configuration releases are subject to strict cryptographic non-repudiation, policy enforcement, multi-party air-gapped approval, public ledger transparency, and offline receiver validation before deployment.

```
                    ┌─────────────────────────────────────────────┐
                    │              SEGEL Architecture              │
                    ├─────────────────────────────────────────────┤
                    │                                             │
 ┌──────────┐       │  ┌─────────┐   ┌──────────┐   ┌─────────┐   │
 │  Author  │──────┼─▶│ Builder │──▶│Inspector │──▶│Approver │   │
 │  Signer  │      │  └────┬────┘   └────┬─────┘   └────┬────┘   │
 └──────────┘       │       │              │              │       │
                    │       ▼              ▼              ▼       │
                    │  ┌─────────────────────────────────────┐    │
                    │  │       Transparency Ledger            │    │
                    │  │    (Merkle log + signed checkpoints) │    │
                    │  └─────────────┬───────────────────────┘    │
                    │                │                            │
                    │       ┌────────┴────────┐                   │
                    │       │    Witness       │                   │
                    │       │  (cosigner)      │                   │
                    │       └─────────────────┘                   │
                    │                                             │
                    │  ┌──────────────────────────────────────┐   │
                    │  │      Passport Assembler              │   │
                    │  │  (candidate & general passports)     │   │
                    │  └────────────────┬─────────────────────┘   │
                    │                   │                          │
                    └───────────────────┼──────────────────────────┘
                                        │
                    ┌───────────────────┼──────────────────────────┐
                    │                   ▼                          │
                    │  ┌────────────────────────────────────┐     │
                    │  │     Promotion Controller           │     │
                    │  │  (canary health → general release) │     │
                    │  └─────────────┬──────────────────────┘     │
                    │                │                             │
                    │     ┌──────────┼──────────┐                 │
                    │     ▼          ▼          ▼                 │
                    │  ┌──────┐  ┌──────┐  ┌──────┐             │
                    │  │Can-1 │  │Can-2 │  │Unit-3│             │
                    │  │(rcvr)│  │(rcvr)│  │(rcvr)│             │
                    │  └──────┘  └──────┘  └──────┘             │
                    │     Offline Receivers                       │
                    └─────────────────────────────────────────────┘
```

---

## 2. Component Zones & Security Boundaries

| Zone | Component | Trust Level | Boundaries & Responsibilities |
|------|-----------|-------------|-------------------------------|
| **Z1** | **SEGEL Core** | Trusted Core | Cryptographic primitives (RFC 8032 Ed25519, DSSE, RFC 6962 Merkle log), canonical JSON serialization, schema models, and passport verification logic. |
| **Z2** | **Signer Processes** | Isolated | Dedicated processes or hardware modules for Author, Builder, Inspector, and Approver keys. |
| **Z3** | **Release Desk** | Untrusted Presentation | FastAPI / Jinja2 orchestrator and operator interface. **NEVER holds or sees private keys**. |
| **Z4** | **Inspector Engine** | Trusted | Deterministic capability extraction (`CAPABILITY_RULES`) and policy rule checks (`PRULE-001`..`PRULE-004`). |
| **Z5** | **AI Sandbox** | Untrusted Advisory | Local Ollama subprocess (`qwen3:4b`). No signing keys, no network outside loopback `127.0.0.1:11434`, output strictly capped at `warn`. |
| **Z6** | **Transparency Ledger** | Trusted | Append-only SQLite log + RFC 6962 Merkle tree with signed checkpoints. |
| **Z7** | **Witness** | Isolated | Independent checkpoint cosigner validating consistency proofs. |
| **Z8** | **Passport Assembler** | Trusted | Packages candidate and general release passports containing cryptographic evidence envelopes. |
| **Z9** | **Offline Receivers** | Trusted Edge | Autonomous units operating disconnected from central network; independently verify all stamps before staging and committing configuration updates. |

---

## 3. The 5-Stamp Attestation Pipeline

Every configuration deployment requires five sequential, cryptographically bound stamps:

```
  Origin    →    Inspect    →    Approve    →    Record    →    Test
  ┌────┐        ┌────────┐      ┌────────┐     ┌──────┐      ┌────┐
  │ 🏭 │───────▶│  🔍   │─────▶│  ✅   │────▶│  📜 │─────▶│ 🧪 │
  └────┘        └────────┘      └────────┘     └──────┘      └────┘
  Builder       Inspector       2-of-3         Merkle log    Canary
  signs         extracts        approvers      + witness     deploy
  provenance    capabilities    sign           cosign        + health
```

1. **Origin Stamp (`origin`)**: Signed by Builder. Binds release files and author manifest digest into an in-toto v1 Statement wrapped in DSSE.
2. **Inspect Stamp (`inspect`)**: Signed by Inspector Signer. Contains deterministic policy evaluations and optional AI advisory purpose classification.
3. **Approve Stamp (`approve`)**: Signed by an M-of-N quorum (default 2-of-3) of air-gapped Approvers. Binds origin evidence digest, inspect evidence digest, and `acknowledgement_digest` (when warnings are present).
4. **Record Stamp (`record`)**: Transparency Ledger Merkle inclusion proof and signed checkpoint, cosigned by independent Witness.
5. **Test Stamp (`test`)**: Deployment receipts and health attestation from canary units certifying safe operation.

---

## 4. Cryptographic Standards and Primitives

- **Digital Signatures**: Ed25519 per RFC 8032.
- **Key Identity**: Raw 32-byte public key hashed with SHA-256 (`SHA-256(raw_bytes)` per SEC-033).
- **Attestation Wrapping**: Dead Simple Signing Envelope (DSSE).
- **Statement Structure**: in-toto Statement v1 (`https://in-toto.io/Statement/v1`).
- **Transparency Tree**: Append-only binary Merkle tree per RFC 6962 with leaf prefix `\x00` and node prefix `\x01`.
- **Consistency Proofs**: RFC 9162 logarithmic audit paths.
- **Checkpoints**: C2SP tlog-checkpoint format with Ed25519 ledger signature and witness cosignature extension.
- **Canonical Serialization**: Canonical JSON with sorted object keys and no insignificant whitespace.

---

## 5. AI Advisory Subsystem Architecture

The AI Inspector provides auxiliary purpose classification to detect discrepancies between declared release intentions and extracted technical capabilities:

1. **Execution Model**: The inspector spawns a scrubbed subprocess (`python -m inspector.ai_worker`) communicating via HTTP loopback exclusively to `http://127.0.0.1:11434`.
2. **Environment Scrubbing**: All process environment variables containing keys, secrets, tokens, or credentials are stripped before spawning.
3. **Prompt Integrity**: The exact prompt template (`docs/evaluation/modelcheck_prompt.txt`) is verified against its runtime SHA-256 freeze hash in `docs/ai_prompt_freeze.txt`. Mismatches abort inference with `ai_status="failed"` and `ai_error_code="PROMPT_TAMPERED"`.
4. **Strict Schema Validation**: Model JSON responses are validated against exact Pydantic schema rules: class must be `L1`..`L6`, reasons capped at 160 characters, ambiguous boolean flag.
5. **Derivation Mapping**: Findings are derived strictly by `derive_findings(class, capabilities)` using the deterministic `EXPECTATION_MAP`. The model's natural language reason is advisory and cannot influence rules.
6. **Severity Capping**: Findings produced by the AI inspector are strictly capped at `severity="warn"`. The AI subsystem can NEVER emit a `reject` finding and can NEVER lower a deterministic finding.

---

## 6. Specification vs Implementation Deviations (TAS / PRD)

All architectural deviations are recorded in `docs/deviations.md` and governed by `docs/ai_decisions.md`:

| Deviation ID | Specification Reference | Codebase Implementation | Rationale / Governing Decision |
|--------------|-------------------------|-------------------------|--------------------------------|
| **DEV-01** | `urn:segel:inspect:v1` predicate URN | `https://segel.dev/attestation/inspect/v1` | Retain established URI scheme; avoid breaking verifier assertions (D4). |
| **DEV-02** | `application/vnd.in-toto+json` envelope | `application/vnd.segel.{stamp}+json` | Stamp-specific MIME types preserved to prevent `SCHEMA_UNKNOWN` (D4). |
| **DEV-03** | `K01..K10` capability taxonomy codes | Semantic snake_case (`network_listen`, `dns_allowlist_change`) | Code uses semantic identifiers with `<kind>#<n>` instance numbering (D2). |
| **DEV-04** | Python 3.12 target runtime | Tested under Python 3.14.6 on Windows | Host platform baseline; code avoids 3.14-only syntax (D-002). |
| **DEV-05** | YAML Baseline v1 format | JSON parsed with stdlib `json` | Eliminates external YAML parser dependency, ensures deterministic serialization (D3). |
| **DEV-06** | Nested `ai` object in Inspect predicate | Flat fields (`ai_findings`, `ai_status`, `ai_model_id`) | Maintains backwards compatibility with Ledger and Passport schemas (D4). |
| **DEV-07** | Predecessor manifest diffing | Standalone file evaluation | Releases evaluate complete payload without historical diffing (`docs/limitations.md`). |
| **DEV-08** | Manifest purpose sanitization | Control character validation & stripping | Pydantic validator rejects `[\x00-\x1f\x7f-\x9f]` at creation; builder sanitizes (D16). |
| **DEV-09** | WARN finding acknowledgement | Signed `acknowledgement_digest` bound in approval | Policy flag `require_warn_acknowledgement` enforces signed digest match (D8). |
| **DEV-10** | In-band trust root transition chains | Monotonic root version check | Out-of-band trust root provisioning in prototype (`docs/limitations.md`). |

---

## 7. Error Handling & Failure Semantics

All system operations fail closed. When any cryptographic check, schema validation, policy threshold, or anti-rollback rule is violated, processing terminates without state mutation. Standardized error codes are defined in `segel_core.errors.ErrorCode`:

- `ENVELOPE_INVALID`, `SIGNATURE_INVALID`, `DIGEST_MISMATCH`
- `UNAUTHORIZED_KEY`, `KEY_REVOKED`, `THRESHOLD_NOT_MET`
- `POLICY_VIOLATION`, `UNACKNOWLEDGED_WARNING`
- `EPOCH_EXPIRED`, `SEQUENCE_REPLAY`
- `MERKLE_PROOF_INVALID`, `CHECKPOINT_INVALID`
- `PROMOTION_CRITERIA_UNMET`, `STATE_CORRUPT`
