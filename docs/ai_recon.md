# SEGEL Codebase Reconnaissance for AI-Inspector Architecture

**Authority**: PRD v2.0, TAS (sections 7.4, 11), MDB, `docs/`  
**Execution Date**: 2026-11-07  
**Scope**: Read-only codebase reconnaissance for AI-Inspector integration planning.

---

## S1 Environment

### Facts
- **Python Version**: 3.14.6 (`python --version` via virtual environment)
- **Dependencies (`pyproject.toml:16-43`)**:
  - Runtime: `cryptography>=44.0.0`, `pydantic>=2.10.0`, `fastapi>=0.115.0`, `uvicorn[standard]>=0.32.0`, `jinja2>=3.1.0`, `python-multipart>=0.0.18`, `cbor2>=5.6.0`, `qrcode[pil]>=8.0`, `pillow>=11.0.0`
  - Optional dev: `pytest>=8.0.0`, `pytest-cov>=6.0.0`, `pytest-asyncio>=0.24.0`, `hypothesis>=6.100.0`, `mypy>=1.13.0`, `ruff>=0.8.0`, `bandit>=1.8.0`, `pip-audit>=2.7.0`, `httpx>=0.28.0`, `httpx2`
  - Optional ai: `httpx>=0.28.0`
- **Installed Packages Check (`pip list`)**:
  - `httpx`: Installed (`0.28.1`)
  - `requests`: Installed (`2.34.2`)
  - `pydantic`: Installed (`2.14.2`), `pydantic_core` (`2.50.2`)
  - `psutil`: **NOT INSTALLED**
  - `jsonschema`: **NOT INSTALLED**
- **Ollama Status**:
  - CLI: `ollama` is **NOT INSTALLED** or not in system PATH (`The term 'ollama' is not recognized`).
  - Daemon status: Not running.
- **GPU & Hardware Acceleration (`nvidia-smi`)**:
  - GPU: NVIDIA GeForce RTX 3050 Laptop GPU (Device 0)
  - Driver: 621.01 (WDDM), CUDA UMD: 13.5
  - VRAM: 4096 MiB (4.0 GB) total, 0 MiB allocated, 0% compute utilization
- **Linter & Static Analysis Configuration**:
  - `ruff` (`pyproject.toml:63-72`): line-length 100, target-version py312. Repo check: 257 violations across repo (mostly in `tests/` and `scripts/`).
  - `mypy` (`pyproject.toml:74-78`): strict = true, warn_return_any = true, target py312.
    - `mypy src`: **Success (0 issues across 46 source files)**.
    - `mypy src tests`: 338 issues (all in `tests/` due to untyped test functions under strict mode).
  - `bandit` (`pyproject.toml`): no dedicated tool config.
    - `bandit -r src`: **0 issues identified** across 5,973 lines of code.
    - `bandit -r . -x ./.venv -s B101`: 2 Medium (binding to `0.0.0.0` in test, `/tmp/test` in test), 1 High (`shell=True` in `scripts/mutation_runner.py:254`).
- **Containerization & Shell Scripts**:
  - Docker: `Dockerfile` exists at repo root.
  - Compose: `lab/compose.yml` exists.
  - PowerShell / Scripts: `scripts/backup_ledger.py`, `scripts/demo.py`, `scripts/init_keys.py`, `scripts/mutation_runner.py`, `scripts/reproduce_benchmarks.py`, `scripts/verify_concurrency_and_restore_drill.py`.
- **Windows Specifics**:
  - Sandbox execution requires explicit Windows binary path resolution for `.venv\Scripts`.
  - Windows file locking requires atomic patterns.

### NOT FOUND / UNKNOWN
- `psutil` package: NOT FOUND in environment.
- `jsonschema` package: NOT FOUND in environment.
- Ollama executable: NOT FOUND on host path.

### Risks for Adding AI
1. Ollama is not installed on this host; AI pipeline must default to graceful fallback (`ai_status="skipped"` / `"failed"`) and cannot require a live daemon during testing.
2. GPU VRAM is 4 GB; small quantised models (e.g., Llama-3.2-1B-Instruct or Qwen-2.5-Coder-1.5B 4-bit) fit within ~1.2-2.0 GB, but 7B/8B models will exceed 4 GB VRAM or spill to system RAM.
3. Strict mypy settings on `src/` require complete type annotations on all new AI modules.

---

## S2 Git State

