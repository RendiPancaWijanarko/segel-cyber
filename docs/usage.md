# Usage Guide

This guide covers operational usage of the SEGEL release distribution platform, including CLI workflows, the Release Desk web interface, and the 5-stamp attestation pipeline.

---

## 1. Core Workflow Overview

A complete release follows an 18-step lifecycle across five independently verifiable stamps:

```
[Author] Manifest Creation (Ed25519)
    │
    ▼
[Builder] Provenance Generation (Origin Stamp)
    │
    ▼
[Inspector] Deterministic Extraction & Policy Rules + Optional AI Advisory (Inspect Stamp)
    │
    ▼
[Approver] Multi-Party M-of-N Approval + WARN Acknowledgement (Approve Stamp)
    │
    ▼
[Ledger] Transparency Merkle Log & Witness Cosignature (Record Stamp)
    │
    ▼
[Passport] Candidate Release Passport Assembly
    │
    ▼
[Canary Receivers] Isolated Canary Deployment & Signed Receipts (Test Stamp)
    │
    ▼
[Promotion] Pre-committed Health Criteria Evaluation & Promotion Record
    │
    ▼
[General Receivers] Offline Verification & Atomic Deployment
```

---

## 2. Configuration & Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `SEGEL_AI_ENABLED` | `1` | `1` to enable local AI purpose classification; `0` to skip AI and operate purely deterministically. |
| `SEGEL_AI_TIMEOUT_S` | `30` | Subprocess timeout in seconds for AI inference requests to Ollama. |
| `SEGEL_AI_PROMPT_FILE` | *(internal)* | Path to the prompt template file (defaults to `docs/evaluation/modelcheck_prompt.txt`). Verified against freeze digest. |
| `SEGEL_AI_FREEZE_FILE` | *(internal)* | Path to the SHA-256 freeze file (defaults to `docs/ai_prompt_freeze.txt`). |

---

## 3. CLI and Programmatic Workflows

### A. Authoring and Building a Release Package
```python
from builder.builder import build_release_package, sign_manifest, sign_origin

files = {
    "baseline.json": b'{"dns_allowlist": ["10.0.0.53"]}'
}

# 1. Package release files and compute canonical manifest digest
build_res = build_release_package(
    files=files,
    release_id="NET-GATEWAY-01",
    sequence=1,
    purpose="Update internal DNS resolvers for branch gateway",
    canary_targets=["canary-1", "canary-2"],
    general_scope=["unit-3"],
)

# 2. Author signs manifest; Builder signs provenance envelope
manifest_env = sign_manifest(build_res, author_key)
origin_env = sign_origin(build_res, builder_key)
```

### B. Inspection and Capability Extraction
```python
from inspector.inspector import inspect_release, create_inspect_attestation, sign_inspect

# Inspect release files: runs deterministic extractors and optional AI advisory
inspection = inspect_release(
    files=files,
    manifest=build_res.manifest,
    manifest_digest=build_res.manifest_digest,
    ai_enabled=True,
)

# Build Inspect in-toto attestation and sign envelope
inspect_stmt = create_inspect_attestation(inspection, build_res.manifest, build_res.manifest_digest)
inspect_env = sign_inspect(inspect_stmt, inspector_key)
```

### C. Air-Gapped Multi-Party Approval
```python
from approver.approver import create_approval_payload, approver_sign, collect_approvals

# Create approval statement and approver payload binding origin and inspect digests
approve_stmt, approve_req = create_approval_payload(
    manifest=build_res.manifest,
    manifest_digest=build_res.manifest_digest,
    origin_envelope=origin_env,
    inspect_envelope=inspect_env,
    inspect_verdict=inspection.verdict,
    canary_targets=["canary-1", "canary-2"],
    promotion_criteria=criteria,
    acknowledgement_digest=ack_digest,  # Bound when inspect verdict is WARN
)

# Approvers review and sign independently
sig0 = approver_sign(approve_req, approver_key_0)
sig1 = approver_sign(approve_req, approver_key_1)

# Collect distinct signatures into Approve envelope
approve_env = collect_approvals(approve_stmt, approve_req, [sig0, sig1])
```

### D. Offline Receiver Verification
```python
from receiver.receiver import Receiver, ReceiverState

receiver_state = ReceiverState(
    unit_id="unit-3",
    unit_role="general",
)

receiver = Receiver(
    state=receiver_state,
    trust_ctx=trust_context,
    receiver_key=receiver_key,
    deploy_root="/opt/segel/app",
)

# Verifies all 5 stamps, anti-rollback sequence, and file digests
verification, receipt_env = receiver.verify_and_deploy(general_passport, files)
assert verification.all_stamps_valid
```

---

## 4. Release Desk Web Interface

The Release Desk (`src/release_desk/app.py`) provides an operational dashboard for monitoring and advancing releases:

1. **Dashboard (`/`)**: Displays active and past releases with current sequence, status, and verification stamps.
2. **Release Creator (`/release/create`)**: Allows submitting a new release manifest with release ID, sequence, purpose, and configuration payload. Control characters in purpose strings are rejected.
3. **Release Detail (`/release/{release_id}`)**:
   - Detailed status of the 5 stamps (Origin, Inspect, Approve, Record, Test).
   - **Deterministic Findings**: Table of extracted capabilities and policy rule evaluations.
   - **AI Advisory Panel**: Dedicated advisory box displaying the predicted purpose class (`L1`..`L6`), advisory text explanation, and fail/skip banners when AI is unconfigured or disabled.
   - **Acknowledgement Interface**: Review and sign off on advisory warnings before approval when required by policy.
   - **Passport Download**: Export candidate or general release passports as signed JSON envelopes.

---

## 5. Security Principles in Daily Operations

1. **AI Output Is Non-Authoritative**: The AI model (`qwen3:4b`) provides advisory commentary only. A classification of `L6` produces an advisory `WARN`; it cannot reject a release or override human approver quorums.
2. **Fail-Closed Handling**: Any failure in network connection to Ollama, model output parsing, timeout (>30s), or prompt digest mismatch results in `ai_status="failed"` without modifying deterministic verdicts.
3. **No Private Keys in Release Desk**: The Release Desk process does not hold private signing keys. All signing takes place in isolated worker functions or simulated air-gapped approver signers.
