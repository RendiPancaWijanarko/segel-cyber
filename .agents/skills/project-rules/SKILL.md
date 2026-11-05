---
name: project-rules
description: Aturan utama proyek SEGEL, panduan PRD v2.0, aturan keamanan kriptografi (Ed25519, SHA-256, DSSE), aturan testing, dan standar implementasi P0.
---

# SEGEL project rules
Source of truth: PRD v2.0, TAS, MDB (docs/prd). If code and docs disagree, report it; do not silently choose.
Scope: P0 only unless I say otherwise. Do not add features, dependencies, or refactors without asking.
Security rules (non-negotiable):
- No custom cryptography. Use the `cryptography` library. Ed25519, SHA-256, DSSE per TAS section 6.
- Fail closed: any parse error, unknown field, or mismatch means rejection with a stable error code and NO state change.
- Ignore DSSE `keyid`; count DISTINCT authorised keys; strict base64; check payloadType exactly.
- Never read wall-clock time in a security decision.
- AI output can only add findings or raise severity; it never lowers a verdict, signs, or deploys.
- No secrets in logs, tests, or fixtures. segel_core imports no other package and no network modules.
Testing rules: never edit tests to make them pass. If a test is wrong, explain and ask. Show command output as evidence.
Labelling: if something is a stub, label it in the UI and docs ("not implemented in this submission").