### Facts
- **Branch**: `hardening/p2b-p5`
- **Remote Status**: Up to date with `origin/hardening/p2b-p5`
- **Working Tree**: Clean (`nothing to commit, working tree clean`)
- **Tags**: None (`git tag -l` returns empty)
- **Last 30 Commits**:
  - `880d7e4` FEAT(shader): match base.html background shader with anisotropic caustic rays from /zassk
  - `4793412` FIX(routing): isolate /zassk as dedicated UI/UX R&D dashboard and ensure background shaders on both environments
  - `8c5ce66` FEAT(frontend): replicate full zassk UI/UX architecture on main SEGEL dashboard route
  - `7ab88b9` FEAT(frontend): complete design system audit and migrate SEGEL frontend to unified glassmorphic shell
  - `9045c4a` FEAT(hero): condense lines 2 and 3 and eliminate all punctuation symbols
  - `b8a1579` FEAT(favicons): implement comprehensive multi-platform favicon suite and endpoints
  - `66f9a06` FEAT(hero): align copywriting with PRD v2.0 vision and 5-stamp passport model
  - `ec7f0c9` FEAT(hero): compress copywriting and refine 3D cube inline-flex geometry
  - `66082d2` FEAT(hero): update Indonesian military copywriting and refine single-line 3D cube layout
  - `2fd9123` FEAT(hero): integrate PUSSIBERAD sovereign command copywriting and 3D cube roll animation
  - `f8cefd3` FEAT(navbar): align floating dock navigation with official SEGEL platform routes
  - `7d0e303` UI-DESIGN-SYSTEM: Comprehensive triadic color system transformation (60-30-10 TNI AD palette)
  - `0efa13e` REFACTOR: Comprehensive codebase-wide terminology migration ZASSK to SEGEL
  - `74ee635` UI-BRANDING: Remove Zassk badge from PUSSIBERAD logo block
  - `0d94872` Revert "UI-TOP-METRICS-ROW: Replace top metrics row with verified 256px unified geometry and exact baselines"
  - `87fe8a0` UI-TOP-METRICS-ROW: Replace top metrics row with verified 256px unified geometry and exact baselines
  - `dab3525` UI-SHADER-SPEED: Increase shader motion speed with organic subtle fluid caustics
  - `9130dbc` UI-LIGHTMODE-SHADERS: Light-mode TypeGPU background, crisp slate typography, and full alignment with reference top metrics row
  - `18e957e` UI-WEBGPU-SHADER: Implement WebGPU anisotropic lit rays shader background with TypeGPU and TNI AD triadic palette
  - `8606863` UI-TOP-ROW: Pixel-perfect interlocking card geometry, smooth organic folder tab, and symmetric step silhouettes
  - `4a0da45` UI-HEADER-INSIGNIA: Replace Search and Profile buttons with static TNI and TNI AD logos
  - `a691832` UI-ZASSK-TOP-ROW: Fix arc colors left-to-right, fuse Profit/Users into interlocking card, and restore Ended Task
  - `558a15f` UI-ZASSK-SECURITY-HEALTH: Re-engineer Security Health card with Zassk reference dot-matrix layout and optimal spacing
  - `633a72c` UI-ZASSK-SECURITY-HEALTH: Replace redundant col 4 trend with security health telemetry card
  - `2da7786` UI-PERFORMANCE-TREND: Add AlignUI performance trend card at bottom of dashboard
  - `eb60634` UI-BRANDING: Adopt PUSSIBERAD logo and typography across release desk and dashboard
  - `545bee5` UI-ZASSK-SPLIT-TREND: Split profit/users cards, align responses gauge, integrate AlignUI performance trend, and remove bezel frame
  - `b2ffe57` UI-ZASSK-REVERSE-ENGINEER: Reconstruct tablet bezel, SVG folder-tab contours, spectral waterfall lines, and multi-layered progress tracks
  - `11d0c76` UI-ZASSK-PIXEL-EXACT: Align file-folder notches, interlocking widgets, needle waterfall chart, and navigation dock
  - `e98dcdc` UI-ZASSK-GEOMETRY: Refine asymmetric card geometry, interlocking profit-user widgets, notched tabs, and needle curtain waveform

### NOT FOUND / UNKNOWN
- Release tags: NOT FOUND.

### Risks for Adding AI
- Work is directly on `hardening/p2b-p5`. Any structural branch divergence or unmerged work must be committed cleanly.

---

## S3 Repo Map

### Architecture Map (Depth <= 3)
- `src/`
  - `approver/`: Multi-party authorization gate (DSSE threshold sign, QR exchange, approval payload)
  - `builder/`: Release packager and origin provenance generator (in-toto v1 statement, deterministic tar.gz)
  - `components/`: UI components (charts, trends, widgets)
  - `demo_infra/`: Synthetic demo key generator and memory bundle
  - `frontend/`: UI design assets, CSS design tokens, prototype layouts
  - `inspector/`: Capability extraction and policy evaluation engine
    - `ai/`: Intended sub-package for AI advisory client (currently empty)
    - `policy/`: Intended sub-package for policy rules (currently empty)
  - `ledger/`: Append-only transparency ledger (Merkle tree, SQLite store, inclusion proofs)
  - `lib/`: Shared utility helpers
  - `passport/`: Release passport assembler (candidate and general passports)
  - `promotion/`: Canary receipt aggregator and promotion criteria evaluator
  - `receiver/`: Air-gapped unit verifier and deployment executor
    - `adapter/`: Baseline configuration deployment adapter with journal recovery
  - `release_desk/`: Untrusted FastAPI web portal (dashboard, telemetry, release creation, QR generation)
    - `static/`: Static CSS, favicons, logos, client scripts
    - `templates/`: Jinja2 templates (dashboard, release detail, ledger, trust)
  - `segel_core/`: Core cryptographic primitives, schemas, verification pipeline, error codes
    - `crypto/`: Ed25519 signatures, DSSE envelopes, SHA-256 Merkle tree hashing
    - `schemas/`: Pydantic models for manifest, attestation, binding, passport, trust, receipt
    - `verification/`: Passport verifier, trust context, epoch/sequence checkers
  - `trust/`: Trust root, verification policy, and snapshot helpers
  - `witness/`: Transparency ledger checkpoint cosigner and fork detector
