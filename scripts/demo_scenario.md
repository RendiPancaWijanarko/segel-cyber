# SEGEL MVP 6-Minute Demonstration Scenario (MDB §9)

This document specifies the authoritative 6-minute live demonstration script for the **Sistem Edar Gelar Elektronik Lapis-ganda (SEGEL)** platform per MVP Development Blueprint (MDB) Section 9.

---

## 1. Demonstration Overview & Timing

| Act | Title | Focus & Core Mechanism | Duration | Real Artifacts Used |
| :--- | :--- | :--- | :---: | :--- |
| **Preflight** | Preflight Readiness | Ollama daemon connectivity, model `qwen3:4b`, warm-up latency | 30 s | `scripts/demo_ai_preflight.ps1` |
| **Act 1** | The Golden Path | 5-Stamp release attestation, ledger recording, canary test, promotion, and air-gapped deployment | 2 min | Clean configuration release (`BASELINE-UNIT-42`) |
| **Act 2** | Policy Rejection | Deterministic privilege escalation detection (`privilege: root` -> `PRULE-004`), fail-closed ledger gate | 1 min | Root privilege release candidate |
| **Act 3** | Ambiguous Intent & AI Advisory | Silent mismatch detection on `DEV-14`, B1 abstention vs. AI `L6` warning, vague-by-default comparison | 1.5 min | `lab/ai_corpus/DEV-14.json` |
| **Act 4** | Cryptographic Defense | Merkle tree consistency proof, Ed25519 DSSE signature verification, replay attack prevention | 1 min | Mutated envelope payload & replayed sequence |

> [!NOTE]
> **Corpus Partition Rule**: In strict compliance with repository security rules, all demo scenarios use synthetic demonstration releases or development split items (`DEV-14`). **Never use a `TEST-*` item.**

---

## 2. Preflight Check (30 Seconds)

Before initiating the demonstration, run the preflight verification script to ensure the local Ollama inference service and `qwen3:4b` weights are loaded in memory:

```powershell
powershell -File scripts/demo_ai_preflight.ps1
```

**Expected Console Output**:
```
============================================================
  SEGEL AI Inspector Preflight Check                        
============================================================
Target Endpoint : http://127.0.0.1:11434
Target Model    : qwen3:4b

[1/4] Checking Ollama loopback connectivity... [OK]
[2/4] Verifying presence of model 'qwen3:4b'... [OK]
      Model Digest: 359d7dd4bcdab3d86b87d73ac27966f4dbb9f5efdfcc75d34a8764a09474fae7
[3/4] Sending warm-up request (keep_alive 30m)... [OK]
      Warm-up Latency: < 2000 ms
[4/4] Querying 'ollama ps' status...
      qwen3:4b    359d7dd4bcda    3.5 GB    34%/66% CPU/GPU    4096       llamacpp    29 minutes from now

Preflight check completed successfully: AI Inspector is ready.
```

---

## 3. Act 1: The Golden Path (Clean Configuration Release)

### Narrative
An authorized configuration engineer updates network parameters for Unit 42. The release traverses the complete 5-stamp security chain, canary execution, and offline receiver deployment.

### Steps & Real Artifacts
1. **Author Signing**:
   - Files: `config/app.yaml` (`port: 8080`, `host: 0.0.0.0`), `config/logging.yaml` (`log_level: info`).
   - Manifest created (`release_id="BASELINE-UNIT-42"`, `sequence=1`).
   - Manifest signed by author key (`application/vnd.segel.manifest+json`).
2. **Builder Provenance (Stamp 1: Origin)**:
   - Builder generates SLSA-aligned in-toto Statement v1 binding git commit, builder environment, and subject file SHA-256 digests.
   - Signed by builder key (`application/vnd.segel.origin+json`).
3. **Deterministic Inspector (Stamp 2: Inspect)**:
   - Deterministic policy evaluates capabilities: `listen_port`, `logging_destination`.
   - Verdict: **PASS** (0 warnings, 0 rejections).
   - Signed by Inspector Signer key (`application/vnd.segel.inspect+json`).
4. **Multi-Party Approval (Stamp 3: Approve)**:
   - 2-of-3 threshold satisfied across distinct approvers (`approver-0` in `group-0` and `approver-1` in `group-1`).
   - Compact QR payload generated for air-gapped transmission.
   - Signed by approver keys (`application/vnd.segel.approve+json`).
5. **Transparency Ledger & Witness (Stamp 4: Record)**:
   - Candidate event recorded in append-only SQLite Merkle tree (`candidate_recorded`).
   - Checkpoint signed by Ledger Signer (`size=1`, `root_hash`).
   - External Witness verifies consistency proof and adds cosignature.
6. **Canary Verification & Promotion (Stamp 5: Test)**:
   - Candidate passport assembled and dispatched to `canary-1` and `canary-2`.
   - Canary units stage, verify stamps, deploy, and emit signed health receipts.
   - Promotion Controller evaluates receipts (2 healthy units, required probes valid).
   - Promotion proof appended to ledger (`release_promoted`), second checkpoint cosigned.
7. **Offline Receiver Verification**:
   - General Receiver (`unit-3`) in air-gapped posture receives General Release Passport.
   - Verifies 5 independent cryptographic stamps with author exclusion (SEC-001) and distinct key thresholds (FR-033).
   - Atomically deploys to staging directory and moves to active target.
   - Verdict: **DEPLOYED SUCCESSFULLY**.

---

## 4. Act 2: Deterministic Policy Rejection (Privilege Escalation)

### Narrative
An attacker or compromised workstation attempts to smuggle an unauthorized root account into a configuration release.

