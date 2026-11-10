# SEGEL — Sistem Edar Gelar Elektronik Lapis-ganda

**Configuration & Release Distribution Platform with Cryptographic Evidence Chain**

*Competition prototype for Kartika Cyber Hackathon 2026, not an official product.*

---

## 1. What SEGEL Is

SEGEL (**Sistem Edar Gelar Elektronik Lapis-ganda**) is a prototype configuration release and distribution system designed for air-gapped and edge environments. It enforces that no configuration or software update is deployed to operational units without an unbroken, independently verifiable chain of cryptographic evidence spanning five sequential pipeline stamps:

```
  Origin    →    Inspect    →    Approve    →    Record    →    Test
  ┌────┐        ┌────────┐      ┌────────┐     ┌──────┐      ┌────┐
  │ 🏭 │───────▶│  🔍   │─────▶│  ✅   │────▶│  📜 │─────▶│ 🧪 │
  └────┘        └────────┘      └────────┘     └──────┘      └────┘
  Builder       Inspector       2-of-3         Merkle log    Canary
  signs         extracts        approvers      + witness     deploy
  provenance    capabilities    sign           cosign        + health
```

1. 🏭 **Origin**: Provenance attesting where the release originated and how it was packaged (Builder).
2. 🔍 **Inspect**: Capability extraction and policy rules, with optional advisory AI classification (Inspector).
3. ✅ **Approve**: Multi-party M-of-N threshold approval (default 2-of-3, author excluded) via air-gapped review, with mandatory warning acknowledgement binding (Approvers).
4. 📜 **Record**: Public tamper-evident append-only Merkle transparency log with signed checkpoints and independent witness cosignatures (Ledger + Witness).
5. 🧪 **Test**: Pre-committed canary deployment health evaluation and offline receiver verification (Canaries + Receivers).

---

## 2. 10-Minute Quickstart

### Prerequisites
- **Python Runtime**: Python 3.14.6 tested on Windows (Python 3.12 syntax compatible, but untested in this environment).
- **Git**
- **Ollama** (optional, only for live AI advisory classification): installed and running on `http://127.0.0.1:11434` with model `qwen3:4b`.

### Step 1: Clone and Set Up Virtual Environment
```powershell
git clone <repo-url> segel-cyber
cd segel-cyber

python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### Step 2: Install Dependencies
```powershell
pip install -e ".[dev]"
```

### Step 3: Run the Test Suite (Zero Network Dependencies)
All 433 unit, integration, property, and adversarial tests execute without external services or internet access (using an in-process scripted `FakeLLM`):
```powershell
pytest
```

### Step 4: Run the Automated 4-Act Demonstration
Executes all 4 demonstration acts under both deterministic-only (`SEGEL_AI_ENABLED=0`) and AI-advisory (`SEGEL_AI_ENABLED=1`) modes:
```powershell
python scripts/run_demo_scenario.py
```

### Step 5: Launch the Interactive Release Desk UI
```powershell
powershell -ExecutionPolicy Bypass -File scripts/run_demo.ps1
```
Open your browser to `http://127.0.0.1:8000`.

---

## 3. The AI Advisory Subsystem

The AI Inspector component provides natural-language purpose classification to detect discrepancies between declared release intentions and extracted configuration capabilities.

### What the Model Does
- The model (`qwen3:4b`) reads the declared manifest `purpose` string alongside extracted technical capability diffs (firewall changes, account additions, logging modifications).
- It classifies the declared purpose into one of six canonical taxonomy classes (`L1`..`L6`) and flags whether the purpose text is ambiguous.
- The expectation map (`EXPECTATION_MAP`) deterministically derives advisory findings from the predicted class.

### Key Security Properties
- **Weights Not in Repository**: Model weights are not tracked in git. Weights are managed externally via Ollama (`ollama pull qwen3:4b`).
- **Loopback Only**: All AI HTTP communications are restricted exclusively to `http://127.0.0.1:11434`. No external API calls or outbound internet connections exist.
- **Strictly Advisory (Capped at `warn`)**: AI findings are strictly capped at severity `warn`. The AI model can **never** emit a `reject` finding, can **never** reject a release, and can **never** lower or suppress a deterministic `REJECT` or `WARN` finding to `PASS`.
- **Zero Key Access**: The AI worker subprocess executes in a scrubbed environment stripped of all secret, key, token, and credential variables. The model never holds or sees private keys and never signs evidence.
- **Runtime Prompt Integrity**: The template prompt is verified against a frozen SHA-256 digest (`docs/ai_prompt_freeze.txt`) at runtime; tampering aborts inference fail-closed (`PROMPT_TAMPERED`).
- **Honest Evaluation Finding**: In pre-registered evaluation, a deterministic vague-by-default rule (B1b) detects silent purpose inconsistencies without invoking an LLM. The AI's measured empirical difference against B1b is fewer false alarms at slightly lower recall; differences of 1-2 items out of 36 are not statistically meaningful.

