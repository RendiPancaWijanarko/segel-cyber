# SEGEL Design Decisions

This document records technical decisions made during MVP development.

## D-001: Modular Monolith Over Microservices

**Decision**: Implement as a modular monolith with clear package boundaries.

**Rationale**: PRD v2.0 explicitly mandates "No microservices or Kubernetes for the MVP." The modular monolith provides clear component boundaries (builder, inspector, approver, etc.) while keeping deployment simple and dependencies minimal.

**Trade-off**: Cannot scale individual components independently, but MVP does not require this.

## D-002: Ed25519 Test Vector Accommodation

**Decision**: Verify Ed25519 correctness via signature output matching rather than intermediate public key derivation.

**Rationale**: Python's `cryptography` library (v49.0.0 on Python 3.14) derives a public key from the RFC 8032 Test Vector 1 seed that differs from the RFC-published public key. However, the computed signature is bit-identical to the RFC expected output. This is a library/platform difference in how the seed-to-key expansion is handled, not a security issue.

**Impact**: None — signatures verify correctly, and key_id derivation uses the library's own consistent public key bytes.

## D-003: Canonical JSON for Deterministic Serialization

**Decision**: Use canonical JSON (sorted keys, no whitespace, UTF-8) as the deterministic serialization format for all content that gets signed.

**Rationale**: JSON is human-readable and widely supported. The canonical form ensures that the same logical content always produces the same byte sequence, which is critical for signature verification. PRD v2.0 specifies JSON Schema as the schema language.

**Alternative considered**: CBOR — included as a dependency but not used for attestation payloads in the MVP.

## D-004: In-Memory Merkle Tree with SQLite Backing

**Decision**: Maintain the Merkle tree in memory, backed by SQLite for persistence.

**Rationale**: The in-memory tree provides fast proof generation. SQLite provides durable storage. On startup, entries are loaded from SQLite into the in-memory tree. SQLite triggers prevent accidental deletion/modification but are explicitly NOT a security boundary (SEC-018).

**Trade-off**: In-memory tree limits scale to available RAM, but MVP volumes are tiny.

## D-005: PAE-Based Approval Signing

**Decision**: Approvers sign the DSSE PAE (Pre-Authentication Encoding) of the approval payload, not the raw payload.

**Rationale**: This matches DSSE convention — signatures in a DSSE envelope are always over PAE(payload_type, payload), not over raw payload bytes. This ensures that the approval signature can be collected externally (on the approver's device) and assembled into a valid DSSE envelope by the Release Desk.

## D-006: Baseline Adapter 10-Step Lifecycle

**Decision**: Implement a rigid 10-step deployment lifecycle in the Baseline Adapter: preflight → snapshot → stage → validate → backup → apply → health_check → commit/rollback → cleanup.

**Rationale**: PRD v2.0 requires recoverable deployment with backup and rollback. The fixed lifecycle ensures that every deployment follows the same safety sequence, and any failure triggers rollback to the pre-deployment state.

## D-007: Trust Context as Single Verification Entry Point

**Decision**: Centralize trust lookups in `TrustContext` which wraps `TrustRoot`, `VerificationPolicy`, and `TrustSnapshot`.

**Rationale**: Every verification operation needs access to keys, roles, thresholds, and policy. Having a single context object prevents components from cherry-picking which trust information they use, and makes it impossible to verify against outdated or partial trust state.

## D-008: Eligibility Classification

**Decision**: Passport verification produces an `EligibilityClass` enum (ELIGIBLE_CANARY, ELIGIBLE_GENERAL, INELIGIBLE) rather than a simple pass/fail.

**Rationale**: A candidate passport is valid for canary targets but not for general deployment. A general passport is valid for all targets. The eligibility class captures this nuance and allows the receiver to make the correct deployment decision based on passport type and unit role.

## D-009: Evidence Binding via Binding Block

**Decision**: Every attestation includes a `BindingBlock` with `{stamp, subject: {release_id, sequence, manifest_sha256}, trust_root_version, policy_version, evidence_id}`.

**Rationale**: Binding blocks prevent evidence transplant attacks — an Origin attestation for release A cannot be reused for release B because the manifest_sha256 won't match. The evidence_id provides uniqueness for audit trails.

## D-010: Jinja2 + HTMX Over React

**Decision**: Use server-side Jinja2 templates with HTMX for interactivity.

**Rationale**: PRD v2.0 specifies "Jinja2 and HTMX for the initial UI." This keeps the frontend dependency-free (no build step, no node_modules) and maintains the modular monolith architecture without introducing a separate frontend build pipeline.

---

# Hardening Pass Decisions (Phase A–F)

## D1: SEC-004 Key Separation Scope
- **Decision**: Move only approver keys out of the Release Desk process into a separate signer process (`approver`).
- **Limitation**: The remaining keys in the demo harness (builder, inspector, ledger, witness) will remain in the demo harness and be explicitly documented as a limitation in `docs/limitations.md`.

## D2: AI Deterministic Isolation Scope
- **Decision**: The AI pipeline remains deterministic-only for the MVP. Tests AT-016 through AT-019 are relabelled "validator-level" and listed under limitations.
- **Rule**: Do not implement an external LLM / AI service pipeline.

## D3: Crash-Safe Journal & Audit Log
- **Decision**: Implement the crash-safe journal (FR-083) and the hash-chained audit log (SEC-017). If any blocker emerges, document as a limitation and report to the user.

## Open Hardening Decisions
*(Items identified during Phase A will be recorded below with options and recommendations before Gate 1).*