### Steps & Real Artifacts
1. **Malicious Release Payload**:
   - Candidate file contains: `{"accounts": [{"name": "evil_admin", "privilege": "root"}]}`.
   - Purpose declared: `"Routine operator maintenance update"`.
2. **Deterministic Inspection (`PRULE-004`)**:
   - Capability extracted: `privilege_granted#1` (severity `reject`).
   - Inspector evaluates deterministic policy rules: `PRULE-004` triggers immediate **REJECT**.
   - Inspector finding: `"Elevated privileges granted to account — not allowed in configuration releases"`.
3. **Fail-Closed Gate Enforcement**:
   - Ledger candidate evidence verifier checks inspect verdict. Because verdict is `REJECT`, ledger rejects entry (`ErrorCode.INSPECT_REJECTED`).
   - Approver CLI aborts signing.
   - Even if the AI model were queried, AI findings cannot lower a deterministic `REJECT` verdict (PRD v2.0 §7.5, Decision D4).
   - Pipeline result: **BLOCKED AT INSPECTION (FAIL CLOSED)**.

---

## 5. Act 3: Ambiguous Intent & AI Advisory (`DEV-14`)

### Narrative
An engineer submits `DEV-14`: a release adding both an outbound firewall rule and a DNS resolver change under a vague, non-specific purpose description.

### Steps & Real Artifacts
1. **Corpus Item `DEV-14` Properties**:
   - **Declared Purpose**: `"Synchronize communication parameters for branch office gateway node"`
   - **Baseline Changes**:
     - `firewall.outbound_allowed`: `10.200.5.1:443/tcp` (`outbound_rule_added#1`)
     - `dns_allowlist`: `10.0.5.53` (`dns_allowlist_change#1`)
   - **Expected Class**: `L4` (outbound rule change).
   - **True Label**: `inconsistent` (silent extra change: DNS change hidden behind general networking text).
2. **AI OFF Behavior (`SEGEL_AI_ENABLED=0`)**:
   - B1 keyword classifier runs over generic purpose text: matches zero specific keywords -> **ABSTAINS** (`None`).
   - Deterministic policy evaluates changes: outbound rule connects to external host (`warn` or `pass`), DNS allowlist change is permitted under policy.
   - Deterministic Verdict: **PASS**.
   - AI Panel: Shows status badge **SKIPPED** with banner: *"AI analysis is disabled by configuration. Release verification is fully governed by deterministic policy rules."*
   - Silent inconsistency passes undetected under standard keyword inspection.
3. **AI ON Behavior (`SEGEL_AI_ENABLED=1`)**:
   - Model `qwen3:4b` analyzes declared purpose in process-isolated worker subprocess.
   - Model classifies purpose as **`L6` (Vague / Unclassified)** with advisory reason: *"Purpose describes broad synchronization without specifying single class L1-L5."*
   - Expectation map rule for `L6`: Every candidate capability produces a `warn` finding:
     - `outbound_rule_added#1` (`warn`): `"purpose too vague to verify (AI class L6)"`
     - `dns_allowlist_change#1` (`warn`): `"purpose too vague to verify (AI class L6)"`
   - Merge logic raises overall verdict from `PASS` to **`WARN`**.
   - Release Desk displays separate **AI Advisory** panel with predicted class `L6` and short model reason.
   - Policy requirement `require_warn_acknowledgement` activates: Approvers must explicitly acknowledge the warning digest before the ledger gate will admit the release.
4. **Honest Architectural Statement (Empirical Comparison)**:
   > **Direct Comparison**: While the AI successfully flagged `DEV-14`, **a deterministic vague-by-default rule (such as baseline B1b, which treats any B1 abstention as class L6) would also flag this exact release**. On the broader evaluation corpus, B1b achieves 100% silent detection (11/11) without an LLM, albeit with 2 false positives on consistent releases. The AI's empirical distinction is lower false alarm frequency rather than unique detection capability.

---

## 6. Act 4: Cryptographic Defense (Tamper Evidence & Replay Prevention)

### Narrative
An adversary intercepts a legitimate, signed release package and attempts (a) bit-level content tampering and (b) sequence replay attack.

### Steps & Real Artifacts
1. **Tamper Attack (Modified Payload)**:
   - Adversary flips 1 byte in the staging package payload after builder and author signatures have been placed.
   - Receiver recomputes SHA-256 payload digest and checks Pre-Authentication Encoding (PAE) in the DSSE envelope.
   - Ed25519 signature verification fails (`SIGNATURE_INVALID`).
   - Receiver aborts immediately: staging directory wiped, 0 files deployed.
2. **Replay Attack (Stale Sequence Number)**:
   - Adversary replays a valid, previously signed release (`sequence=1`) to an already updated receiver (`highest_sequence=2`).
   - Receiver state verifier checks monotonically increasing sequence invariant (`current_seq > highest_seq`).
   - Sequence invariant violated: receiver returns error code `SEQUENCE_REPLAY`.
   - Deployment rejected: state remains unchanged.

---

## 7. Execution Guide: Running the Demo

### Option A: Web User Interface Walkthrough
```powershell
# 1. Run preflight
powershell -File scripts/demo_ai_preflight.ps1

# 2. Launch Release Desk with AI enabled
powershell -File scripts/run_demo.ps1 -AiEnabled 1

# 3. Open browser at http://127.0.0.1:8000
# - Navigate to "New Release"
# - Create clean release (Act 1) -> Follow through Approve, Canary, and Promote
# - Create DEV-14 release (Act 3) -> Observe AI Advisory Panel with L6 warning
```

### Option B: Automated Non-Interactive Runner
```powershell
# Executes all 4 acts with AI ON and AI OFF
python scripts/run_demo_scenario.py
```