- `scripts/`: Operational tools (`demo.py`, `backup_ledger.py`, `mutation_runner.py`, `verify_concurrency_and_restore_drill.py`)
- `tests/`: Test suite
  - `adversarial/`: AT-001 through AT-045 security attack tests
  - `gaps/`: Phase C red tests covering gap requirements (FR-051, FR-066, SEC-004, SEC-017, AT-030)
  - `integration/`: End-to-end full lifecycle integration tests
  - `unit/`: Component-level unit tests for crypto, core, ledger, receiver, approver, builder, inspector
- `docs/`: Technical specifications, architectural decisions, security reviews, audit logs
- `lab/`: Demonstration persistence, compose configurations, and key storage

### Entry Points and CLIs
- `segel-receiver`: `receiver.cli:main` (`pyproject.toml:46`)
- `segel-approver`: `approver.cli:main` (`pyproject.toml:47`)
- `segel-witness`: `witness.cli:main` (`pyproject.toml:48`)
- Web Portal: `uvicorn release_desk.app:app`

### Execution Commands
- **Interactive Demo**: `python scripts/demo.py` (executes full 18-step lifecycle, canary deployment, and rejection scenarios).
- **Web Interface**: `python -m uvicorn release_desk.app:app --host 127.0.0.1 --port 8000` (serves `http://127.0.0.1:8000/`).
- **Test Suite**: `pytest -q`

### Test Suite Metrics
- **Total Test Count**: 310 tests
- **Count by Directory**:
  - `tests/adversarial`: 68 tests
  - `tests/gaps`: 18 tests
  - `tests/integration`: 6 tests
  - `tests/unit`: 218 tests
- **Total Runtime**: 7.15 seconds (`pytest -q` on Windows)
- **Slowest 10 Tests**:
  1. `1.02s` `tests/unit/test_properties.py::TestCanonicalJsonProperties::test_deterministic`
  2. `0.48s` `tests/gaps/test_c5_at030_crash.py::test_c5_at030_red_crash_during_apply_recovery`
  3. `0.44s` `tests/unit/test_properties.py::TestCanonicalJsonProperties::test_parseable`
  4. `0.43s` `tests/unit/test_properties.py::TestCanonicalJsonProperties::test_utf8_encoded`
  5. `0.40s` `tests/gaps/test_c5_at030_crash.py::test_c5_at030_red_crash_during_staging_recovery`
  6. `0.32s` `tests/unit/test_properties.py::TestCanonicalJsonProperties::test_sorted_keys`
  7. `0.15s` `tests/adversarial/test_at_NNN.py::test_at_028_decompression_bomb`
  8. `0.12s` `tests/unit/test_release_desk.py::test_full_web_lifecycle_canary_and_promote`
  9. `0.12s` `tests/unit/test_release_desk.py::test_segel_endpoint`
  10. `0.08s` `tests/unit/test_release_desk.py::test_index_page`

---

## S4 Inspect Pipeline, End to End

### Call Chain
1. **Release Creation Trigger**: `release_desk/app.py:211` (`create_release`) receives form submission and payload files.
2. **Package Construction & Origin**: `builder/builder.py:63` (`build_release_package`) generates manifest and in-toto v1 Statement (`ORIGIN_PREDICATE_TYPE`).
3. **Inspection Trigger**: `release_desk/app.py:265` invokes `inspector/inspector.py:198` (`inspect_release`).
4. **Deterministic Capability Extraction**: `inspector/inspector.py:115` (`extract_capabilities`).
5. **Deterministic Policy Evaluation**: `inspector/inspector.py:155` (`evaluate_policy`).
6. **AI Advisory Execution**: `inspector/inspector.py:230` calls `inspector/inspector.py:345` (`_run_ai_advisory`).
7. **Merge & Escalation Logic**: `inspector/inspector.py:236-247` merges deterministic and AI findings (escalate only, no downgrade).
8. **Inspect Statement Construction**: `inspector/inspector.py:268` (`create_inspect_attestation`) builds in-toto v1 Statement with `InspectPredicate`.
9. **Inspector Signing**: `release_desk/app.py:273` calls `inspector/inspector.py:324` (`sign_inspect`) using `inspector_key` (`role="inspector_signer"`).
10. **Approval Binding**: `approver/approver.py:70` (`create_approval_payload`) computes `inspect_digest = sha256_hex(canonical_json(inspect_envelope.to_dict()))` and binds it into `ApprovePredicate.inspect_evidence_digest`.
11. **Ledger Append Verification (FR-051)**: `ledger/ledger.py:217` (`append_entry`) calls `ledger/ledger.py:452` (`_verify_candidate_evidence`), checking `inspect_envelope` signature and non-REJECT verdict.
12. **Candidate Passport Assembly**: `passport/assembler.py:21` (`build_candidate_passport`) packages `inspect_envelope` into `ReleasePassport.inspect_envelope`.
13. **Receiver Offline Verification**: `receiver/receiver.py:155` (`verify_and_deploy`) calls `segel_core/verification/passport.py:200` (`verify_passport`), verifying DSSE signature, binding block, verdict, and minimum policy floor (`passport.py:281-326`).

