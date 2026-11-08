# SEGEL AI-Inspector Reconnaissance Summary

### 1. Environment & Test/Lint Baseline (5 Lines)
- **Runtime**: Python 3.14.6 | `httpx` 0.28.1, `requests` 2.34.2, `pydantic` 2.14.2 | `psutil` & `jsonschema`: NOT INSTALLED
- **Compute & Daemon**: RTX 3050 Laptop GPU (4.0 GB VRAM, Driver 621.01, CUDA 13.5) | Ollama: NOT INSTALLED / NOT RUNNING
- **Static Analysis**: `mypy src`: 0 errors (46 files) | `bandit -r src`: 0 issues | `ruff`: 257 warnings across repo (mostly tests/scripts)
- **Suite Metrics**: 310 passed in 7.15s (adversarial: 68, gaps: 18, integration: 6, unit: 218)
- **Performance**: Inspect stage alone: ~1.8 ms | Full E2E release lifecycle (18 steps): ~100 ms

### 2. Inspect Call Chain
1. `src/release_desk/app.py:211`: `create_release()` initiates release workflow.
2. `src/builder/builder.py:63`: `build_release_package()` packages files and generates manifest.
3. `src/release_desk/app.py:265`: invokes `inspect_release()`.
4. `src/inspector/inspector.py:115`: `extract_capabilities()` scans files for regex patterns.
5. `src/inspector/inspector.py:155`: `evaluate_policy()` computes deterministic findings & verdict.
6. `src/inspector/inspector.py:230`: `_run_ai_advisory()` called if `ai_enabled=True`.
7. `src/inspector/inspector.py:236`: merge logic prevents AI downgrading deterministic REJECT.
8. `src/inspector/inspector.py:268`: `create_inspect_attestation()` builds in-toto statement.
9. `src/release_desk/app.py:273`: `sign_inspect()` signs envelope with `inspector_key`.
10. `src/approver/approver.py:101`: `create_approval_payload()` hashes Inspect envelope into approval.
11. `src/ledger/ledger.py:506`: `_verify_candidate_evidence()` verifies Inspect DSSE signature & verdict.
12. `src/passport/assembler.py:21`: `build_candidate_passport()` bundles signed Inspect envelope.
13. `src/segel_core/verification/passport.py:281`: `verify_passport()` performs receiver verification.

### 3. Critical Code Excerpts (<= 25 Lines Each)

```python
# Inspect Predicate (src/segel_core/schemas/attestation.py:190-235)
class InspectPredicate(BaseModel):
    binding: BindingBlock = Field(..., description="Binding block linking evidence to release")
    policy_version: int = Field(..., ge=1, description="Inspection policy version")
    verdict: str = Field(..., pattern=r"^(PASS|WARN|REJECT)$")
    deterministic_findings: list[InspectFinding] = Field(default_factory=list)
    ai_findings: list[InspectFinding] = Field(default_factory=list)
    ai_status: str = Field(default="skipped", pattern=r"^(ok|failed|skipped)$")
    ai_model_id: str = Field(default="")
    ai_prompt_digest: str = Field(default="")
    capabilities: list[dict[str, Any]] = Field(default_factory=list)
```

```python
# Verdict & Severity Types (src/segel_core/schemas/attestation.py:173-181, 206-210)
severity: str = Field(..., pattern=r"^(pass|warn|reject)$")
source: str = Field(..., pattern=r"^(deterministic|ai)$")
verdict: str = Field(..., pattern=r"^(PASS|WARN|REJECT)$")
```

```python
# _run_ai_advisory (src/inspector/inspector.py:345-360)
def _run_ai_advisory(files: dict[str, bytes], capabilities: list[dict[str, Any]]) -> tuple[list[InspectFinding], str]:
    # MVP: AI advisory is optional and may be unavailable
    raise NotImplementedError("AI advisory requires Ollama — skipped for MVP")
```

```python
# Merge & Non-Downgrade Logic (src/inspector/inspector.py:236-247)
if verdict == "REJECT":
    for af in ai_findings:
        if af.severity != "reject": af.severity = "reject"
else:
    for af in ai_findings:
        if af.severity == "reject" and verdict != "REJECT": verdict = "REJECT"
        elif af.severity == "warn" and verdict == "PASS": verdict = "WARN"
```

```python
# Inspector Signer (src/inspector/inspector.py:324-342)
def sign_inspect(statement_dict: dict[str, Any], inspector_key: KeyPair) -> DSSEEnvelope:
    payload = canonical_json(statement_dict)
    return create_envelope(payload_type="application/vnd.segel.inspect+json", payload=payload, signers=[(inspector_key.key_id, inspector_key.private_key)])
```

```python
# Inspect / AI Error Codes (src/segel_core/errors.py:21, 39, 40)
class ErrorCode(StrEnum):
    SIG_INVALID = "SIG_INVALID"
    POLICY_DOWNGRADE = "POLICY_DOWNGRADE"
    AI_FAILED = "AI_FAILED"  # Informational, not a security block
```