---

## 4. Implementation Status Table

| Feature / Subsystem | Status | Description & Test Coverage |
|---------------------|:------:|-----------------------------|
| **RFC 8032 Ed25519 Signatures** | **Implemented** | RFC 8032 test vectors passing in `tests/vectors/test_ed25519_vectors.py`. Key ID = `SHA-256(raw_pubkey)`. |
| **DSSE Envelopes & Canonical JSON** | **Implemented** | PAE encoding and canonical key ordering verified in `tests/unit/test_dsse.py` and `test_canonical.py`. |
| **in-toto Statement v1 Schemas** | **Implemented** | Origin, Inspect, Approve, Record, Test predicates validated in `tests/unit/test_schemas.py`. |
| **Deterministic Capability Extraction** | **Implemented** | Regex boundary rules and structured extractor tested in `tests/unit/test_inspector.py`. |
| **Policy Engine (PRULE-001..004)** | **Implemented** | Deterministic `REJECT` on root privilege escalation tested in `tests/adversarial/test_at004_prohibited_capabilities.py`. |
| **Air-Gapped Multi-Party Approval** | **Implemented** | 2-of-3 threshold and author self-approval exclusion tested in `tests/adversarial/test_at005_self_approval.py`. |
| **WARN Acknowledgement Binding** | **Implemented** | `acknowledgement_digest` bound in approve stamp; enforced by Ledger gate and Receiver verifier (`tests/unit/test_ai_7_ack_and_manifest.py`). |
| **RFC 6962 Transparency Ledger** | **Implemented** | Append-only Merkle log with signed checkpoints tested in `tests/unit/test_ledger.py`. |
| **Witness Cosigning & Consistency** | **Implemented** | RFC 9162 consistency proof validation tested in `tests/unit/test_witness.py`. |
| **Candidate & General Passports** | **Implemented** | Evidence bundling and verification tested in `tests/unit/test_passport.py`. |
| **Offline Receiver & Deployment Adapter** | **Implemented** | 10-step atomic deployment lifecycle, journal recovery, rollback, and read-only permissions tested in `tests/unit/test_receiver.py`. |
| **Anti-Rollback Sequence Enforcement** | **Implemented** | Monotonic sequence checks tested in `tests/adversarial/test_at002_rollback.py`. |
| **AI Advisory Subsystem** | **Implemented** | Capped at `warn`, prompt frozen, timeout fail-closed, scrubbed env tested in `tests/unit/test_ai_fake_llm.py` and `test_ai_acceptance.py`. |
| **Release Desk Web Interface** | **Implemented** | FastAPI dashboard, release detail, AI advisory panel, control char rejection, footer disclaimer. |
| **Predecessor Manifest Diffing** | **Partial** | Standalone release payload inspection implemented; historical predecessor diffing omitted (DEV-07). |
| **Trust Root Rollover Chains** | **Partial** | Monotonic `root_version` validation implemented; multi-root transition signature chains deferred (DEV-10). |
| **Dual Independent Builders** | **Not Implemented** | Single builder in MVP; bit-for-bit reproducible dual-builder verification deferred to P1 (FR-011). |
| **Fountain Code QR Streaming** | **Not Implemented** | Compact JSON/CBOR QR payloads implemented; multi-frame animated QR streaming deferred to P1 (AT-036). |
| **Emergency Revocation Push** | **Not Implemented** | Offline receivers require physical Trust Update Packages (TUP); network push deferred to P1 (AT-011). |

---

## 5. Documentation Map

- [Installation Guide](docs/install.md) — Step-by-step installation, dependencies, Ollama setup, and troubleshooting.
- [Usage Guide](docs/usage.md) — Operational workflows, CLI commands, web UI, and environment variables.
- [Architecture & Deviations](docs/architecture.md) — System architecture, component zones, data flows, and specification drift (DEV-01..DEV-10).
- [Consolidated Limitations](docs/limitations.md) — Security boundaries, operational limitations, and deferred features.
- [AI Decisions Log](docs/ai_decisions.md) — Pre-registered architectural and design decisions (D1..D22).
- [AI Evaluation Report](docs/evaluation/ai_report.md) — Empirical baseline evaluation (B0, B1, B1b, AI, B2) on the test split.
- [Notice](NOTICE) — Third-party software licenses and model attributions.
- [AI Assistance Disclosure](docs/ai_assistance_disclosure.md) — Transparency disclosure on AI-assisted coding and human oversight.

---

## 6. Disclaimer

*Competition prototype for Kartika Cyber Hackathon 2026, not an official product.*
SEGEL does not prove software or configuration is free of defect. It provides cryptographically verifiable evidence regarding origin, policy inspection, multi-party approval, ledger transparency, and canary testing. All demonstration keys are synthetic and must not be used in production environments.