### Code Excerpts

#### Capability Extraction Signature (`src/inspector/inspector.py:115-117`)
```python
def extract_capabilities(
    files: dict[str, bytes],
) -> list[dict[str, Any]]:
```

#### Policy Evaluation Signature (`src/inspector/inspector.py:155-158`)
```python
def evaluate_policy(
    capabilities: list[dict[str, Any]],
    policy_version: int = 1,
) -> tuple[str, list[InspectFinding]]:
```

#### Verdict and Severity Enums (`src/segel_core/schemas/attestation.py:173-181`, `206-210`)
```python
# Finding severity
severity: str = Field(
    ...,
    pattern=r"^(pass|warn|reject)$",
    description="Finding severity: pass, warn, or reject",
)
source: str = Field(
    ...,
    pattern=r"^(deterministic|ai)$",
    description="Whether the finding is deterministic or AI-generated",
)

# Predicate verdict
verdict: str = Field(
    ...,
    pattern=r"^(PASS|WARN|REJECT)$",
    description="Aggregate verdict: PASS, WARN, or REJECT",
)
```

#### Current `_run_ai_advisory` Body (`src/inspector/inspector.py:345-360`)
```python
def _run_ai_advisory(
    files: dict[str, bytes],
    capabilities: list[dict[str, Any]],
) -> tuple[list[InspectFinding], str]:
    """Run AI advisory analysis (Ollama).

    This is an optional, isolated analysis. The AI has no signing keys
    and cannot modify verdicts — it can only ADD findings.

    Returns:
        Tuple of (findings, model_id).
    """
    # MVP: AI advisory is optional and may be unavailable
    # When Ollama is available, this sends the capability summary
    # for additional analysis. For now, return empty.
    raise NotImplementedError("AI advisory requires Ollama — skipped for MVP")
```

#### Merge & Escalation Logic (`src/inspector/inspector.py:236-247`)
```python
            # SEC-013: AI MUST NOT downgrade a deterministic REJECT
            if verdict == "REJECT":
                # Filter out any AI findings that would lower severity
                for af in ai_findings:
                    if af.severity != "reject":
                        af.severity = "reject"  # Force to match deterministic
            else:
                # AI can escalate (warn→reject) but not downgrade
                for af in ai_findings:
                    if af.severity == "reject" and verdict != "REJECT":
                        verdict = "REJECT"
                    elif af.severity == "warn" and verdict == "PASS":
                        verdict = "WARN"
```

#### Inspector Signer (`src/inspector/inspector.py:324-342`)
```python
def sign_inspect(
    statement_dict: dict[str, Any],
    inspector_key: KeyPair,
) -> DSSEEnvelope:
    """Sign the Inspect attestation with the Inspector Signer's key."""
    payload = canonical_json(statement_dict)
    return create_envelope(
        payload_type="application/vnd.segel.inspect+json",
        payload=payload,
        signers=[(inspector_key.key_id, inspector_key.private_key)],
    )
```

#### Inspect Predicate Schema (`src/segel_core/schemas/attestation.py:190-235`)
```python
class InspectPredicate(BaseModel):
    """Inspection result with deterministic and AI findings."""

    binding: BindingBlock = Field(
        ...,
        description="Binding block linking this evidence to a release",
    )
    policy_version: int = Field(
        ...,
        ge=1,
        description="Inspection policy version used for this analysis",
    )
    verdict: str = Field(
        ...,
        pattern=r"^(PASS|WARN|REJECT)$",
        description="Aggregate verdict: PASS, WARN, or REJECT",
    )
    deterministic_findings: list[InspectFinding] = Field(
        default_factory=list,
        description="Findings from deterministic rule checks",
    )
    ai_findings: list[InspectFinding] = Field(
        default_factory=list,
        description="Findings from AI-based analysis",
    )
    ai_status: str = Field(
        default="skipped",
        pattern=r"^(ok|failed|skipped)$",
        description="Status of AI analysis: ok, failed, or skipped",
    )
    ai_model_id: str = Field(
        default="",
        description="Identifier of the AI model used, if any",
    )
    ai_prompt_digest: str = Field(
        default="",
        description="SHA-256 digest of the AI prompt template used",
    )
    capabilities: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Capabilities detected in the release payload",
    )
```

