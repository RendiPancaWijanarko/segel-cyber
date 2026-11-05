# SEGEL Pilot Operator Runbook

**Target Milestone**: SEGEL Version 0.1.0-MVP  
**Classification**: Standard Operating Procedures (SOP) & Incident Response  
**Author**: Lead Release Engineer & Operations Specialist  
**Date**: November 3, 2026  

---

## 1. Daily Release Lifecycle Operations

This runbook guides operators through executing a full 5-stamp production release under controlled pilot conditions:

### Phase 1: Authoring & Packaging
1. Prepare the release configuration files (e.g. `config/app.yaml`, `config/logging.yaml`).
2. Run bundle packaging and author signing:
   ```bash
   # Build deterministic bundle and manifest
   python -m builder.cli build \
       --source-dir ./configs \
       --release-id RELEASE-2026-11-A \
       --sequence 1 \
       --purpose "Production config update" \
       --canary-targets canary-1,canary-2 \
       --general-scope canary-1,canary-2,unit-3 \
       --output-dir ./dist
   ```
3. Author signs the manifest using their dedicated author key:
   ```bash
   python -m builder.cli sign-manifest \
       --manifest ./dist/manifest.json \
       --key /etc/segel/keys/author.priv.json \
       --output ./dist/manifest.dsse.json
   ```

---

### Phase 2: Inspection & Policy Validation
1. Run the deterministic capability extraction and policy engine:
   ```bash
   python -m inspector.cli inspect \
       --bundle ./dist/release.tar.gz \
       --manifest ./dist/manifest.json \
       --policy /etc/segel/trust/policy.json \
       --output ./dist/inspect.dsse.json \
       --key /etc/segel/keys/inspector.priv.json
   ```
2. Check verdict:
   - If `PASS`: Proceed to Phase 3.
   - If `WARN`: Review deterministic findings with Security Officer.
   - If `REJECT`: Release rejected. Remediate forbidden configuration parameters.

---

### Phase 3: Approver Quorum & Air-Gapped Transfer
1. Generate the compact approval request payload / QR code:
   ```bash
   segel-approver create-request \
       --manifest ./dist/manifest.dsse.json \
       --origin ./dist/origin.dsse.json \
       --inspect ./dist/inspect.dsse.json \
       --output ./dist/approval_request.cbor
   ```
2. Approvers review the payload on separate air-gapped terminals:
   - **Approver 1 (Security - group-0)**:
     ```bash
     segel-approver sign --request approval_request.cbor --key /etc/segel/keys/approver_sec.priv.json --output approval_sec.resp
     ```
   - **Approver 2 (Operations - group-1)**:
     ```bash
     segel-approver sign --request approval_request.cbor --key /etc/segel/keys/approver_ops.priv.json --output approval_ops.resp
     ```
3. Aggregate approvals into the signed `approve_envelope`:
   ```bash
   segel-approver aggregate \
       --request approval_request.cbor \
       --responses approval_sec.resp,approval_ops.resp \
       --output ./dist/approve.dsse.json
   ```

---

### Phase 4: Ledger Recording & Candidate Passport Assembly
1. Record candidate release in Transparency Ledger:
   ```bash
   # Records event and signs checkpoint
   python -m ledger.cli record-candidate \
       --manifest-digest <digest> \
       --release-id RELEASE-2026-11-A \
       --sequence 1
   ```
2. Request witness cosignature from independent witness daemon:
   ```bash
   segel-witness cosign --host segel-witness:8003 --checkpoint-size <size>
   ```
3. Assemble Candidate Passport:
   ```bash
   python -m passport.cli assemble-candidate \
       --manifest ./dist/manifest.dsse.json \
       --origin ./dist/origin.dsse.json \
       --inspect ./dist/inspect.dsse.json \
       --approve ./dist/approve.dsse.json \
       --ledger-proof ./dist/ledger_proof.json \
       --output ./dist/candidate.passport.json
   ```

---

### Phase 5: Canary Deployment & Health Verification
1. Transfer `candidate.passport.json` and bundle to Canary nodes (`canary-1`, `canary-2`).
2. Execute canary deployment:
   ```bash
   segel-receiver verify ./dist/candidate.passport.json \
       --bundle ./dist/release.tar.gz \
       --unit-id canary-1 \
       --unit-role canary \
       --deploy-to /opt/app/config
   ```