### 4. S7 Coupling Table

| Component | File:Line | Strict Schema? | Breaks on Extra Fields? |
|---|---|---|---|
| Receiver Verification | `src/segel_core/verification/passport.py:281` | No (`json.loads`, `.get()`) | No |
| Transparency Ledger (FR-051) | `src/ledger/ledger.py:506` | No (`json.loads`, `.get()`) | No |
| Approver Service | `src/approver/approver.py:101` | No (Hashes envelope) | No for new releases |
| Release Desk UI | `src/release_desk/templates/release_detail.html:132` | No (Jinja context) | No |
| Test Suite Fixtures | `tests/adversarial/test_at_NNN.py` | No (Dynamic factories) | No |

### 5. S15 Assumption Table

| ID | Assumption | Status | Evidence (Relative File:Line) |
|---|---|---|---|
| A1 | Deterministic extraction runs before AI | TRUE | `src/inspector/inspector.py:220-230` |
| A2 | Separate Inspector Signer signs Inspect | PARTIAL | Distinct role, but held in same web process (`src/release_desk/app.py:273`) |
| A3 | Dedicated `ai` block in Inspect predicate | PARTIAL | Flat fields exist; dedicated sub-object does not (`src/segel_core/schemas/attestation.py:215`) |
| A4 | Stable capability IDs referenced by findings | PARTIAL | Stable names (`network_listen`), but K01..K10 format not implemented (`src/inspector/inspector.py:37`) |
| A5 | Expectation map & L1..L6 classes exist | FALSE | NOT FOUND in `src/` |
| A6 | Merge logic is raise-only and tested | TRUE | `src/inspector/inspector.py:236`, tested in `tests/adversarial/test_at_NNN.py:914` |
| A7 | AI module cannot import signing keys | FALSE | Shared process memory space (`src/release_desk/app.py:121`) |
| A8 | Ledger FR-051 tolerates extra fields | TRUE | `src/ledger/ledger.py:506-518` |
| A9 | Receiver tolerates extra fields | TRUE | `src/segel_core/verification/passport.py:295-322` |
| A10 | Purpose text sanitized & stripped | PARTIAL | Max length 300 enforced, but control chars not stripped (`src/segel_core/schemas/manifest.py:72`) |
| A11 | Desk displays advisory findings separately | FALSE | Only `deterministic_findings` displayed (`src/release_desk/templates/release_detail.html:178`) |
| A12 | Fixtures build releases via factories | TRUE | Zero static fixture files on disk (`tests/adversarial/test_at_NNN.py:75`) |
| A13 | Place for model name/digest/prompt hash | PARTIAL | `ai_model_id` and `ai_prompt_digest` exist; model weight digest missing (`src/segel_core/schemas/attestation.py:224`) |
| A14 | Tests run offline without network | TRUE | Verified in `tests/unit/test_receiver_offline_isolation.py:47` |
| A15 | Existing suite runs in < 30 seconds | TRUE | Entire suite of 310 tests runs in 7.15 seconds |

### 6. Top 10 Risks & Blockers (Ranked)
1. **Ollama Daemon Missing**: Host has no Ollama binary; tests must not require a live daemon.
2. **GPU VRAM Ceiling**: 4.0 GB VRAM limit requires small quantized models (< 2 GB weights).
3. **Key Isolation (SEC-004/013)**: Inspector key is held in web server memory; AI client must be process-isolated.
4. **Prompt Injection (AT-019)**: Manifest `purpose` and config text lack control character sanitization.
5. **Capability Taxonomy Mismatch**: Current code uses `network_listen`; PRD specifies K01..K10.
6. **Expectation Map & Purpose Classes Missing**: L1..L6 purpose classifications are not yet built.
7. **UI Advisory Display Missing**: Desk UI only renders deterministic findings.
8. **WARN Acknowledgement Gap**: `ApprovePredicate.acknowledgement_digest` is never populated or checked.
9. **Latency Impact**: E2E pipeline currently runs in ~100 ms; LLM inference could add 500-2000 ms.
10. **Schema Versioning**: Adding an `ai` nested object would require bumping predicate to `v2`.

### 7. S16 Key Architectural Decisions
1. **Execution Boundary**: Subprocess / CLI invocation with sanitized environment vs. in-process async `httpx`? *(Rec: Subprocess to strictly enforce SEC-013 key isolation)*.
2. **Taxonomy Alignment**: Retain internal string IDs with K-mapping vs. full rename? *(Rec: Internal mapping to preserve existing tests)*.
3. **Schema Evolution**: Maintain flat fields + `ai_model_digest` vs. nested `ai` block? *(Rec: Flat fields to maintain zero-breakage with passport verifiers)*.
4. **Offline Host Fallback**: Require Ollama daemon vs. graceful `ai_status="skipped"`? *(Rec: Graceful fallback per PRD §7.5 and AT-018)*.