- **Predicate Type URN**: `https://segel.dev/attestation/inspect/v1` (`src/segel_core/schemas/attestation.py:90`)
- **DSSE Payload Type**: `application/vnd.segel.inspect+json` (`src/inspector/inspector.py:339`)
- **Extra Fields Behaviour**: Pydantic v2 default (`extra="ignore"`). `extra="forbid"` is NOT configured.
- **Current `ai_status` Representation**: Field on `InspectPredicate` restricted by pattern `r"^(ok|failed|skipped)$"` with default `"skipped"`.

---

## S5 Baseline v1 and Capabilities

### Facts
- **Payload Type**: `"baseline/v1"` (`src/segel_core/schemas/manifest.py:69`).
- **Capability Rules & IDs (`src/inspector/inspector.py:37-80`)**:
  - `network_listen`: Patterns matching `listen`, `bind_address`, `port`, `server`.
  - `file_write`: Patterns matching `log_file`, `output_path`, `write_dir`, `data_dir`.
  - `external_connect`: Patterns matching `upstream`, `remote_host`, `proxy`, `api_url`.
  - `credential_reference`: Patterns matching `password`, `secret`, `token`, `api_key`, `auth`.
  - `privilege_escalation`: Patterns matching `run_as_root`, `privileged`, `sudo`.
- **Policy Rules (`src/inspector/inspector.py:84-100`)**:
  - `PRULE-001`: `privilege_escalation` -> `reject`
  - `PRULE-002`: `credential_reference` -> `warn`
  - `PRULE-003`: `external_connect` -> `warn`
- **Manifest Purpose Sanitization (`src/segel_core/schemas/manifest.py:72-76`)**:
  - `purpose: str = Field(..., max_length=300)`.
  - Enforces length <= 300.
  - **No control character stripping or ASCII sanitization exists**.
- **Predecessor / Sequence 1 Diff Logic**:
  - Diffing against predecessor is **not implemented** (`docs/audit.md:21`). Sequence 1 and all higher sequences evaluate files independently without comparing prior manifests.

### NOT FOUND / UNKNOWN
- Capability ID taxonomy `K01..K10` or instance IDs (e.g., `K01#3`): NOT FOUND in code.
- Expectation map and purpose classes (`L1..L6`): NOT FOUND in code.
- Baseline configuration file schema / validator (e.g. JSON schema for YAML files): NOT FOUND.

### Risks for Adding AI
1. AI prompted with arbitrary `purpose` strings can suffer prompt injection attacks because `purpose` is not sanitized for control characters or delimiter escapes.
2. If the AI model expects `K01..K10` format, but deterministic extraction outputs `network_listen`, a mapping layer is required.

---

## S6 Policy and Trust

### Facts
- **Verification Policy Schema (`src/segel_core/schemas/trust.py:171-225`)**:
  - `min_inspect_policy_version: int = Field(default=1, ge=1)`: Enforced in `src/segel_core/verification/passport.py:311-317`. If `inspect_policy_ver < min_policy`, raises `PolicyDowngradeError(POLICY_DOWNGRADE)`.
  - `required_stamps`: Defaults to `["origin", "inspect", "approve", "record", "test"]`.
  - `approval_threshold`: Minimum distinct approver signatures (default 2).
  - `approval_groups`: Per-group quotas.
- **WARN Acknowledgement Representation**:
  - `src/segel_core/schemas/attestation.py:292-295`: `ApprovePredicate` defines `acknowledgement_digest: str = Field(default="", description="Digest of acknowledged WARN findings (empty if none)")`.
  - Currently, `create_approval_payload()` (`src/approver/approver.py:118`) does not populate this field, leaving it default empty string `""`.

### NOT FOUND / UNKNOWN
- `ai_required` policy flag: NOT FOUND in `VerificationPolicy`.
- Dedicated `acknowledge_warn` boolean/object: NOT FOUND.

### Risks for Adding AI
- If AI findings introduce WARN severities, there is no UI workflow or policy check requiring approvers to acknowledge them via `acknowledgement_digest`.

---

## S7 Verification Coupling (Critical)