3. Retrieve signed canary deployment receipts:
   - `canary-1.receipt.json`
   - `canary-2.receipt.json`

---

### Phase 6: Promotion & General Passport Assembly
1. Evaluate promotion criteria (requires $\ge 2$ healthy canary receipts):
   ```bash
   python -m promotion.cli evaluate \
       --receipts canary-1.receipt.json,canary-2.receipt.json \
       --criteria-required-count 2 \
       --output ./dist/promotion_result.json
   ```
2. Record promotion in Transparency Ledger and assemble General Passport:
   ```bash
   python -m passport.cli assemble-general \
       --candidate-passport ./dist/candidate.passport.json \
       --canary-receipts canary-1.receipt.json,canary-2.receipt.json \
       --promotion-proof ./dist/promotion_proof.json \
       --output ./dist/general.passport.json
   ```

---

### Phase 7: Air-Gapped Offline Deployment
1. Copy `general.passport.json` and `release.tar.gz` to authorized USB media.
2. Mount on offline general unit (`unit-3`):
   ```bash
   segel-receiver verify /media/usb/general.passport.json \
       --bundle /media/usb/release.tar.gz \
       --unit-id unit-3 \
       --unit-role general \
       --deploy-to /opt/app/config
   ```
3. Verify output:
   - Eligibility: `ELIGIBLE_GENERAL`.
   - Files deployed to `/opt/app/config` with read-only permissions (`-r--r--r--`).
   - Signed receipt written to `/media/usb/unit-3.receipt.json`.

---

## 2. Incident Response & Troubleshooting

### Error: `SIG_INVALID` (Signature Verification Failed)
- **Cause**: Envelope payload was tampered with, or signer key does not match public key in `trust_root.json`.
- **Operator Action**:
  1. Inspect signer key ID in DSSE envelope header.
  2. Verify that key ID exists in `/etc/segel/trust/trust_root.json`.
  3. Ensure file was not altered in transit.

### Error: `THRESHOLD_NOT_MET` (Approval Quorum Incomplete)
- **Cause**: Less than 2 valid approvers signed, or Author attempted self-approval (SEC-001), or per-group minimums were not satisfied.
- **Operator Action**:
  1. Verify Author key is excluded.
  2. Ensure at least one approver from `group-0` and one approver from `group-1` signed.

### Error: `SEQUENCE_REPLAY` (Anti-Rollback Rejection)
- **Cause**: Release sequence number is less than or equal to the sequence currently deployed on the receiver.
- **Operator Action**:
  1. Inspect local receiver state: `cat /var/lib/segel/state/receiver_state.json`.
  2. Verify release sequence. To deploy a rollback configuration, author a **new release** with an **incremented sequence number**.

### Error: `EPOCH_STALE` (Trust Metadata Too Old)
- **Cause**: Receiver is running on an older epoch than required by the release passport.
- **Operator Action**:
  1. Distribute a Trust Update Package to advance receiver epoch.
  2. Verify new `trust_root.json` and `policy.json` are installed in `/etc/segel/trust/`.

### Error: `CHECKPOINT_FORK` (Witness Detected Fork)
- **Cause**: Ledger presented a checkpoint whose Merkle consistency proof does not extend the witness's previously verified root.
- **Operator Action**:
  1. **CRITICAL SECURITY ALERT**: Potential ledger tampering or split-view attack.
  2. Immediately halt all release distributions.
  3. Inspect ledger database logs and alert the Security Operations Center (SOC).

### Error: `STATE_CORRUPT` (Receiver in Recovery Mode)
- **Cause**: Deployment was violently interrupted (power loss or crash) while files were being copied, and rollback could not complete cleanly.
- **Operator Action**:
  1. Run receiver recovery:
     ```bash
     segel-receiver recover --state-dir /var/lib/segel/state --deploy-to /opt/app/config
     ```
  2. If clean backup exists, recovery restores pre-deployment files and clears `recovery_mode: false`.
  3. Re-run deployment verification.