| Component | File & Line | Parses Inspect? | Verifies DSSE Signature? | Strict on Extra Predicate Fields? | Would New AI Fields Break It? |
|---|---|---|---|---|---|
| **Receiver Verifier** | `src/segel_core/verification/passport.py:281-326` | Yes (`json.loads`) | Yes (`verify_envelope`) | No (`extra="ignore"`, accesses fields via `.get()`) | **No**. Tolerates extra fields without schema errors. |
| **Ledger FR-051 Gate** | `src/ledger/ledger.py:496-518` | Yes (`json.loads`) | Yes (`verify_envelope`) | No (Checks only binding stamp, subject, and non-REJECT verdict) | **No**. Extra fields are ignored. |
| **Approver Service** | `src/approver/approver.py:101` | No | No (Hashes raw envelope) | N/A (Computes SHA-256 of canonical envelope JSON) | **No** for new releases; **Yes** if modifying existing pre-signed test envelopes. |
| **Release Desk UI** | `src/release_desk/templates/release_detail.html:132-220` | Yes (Jinja context) | No | No (Reads `release.verdict`, `release.inspection.*`) | **No**. Renders existing fields safely. |
| **Inspect Unit Tests** | `tests/unit/test_inspector.py:176-189` | Yes | Yes | No (Asserts key presence `in pred`, not exact key set) | **No**. |
| **Adversarial AT-016..018** | `tests/adversarial/test_at_NNN.py:896-950` | Yes | No | No (Inspects `ai_status`, `verdict`) | **No**, provided `ai_status` remains `ok`/`failed`/`skipped`. |

### Critical Finding
Adding new fields (or an `ai` block) to `InspectPredicate` **WILL NOT BREAK** Receiver verification, Ledger verification, or existing unit tests because:
1. Pydantic models in `src/segel_core/schemas/attestation.py` do not specify `extra="forbid"`.
2. Verification logic in `passport.py` and `ledger.py` accesses fields via `.get()` rather than strict schema reconstruction.
3. No hardcoded SHA-256 digests of Inspect envelopes exist in test fixtures.

---

## S8 Error Codes

### Facts
- Defined in `src/segel_core/errors.py:15-41` as `ErrorCode(StrEnum)`:
  - `SIG_INVALID`
  - `DIGEST_MISMATCH`
  - `STAMP_MISSING`
  - `THRESHOLD_NOT_MET`
  - `KEY_NOT_AUTHORISED`
  - `SUBJECT_MISMATCH`
  - `SEQUENCE_REPLAY`
  - `EPOCH_STALE`
  - `KEY_REVOKED`
  - `STATE_CORRUPT`
  - `CHECKPOINT_FORK`
  - `PROOF_INVALID`
  - `SCOPE_MISMATCH`
  - `ADAPTER_NOT_ALLOWED`
  - `SCHEMA_UNKNOWN`
  - `PACKAGE_MALFORMED`
  - `RESOURCE_LIMIT`
  - `HELD`
  - `POLICY_DOWNGRADE`
  - `AI_FAILED` (Informational, does not block pipeline)
- **Inspect / AI-Related Codes**:
  - `AI_FAILED`: Raised/recorded when AI analysis fails or times out.
  - `POLICY_DOWNGRADE`: Used when inspect policy version is below `min_inspect_policy_version` (`passport.py:314`).
  - `SIG_INVALID`: Used when inspect signature is invalid or verdict is REJECT (`passport.py:306`).

### NOT FOUND / UNKNOWN
- `CAPABILITY_FORBIDDEN`: NOT FOUND in `ErrorCode` (forbidden capabilities trigger `verdict = "REJECT"`, which raises `SIG_INVALID` or `POLICY_DOWNGRADE`).

---

## S9 Signing and Key Handling

### Facts
- **Inspector Signer Implementation**: `src/inspector/inspector.py:324-342` (`sign_inspect`).
- **Key Location in Demo**: Stored in `DemoState._demo_keys.inspector_key` (`src/demo_infra/keys.py:16`, `src/release_desk/app.py:273`).
- **Process Isolation**: The Inspect stage runs in the **same process** as the Release Desk FastAPI web application.
- **Decision D1 State**:
  - Approver keys were successfully separated into `StandaloneApproverSigner` (`src/approver/service.py`).
  - However, `author_key`, `builder_key`, `inspector_key`, `ledger_key`, and `witness_key` remain in `DemoKeyBundle` held in web server heap memory (`src/release_desk/app.py:121-185`).
- **Requirements to Guarantee AI Cannot Access Signing Keys**:
  - AI advisory execution must run in an isolated boundary (out-of-process subprocess or isolated HTTP container) with zero key parameters.
  - The AI function signature must accept only sanitized configuration text and return structured JSON findings.
  - `sign_inspect` must only be called after AI output has been schema-validated and merged.

---

## S10 UI Surfaces

### Facts
- **Framework**: FastAPI + Jinja2 server-side rendering + vanilla CSS + Lucide icons.
- **Receiver UI**: **CLI only** (`src/receiver/cli.py`). No Receiver web interface exists.
- **Desk Pages**:
  - Dashboard: `src/release_desk/templates/index.html` (renders pipeline metrics, 5-stamp status, release list).
  - Release Creation: `src/release_desk/templates/new_release.html`.
  - Release Detail / Review: `src/release_desk/templates/release_detail.html`:
    - Lines 52-57: 5-stamp progress bar showing Inspect verdict badge.
    - Lines 132-220: Inspection Results card (verdict, capabilities detected, deterministic findings, AI status).
    - Lines 285-350: Evidence Explorer showing raw DSSE JSON for all 5 stamps.
- **AI UI Integration Point**:
  - Dedicated AI Advisory Findings section in `src/release_desk/templates/release_detail.html` right after deterministic findings (line 204).
  - AI Health telemetry card on the main dashboard (`src/release_desk/templates/index.html`).

---

## S11 Tests

### Facts
- **Fixtures & Construction**:
  - Tests do not load static files from disk. They construct releases dynamically via helper `build_release_package(files=..., release_id=..., sequence=..., purpose=...)`.
  - `SyntheticLab` in `tests/adversarial/test_at_NNN.py:75` provides synthetic keys and environment state.
- **Current AT-016..018 Content**:
  - `test_at_016_ai_cites_nonexistent_capability_id` (`test_at_NNN.py:896`): In-line test verifying hallucinated capability IDs are discarded.
  - `test_at_017_ai_says_safe_while_deterministic_verdict_is_reject` (`test_at_NNN.py:914`): Verifies AI cannot lower `REJECT` verdict.
  - `test_at_018_ai_timeout_or_malformed_output` (`test_at_NNN.py:938`): Calls `inspect_release(..., ai_enabled=True)` and verifies `ai_status == "failed"`, `verdict == "PASS"`.
  - `test_at_019_injection_in_purpose_text_and_configuration_values` (`test_at_NNN.py:953`): Tests 20 prompt injection strings through `build_release_package()` and `inspect_release()`, verifying verdicts remain deterministic.

---

## S12 Docs State

### File Inventory
- `docs/ARCHITECTURE.md`: High-level zone model (Z1..Z5), stamps, and trust hierarchy.
- `docs/audit.md`: Formal audit mapping PRD v2.0 FR/SEC/AT requirements to implementation.
- `docs/DECISIONS.md`: Architectural decisions D1 (signer separation), D2 (deterministic AI), D3 (journal recovery).
- `docs/DEMO_GUIDE.md`: Step-by-step walkthrough of the 18-step interactive demo.
- `docs/DESIGN_SYSTEM.md`: UI tokens, color palette (60-30-10 TNI AD), and component geometry.
- `docs/hardening_state.md`: Progress checklist for hardening pass.
- `docs/id_reconciliation.md`: Reconciliation of test function names to genuine PRD requirement IDs.
- `docs/IMPLEMENTATION_PLAN.md`: Historical roadmap and task breakdown.
- `docs/KNOWN_LIMITATIONS.md`: Deferred requirements and MVP scope boundaries.
- `docs/limitations.md`: Codified limitations under Decisions D1, D2, and D3.
- `docs/PROGRESS.md`: Module implementation status and test metrics.
- `docs/SECURITY_MODEL.md`: Threat model, zone isolation, and cryptographic assumptions.
- `docs/security_review.md`: Code security audit findings (SEC-FINDING-01..05).
- `docs/TEST_REPORT.md`: Baseline test run logs and coverage stats.
- `docs/test_validity.md`: Analysis of adversarial test validity and sound vs vacuous classifications.
- `docs/TRACEABILITY.md`: Traceability matrix from PRD requirements to code and tests.

### Absolute Claims Wording Found
- `docs/limitations.md:37`: `Guarantee: Abrupt power loss or process kill mid-deployment leaves backups intact and enables zero-state-corruption recovery.`
- `docs/PROGRESS.md:93`: `None. All 138 tests passing with 100% test integrity.`
- `docs/SECURITY_MODEL.md:17`: `Storage is untrusted; all integrity guarantees stem from signed data.`
- `docs/audit.md:209`: `Documented 100% compliant in PRD Appendix E`

### Absolute Local Paths Present in Existing Docs
Absolute local workspace paths containing URI file schemes and OS directory roots are present in:
- `docs/audit.md` (lines 15, 16, 17, 18, 19, 20, 21, 23, 24, 25, 46, 60, 63, 75, 76, 77, 80, 81, 82)
- `docs/id_reconciliation.md` (lines 11, 41, 42, 45, 49, 54, 59)
- `docs/security_review.md` (lines 32, 148)

---

## S13 Data and Lab

### Facts
- `lab/backups/`: Contains sample SQLite backup `ledger_backup.db`.
- `lab/data/`: Contains SQLite live database `ledger.db`.
- `lab/keys/`: Contains pre-generated demo keypairs (11 pairs for author, builder, inspector, approvers, ledger, witness, receivers).
- `lab/trust/`: Contains `policy.json` and `trust_root.json`.
- `lab/corpus/`, `lab/units/`, `lab/deploy/`: Empty directories.
- **Baseline Fixtures**: **0 static files**. All test configurations are generated dynamically in memory.

---

## S14 Performance Baseline

- **Inspect Stage Alone**: **1.5 - 2.0 ms** (regex extraction + policy evaluation).
- **Full E2E Release Lifecycle (Author -> Receiver Deployment)**: **~100 ms** (`tests/integration/test_lifecycle.py::TestEndToEndLifecycle::test_full_lifecycle` takes 0.10s across all 18 cryptographic and ledger steps).

---

## S15 Assumption Check

| Assumption | Status | Relative File:Line Evidence |
|---|---|---|
| **A1** Inspect runs deterministic extraction + policy before AI | **TRUE** | `src/inspector/inspector.py:220-230` (`capabilities = extract_capabilities()`, `verdict = evaluate_policy()`, then `if ai_enabled:`) |
| **A2** Separate Inspector Signer composes and signs Inspect | **PARTIAL** | Separate function (`src/inspector/inspector.py:324`) and role (`"inspector_signer"`), but held in same web process in demo (`src/release_desk/app.py:273`) |
| **A3** Inspect predicate has fields for an `ai` block | **PARTIAL** | Flat fields exist (`ai_findings`, `ai_status`, `ai_model_id`, `ai_prompt_digest` in `src/segel_core/schemas/attestation.py:215-231`), but no nested `ai` block |
| **A4** Capability IDs have stable format and referenced by findings | **PARTIAL** | Stable string names (`network_listen`, `file_write`), but not K01..K10 format (`src/inspector/inspector.py:37-80`) |
| **A5** Expectation map and purpose classes L1..L6 exist | **FALSE** | NOT FOUND in `src/` |
| **A6** Merge logic is raise-only and tested | **TRUE** | `src/inspector/inspector.py:236-247`, tested in `tests/adversarial/test_at_NNN.py:914-935` (`test_at_017`) |
| **A7** AI module cannot import signing keys today | **FALSE** | Single-process architecture (`src/release_desk/app.py`); keys are accessible in Python memory |
| **A8** Ledger FR-051 verification tolerates extra predicate fields | **TRUE** | `src/ledger/ledger.py:506-518` parses via `json.loads()` and checks only binding, subject, and verdict |
| **A9** Receiver verification tolerates extra predicate fields | **TRUE** | `src/segel_core/verification/passport.py:295-322` uses `.get()` and Pydantic models default to `extra="ignore"` |
| **A10** Purpose text is length-limited and control-char stripped | **PARTIAL** | Length-limited to 300 (`src/segel_core/schemas/manifest.py:74`), but control characters are NOT stripped |
| **A11** Desk displays advisory findings separately | **FALSE** | `src/release_desk/templates/release_detail.html:178` iterates only `deterministic_findings` |
| **A12** Fixtures build releases through factories | **TRUE** | `tests/adversarial/test_at_NNN.py` uses `build_release_package()` and `SyntheticLab()`; 0 static fixture files |
| **A13** Place for model name/digest/prompt hash in evidence | **PARTIAL** | `ai_model_id` and `ai_prompt_digest` exist; model weights digest is missing (`src/segel_core/schemas/attestation.py:224-231`) |
| **A14** Tests run offline with network disabled | **TRUE** | Verified in `tests/unit/test_receiver_offline_isolation.py:47-129`; 310 tests pass with zero network sockets |
| **A15** Existing suite runs in under 30 seconds | **TRUE** | Full test suite runs in **7.15 seconds** (310 passed) |

---

## S16 Questions for Decision

1. **AI Execution Architecture (In-Process vs Isolated Subprocess)**:
   - *Option A*: Async in-process HTTP client (`httpx`) calling local Ollama (`http://127.0.0.1:11434`).
   - *Option B*: Subprocess / CLI wrapper executing in an isolated process with scrubbed environment variables.
   - *Recommendation*: **Option B (Subprocess)** or isolated HTTP adapter with explicit memory boundary to satisfy PRD SEC-004 & SEC-013.

2. **Capability Taxonomy Alignment**:
   - *Option A*: Retain existing IDs (`network_listen`, `credential_reference`, etc.) and add an internal mapping to PRD K01..K10.
   - *Option B*: Break existing IDs and rename them directly to K01..K10 across `inspector.py` and all tests.
   - *Recommendation*: **Option A**. Keeps all 310 tests green while exposing K01..K10 in AI prompts and findings.

3. **Schema Field Structure for AI Advisory**:
   - *Option A*: Maintain existing flat fields on `InspectPredicate` (`ai_findings`, `ai_status`, `ai_model_id`, `ai_prompt_digest`) and add `ai_model_digest: str = ""`.
   - *Option B*: Replace flat fields with a nested `ai: AIAdvisoryBlock` object (requires schema version bump to `inspect/v2`).
   - *Recommendation*: **Option A**. Preserves 100% backward compatibility with `inspect/v1` and avoids breaking existing passport verifiers.

4. **Handling Host Environments Without Ollama**:
   - *Option A*: Fail hard if Ollama is missing when `ai_enabled=True`.
   - *Option B*: Gracefully record `ai_status="failed"` (or `"skipped"`), cite `AI_FAILED`, keep deterministic verdict, and never block release creation or testing.
   - *Recommendation*: **Option B**. Mandated by PRD §7.5 and AT-018; essential for CI/CD and air-gapped environments.
