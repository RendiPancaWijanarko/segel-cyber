#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Non-interactive runner for SEGEL 6-minute demonstration scenario (MDB §9).

Executes Acts 1 through 4 under both AI OFF and AI ON modes.
Outputs pass/fail status per act.
Complies with repository rules: uses synthetic demo releases and DEV-14 only;
never uses a TEST-* item.
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path

# Force UTF-8 output on Windows
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(WORKSPACE_ROOT / "src"))

from approver.approver import (
    approver_sign,
    collect_approvals,
    create_approval_payload,
)
from builder.builder import build_release_package, sign_manifest, sign_origin
from inspector.inspector import inspect_release, sign_inspect, create_inspect_attestation
from ledger.ledger import TransparencyLedger
from passport.assembler import build_candidate_passport, build_general_passport
from promotion.controller import CanaryReceipt, evaluate_promotion
from receiver.receiver import Receiver, ReceiverState
from segel_core.canonical import canonical_json, compute_acknowledgement_digest
from segel_core.crypto.ed25519 import export_public_key, generate_keypair
from segel_core.errors import DigestMismatchError, ErrorCode
from segel_core.schemas.attestation import PromotionCriteria
from segel_core.schemas.passport import LedgerProof, ReleasePassport
from segel_core.schemas.trust import (
    KeyRecord,
    RoleThreshold,
    TrustRoot,
    TrustSnapshot,
    VerificationPolicy,
)
from segel_core.verification.passport import EligibilityClass, verify_passport
from segel_core.verification.trust import TrustContext
from witness.witness import Witness


def _kr(kp, role: str, group: str = "default") -> KeyRecord:
    return KeyRecord(
        key_id=kp.key_id,
        public_key_b64=export_public_key(kp.public_key_bytes),
        role=role,
        group=group,
    )


def setup_demo_context():
    """Build synthetic demo trust context and keyrings."""
    keys = {
        "author": generate_keypair(),
        "builder": generate_keypair(),
        "inspector": generate_keypair(),
        "approvers": [generate_keypair() for _ in range(3)],
        "ledger": generate_keypair(),
        "witness": generate_keypair(),
        "canaries": [generate_keypair() for _ in range(2)],
        "receiver": generate_keypair(),
    }

    trust_root = TrustRoot(
        root_version=1,
        keys=[
            _kr(keys["author"], "author"),
            _kr(keys["builder"], "builder"),
            _kr(keys["inspector"], "inspector_signer"),
            _kr(keys["approvers"][0], "approver", "group-0"),
            _kr(keys["approvers"][1], "approver", "group-1"),
            _kr(keys["approvers"][2], "approver", "group-0"),
            _kr(keys["ledger"], "ledger"),
            _kr(keys["witness"], "witness"),
            _kr(keys["canaries"][0], "receiver"),
            _kr(keys["canaries"][1], "receiver"),
            _kr(keys["receiver"], "receiver"),
        ],
        roles=[
            RoleThreshold(role="author", threshold=1),
            RoleThreshold(role="builder", threshold=1),
            RoleThreshold(role="inspector_signer", threshold=1),
            RoleThreshold(
                role="approver",
                threshold=2,
                group_minimums={"group-0": 1, "group-1": 1},
            ),
            RoleThreshold(role="ledger", threshold=1),
            RoleThreshold(role="witness", threshold=1),
            RoleThreshold(role="receiver", threshold=1),
        ],
    )

    policy = VerificationPolicy(
        policy_version=1,
        required_stamps=["origin", "inspect", "approve", "record", "test"],
        approval_threshold=2,
        approval_groups={"group-0": 1, "group-1": 1},
        canary_required_count=2,
        witness_cosignature_count=1,
        require_warn_acknowledgement=True,
    )

    snapshot = TrustSnapshot(epoch=1)
    trust_ctx = TrustContext(root=trust_root, policy=policy, snapshot=snapshot)
    return keys, trust_ctx


def run_act_1_golden_path(ai_mode: bool) -> bool:
    """Act 1: The Golden Path — Clean configuration release through all 5 stamps."""
    keys, trust_ctx = setup_demo_context()
    deploy_dir = Path(tempfile.mkdtemp(prefix="segel-act1-"))

    cand = {
        "dns_allowlist": ["10.0.0.53", "10.0.1.53"],
        "firewall": {"outbound_allowed": []},
        "services": {"enabled": [], "disabled": []},
        "accounts": [],
        "logging": {"enabled": True, "destination": ""},
        "scheduled_tasks": [],
        "trust_anchors": [],
    }
    clean_files = {
        "baseline.json": json.dumps(cand, indent=2).encode("utf-8")
    }

    # 1. Author & Builder
    build_res = build_release_package(
        files=clean_files,
        release_id="BASELINE-UNIT-42",
        sequence=1,
        purpose="Update internal DNS resolvers for branch office gateway",
        canary_targets=["canary-1", "canary-2"],
        general_scope=["canary-1", "canary-2", "unit-3"],
    )
    manifest_env = sign_manifest(build_res, keys["author"])
    origin_env = sign_origin(build_res, keys["builder"])

    # 2. Inspect
    inspection = inspect_release(
        files=clean_files,
        manifest=build_res.manifest,
        manifest_digest=build_res.manifest_digest,
        ai_enabled=ai_mode,
    )
    if inspection.verdict != "PASS":
        print(f"       [ACT 1 FAIL] Expected verdict PASS, got {inspection.verdict}")
        return False

    inspect_stmt = create_inspect_attestation(
        inspection, build_res.manifest, build_res.manifest_digest
    )
    inspect_env = sign_inspect(inspect_stmt, keys["inspector"])

    # 3. Approve
    approve_stmt, approve_req = create_approval_payload(
        manifest=build_res.manifest,
        manifest_digest=build_res.manifest_digest,
        origin_envelope=origin_env,
        inspect_envelope=inspect_env,
        inspect_verdict=inspection.verdict,
        canary_targets=["canary-1", "canary-2"],
        promotion_criteria=PromotionCriteria(
            required_healthy_canary_units=2,
            required_probes=["file_exists", "config_valid"],
        ),
    )
    from approver.approver import approver_sign
    resp0 = approver_sign(approve_req, keys["approvers"][0])
    resp1 = approver_sign(approve_req, keys["approvers"][1])
    approve_env = collect_approvals(approve_stmt, approve_req, [resp0, resp1])

    # 4. Ledger & Witness
    ledger_db = deploy_dir / "ledger.db"
    ledger = TransparencyLedger(db_path=str(ledger_db))
    cand_event = {
        "event_type": "candidate_recorded",
        "release_id": "BASELINE-UNIT-42",
        "sequence": 1,
        "manifest_sha256": build_res.manifest_digest,
    }
    entry = ledger.append("candidate_recorded", cand_event)
    signed_cp = ledger.sign_checkpoint(keys["ledger"])
    witness = Witness(witness_key=keys["witness"])
    cosig = witness.cosign_checkpoint(signed_cp.checkpoint)
    ledger.add_witness_cosignature(signed_cp.checkpoint.size, keys["witness"].key_id, cosig)

    proof = ledger.inclusion_proof(entry.index)
    ledger_proof = LedgerProof(
        event_type="candidate_recorded",
        entry_index=proof.entry_index,
        leaf_hash=proof.leaf_hash,
        inclusion_proof=proof.proof,
        checkpoint_size=proof.checkpoint_size,
        checkpoint_root_hash=proof.checkpoint_root_hash,
        checkpoint_signature=signed_cp.ledger_signature,
        witness_cosignatures=[cosig],
    )

    candidate_passport = build_candidate_passport(
        manifest_env, origin_env, inspect_env, approve_env,
        ledger_proof, signed_cp, min_epoch=1,
    )

    # 5. Canaries & Promotion
    canary_receipts = []
    canary_receipt_envelopes = []
    for i, c_key in enumerate(keys["canaries"]):
        c_dir = deploy_dir / f"canary-{i+1}"
        c_dir.mkdir(parents=True, exist_ok=True)
        c_state = ReceiverState(
            unit_id=f"canary-{i+1}",
            unit_role="canary",
        )
        c_rx = Receiver(
            state=c_state,
            trust_ctx=trust_ctx,
            receiver_key=c_key,
            deploy_root=c_dir / "app",
        )
        verif, receipt_env = c_rx.verify_and_deploy(candidate_passport, clean_files)
        if not verif.all_stamps_valid or verif.eligibility != EligibilityClass.ELIGIBLE_CANARY or receipt_env is None:
            print(f"       [ACT 1 FAIL] Canary {i+1} verify_and_deploy failed: {verif.eligibility_reasons}")
            return False
        receipt_payload = json.loads(receipt_env.get_payload_bytes())
        pred = receipt_payload.get("predicate", {})
        canary_receipts.append(
            CanaryReceipt(
                unit_id=f"canary-{i+1}",
                overall_result=pred.get("overall_result", "healthy"),
                health_results=pred.get("health_results", []),
                envelope=receipt_env,
            )
        )
        canary_receipt_envelopes.append(receipt_env)

    criteria = PromotionCriteria(
        required_healthy_canary_units=2,
        required_probes=["file_exists", "config_valid"],
    )
    promo_res = evaluate_promotion(
        criteria=criteria,
        receipts=canary_receipts,
    )
    if not promo_res.promoted:
        print(f"       [ACT 1 FAIL] Promotion evaluation failed: {promo_res.reason}")
        return False

    promo_event = {
        "event_type": "release_promoted",
        "release_id": "BASELINE-UNIT-42",
        "sequence": 1,
        "manifest_sha256": build_res.manifest_digest,
        "healthy_canary_units": promo_res.healthy_units,
    }
    entry_p = ledger.append("release_promoted", promo_event)
    signed_cp_p = ledger.sign_checkpoint(keys["ledger"])
    consistency_proof = ledger._tree.consistency_proof(signed_cp.checkpoint.size, signed_cp_p.checkpoint.size)
    cosig2 = witness.cosign_checkpoint(signed_cp_p.checkpoint, consistency_proof=consistency_proof)
    ledger.add_witness_cosignature(signed_cp_p.checkpoint.size, keys["witness"].key_id, cosig2)

    proof_p = ledger.inclusion_proof(entry_p.index)
    ledger_proof_p = LedgerProof(
        event_type="release_promoted",
        entry_index=proof_p.entry_index,
        leaf_hash=proof_p.leaf_hash,
        inclusion_proof=proof_p.proof,
        checkpoint_size=proof_p.checkpoint_size,
        checkpoint_root_hash=proof_p.checkpoint_root_hash,
        checkpoint_signature=signed_cp_p.ledger_signature,
        witness_cosignatures=[cosig2],
    )
    general_passport = build_general_passport(
        manifest_envelope=manifest_env,
        origin_envelope=origin_env,
        inspect_envelope=inspect_env,
        approve_envelope=approve_env,
        candidate_proof=ledger_proof,
        test_envelopes=canary_receipt_envelopes,
        promotion_proof=ledger_proof_p,
        signed_checkpoint=signed_cp_p,
        min_epoch=1,
    )

    # 6. General Receiver Deployment
    gen_dir = deploy_dir / "unit-3"
    gen_dir.mkdir(parents=True, exist_ok=True)
    gen_state = ReceiverState(
        unit_id="unit-3",
        unit_role="general",
    )
    gen_rx = Receiver(
        state=gen_state,
        trust_ctx=trust_ctx,
        receiver_key=keys["receiver"],
        deploy_root=gen_dir / "app",
    )
    gen_verif, gen_receipt = gen_rx.verify_and_deploy(general_passport, clean_files)
    if not (gen_verif.all_stamps_valid and gen_verif.eligibility == EligibilityClass.ELIGIBLE_GENERAL and gen_receipt is not None):
        print(f"       [ACT 1 FAIL] General deployment failed: {gen_verif.eligibility_reasons}")
        return False
    return True


def run_act_2_policy_rejection(ai_mode: bool) -> bool:
    """Act 2: Deterministic Policy Violation Rejection — Root privilege escalation blocked fail-closed."""
    keys, trust_ctx = setup_demo_context()
    malicious_files = {
        "baseline.json": b'{"accounts": [{"name": "evil_admin", "privilege": "root"}]}'
    }
    build_res = build_release_package(
        files=malicious_files,
        release_id="MALICIOUS-ROOT-01",
        sequence=1,
        purpose="Routine operator maintenance update",
        canary_targets=["canary-1", "canary-2"],
        general_scope=["unit-3"],
    )

    inspection = inspect_release(
        files=malicious_files,
        manifest=build_res.manifest,
        manifest_digest=build_res.manifest_digest,
        ai_enabled=ai_mode,
    )

    # Verification: deterministic verdict must strictly be REJECT
    # Even if AI is enabled, it cannot lower or suppress this REJECT
    if inspection.verdict != "REJECT":
        print(f"       [ACT 2 FAIL] Expected REJECT, got {inspection.verdict}")
        return False

    has_prule_004 = any(f.capability_id == "PRULE-004" for f in inspection.deterministic_findings)
    return has_prule_004


def run_act_3_ambiguous_dev14(ai_mode: bool) -> tuple[bool, str]:
    """Act 3: Ambiguous / Silent Mismatch with DEV-14.
    
    DEV-14 purpose: 'Synchronize communication parameters for branch office gateway node'.
    Changes: outbound_rule_added + dns_allowlist_change.
    - When AI OFF: B1 abstains, verdict is PASS.
    - When AI ON: AI classifies L6, raises verdict to WARN with 2 advisory findings.
    - Direct statement: A vague-by-default rule (B1b) would also flag this release deterministically.
    """
    dev14_path = WORKSPACE_ROOT / "lab" / "ai_corpus" / "DEV-14.json"
    dev14 = json.loads(dev14_path.read_text(encoding="utf-8"))
    cand = dev14["candidate_baseline"]
    purpose = dev14["purpose"]

    files = {"baseline.json": json.dumps(cand).encode("utf-8")}
    build_res = build_release_package(
        files=files,
        release_id="DEV-14-RELEASE",
        sequence=1,
        purpose=purpose,
        canary_targets=["canary-1"],
        general_scope=["unit-3"],
    )

    inspection = inspect_release(
        files=files,
        manifest=build_res.manifest,
        manifest_digest=build_res.manifest_digest,
        ai_enabled=ai_mode,
    )

    if not ai_mode:
        # AI OFF: B1 abstains, deterministic verdict is PASS
        is_ok = (inspection.verdict == "PASS" and inspection.ai_status == "skipped" and len(inspection.ai_findings) == 0)
        detail = (
            f"AI OFF -> Verdict: {inspection.verdict}, AI Status: {inspection.ai_status}. "
            "B1 classifier abstained on non-specific purpose; deterministic rules passed. "
            "(Plain note: A deterministic vague-by-default rule such as B1b would also flag this release without AI)."
        )
        return is_ok, detail
    else:
        # AI ON: AI classifies as L6 (vague), raises verdict to WARN, emits 2 warn findings
        is_l6 = (inspection.ai_class == "L6" or any("L6" in f.description for f in inspection.ai_findings))
        is_warn = (inspection.verdict == "WARN")
        is_ok = is_l6 and is_warn and inspection.ai_status == "ok"
        detail = (
            f"AI ON -> Verdict: {inspection.verdict}, AI Status: {inspection.ai_status}, AI Class: {inspection.ai_class}. "
            f"Model flagged purpose as too vague to verify, generating {len(inspection.ai_findings)} WARN findings. "
            "(Plain note: A deterministic vague-by-default rule such as B1b would also flag this release without AI)."
        )
        return is_ok, detail


def run_act_4_cryptographic_defense() -> bool:
    """Act 4: Cryptographic Defense — Tampering detection and sequence replay rejection."""
    keys, trust_ctx = setup_demo_context()
    deploy_dir = Path(tempfile.mkdtemp(prefix="segel-act4-"))

    clean_files = {"config/app.yaml": b"server: port 80\n"}
    build_res = build_release_package(
        files=clean_files,
        release_id="CRYPTO-DEFENSE-01",
        sequence=2,
        purpose="Cryptographic integrity verification test",
        canary_targets=["canary-1"],
        general_scope=["unit-3"],
    )
    manifest_env = sign_manifest(build_res, keys["author"])
    origin_env = sign_origin(build_res, keys["builder"])
    inspection = inspect_release(clean_files, build_res.manifest, build_res.manifest_digest, ai_enabled=False)
    inspect_stmt = create_inspect_attestation(inspection, build_res.manifest, build_res.manifest_digest)
    inspect_env = sign_inspect(inspect_stmt, keys["inspector"])

    approve_stmt, approve_req = create_approval_payload(
        build_res.manifest, build_res.manifest_digest, origin_env, inspect_env, inspection.verdict,
        canary_targets=["canary-1"],
        promotion_criteria=PromotionCriteria(required_healthy_canary_units=1, required_probes=["file_exists"]),
    )
    from approver.approver import approver_sign
    r0 = approver_sign(approve_req, keys["approvers"][0])
    r1 = approver_sign(approve_req, keys["approvers"][1])
    approve_env = collect_approvals(approve_stmt, approve_req, [r0, r1])

    ledger = TransparencyLedger(db_path=str(deploy_dir / "ledger.db"))
    entry = ledger.append("candidate_recorded", {"release_id": "CRYPTO-DEFENSE-01", "sequence": 2})
    signed_cp = ledger.sign_checkpoint(keys["ledger"])
    witness = Witness(witness_key=keys["witness"])
    cosig = witness.cosign_checkpoint(signed_cp.checkpoint)
    ledger.add_witness_cosignature(signed_cp.checkpoint.size, keys["witness"].key_id, cosig)

    proof = ledger.inclusion_proof(entry.index)
    ledger_proof = LedgerProof(
        event_type="candidate_recorded",
        entry_index=proof.entry_index,
        leaf_hash=proof.leaf_hash,
        inclusion_proof=proof.proof,
        checkpoint_size=proof.checkpoint_size,
        checkpoint_root_hash=proof.checkpoint_root_hash,
        checkpoint_signature=signed_cp.ledger_signature,
        witness_cosignatures=[cosig],
    )
    candidate_passport = build_candidate_passport(
        manifest_env, origin_env, inspect_env, approve_env,
        ledger_proof, signed_cp, min_epoch=1,
    )

    # Sub-case A: Content tampering
    tampered_files = {"config/app.yaml": b"server: port 666 (tampered)\n"}
    tamper_dir = deploy_dir / "canary-tamper"
    tamper_dir.mkdir(parents=True, exist_ok=True)
    tamper_state = ReceiverState(
        unit_id="canary-1",
        unit_role="canary",
    )
    tamper_rx = Receiver(
        state=tamper_state,
        trust_ctx=trust_ctx,
        receiver_key=keys["canaries"][0],
        deploy_root=tamper_dir / "app",
    )
    tamper_blocked = False
    try:
        verif_t, receipt_t = tamper_rx.verify_and_deploy(candidate_passport, tampered_files)
        if receipt_t is not None:
            receipt_payload = json.loads(receipt_t.get_payload_bytes())
            overall = receipt_payload.get("predicate", {}).get("overall_result", "")
            if overall == "error":
                tamper_blocked = True
        else:
            tamper_blocked = True
    except DigestMismatchError:
        tamper_blocked = True
    except Exception as e:
        if "Digest mismatch" in str(e) or "mismatch" in str(e).lower():
            tamper_blocked = True

    # Sub-case B: Monotonic sequence replay attack
    # Update receiver state sequence to 5 (candidate is sequence 2)
    replay_dir = deploy_dir / "canary-replay"
    replay_dir.mkdir(parents=True, exist_ok=True)
    replay_state = ReceiverState(
        unit_id="canary-1",
        unit_role="canary",
        highest_sequence={"CRYPTO-DEFENSE-01": 5},
    )
    replay_rx = Receiver(
        state=replay_state,
        trust_ctx=trust_ctx,
        receiver_key=keys["canaries"][0],
        deploy_root=replay_dir / "app",
    )
    verif_r, receipt_r = replay_rx.verify_and_deploy(candidate_passport, clean_files)
    replay_blocked = (
        (not verif_r.all_stamps_valid)
        or (
            verif_r.eligibility == EligibilityClass.INELIGIBLE
            and any("anti-rollback" in r.lower() or "sequence" in r.lower() for r in verif_r.eligibility_reasons)
            and receipt_r is None
        )
    )

    return tamper_blocked and replay_blocked


def run_full_scenario() -> int:
    print("======================================================================")
    print("  SEGEL 6-Minute Demonstration Scenario Runner (MDB §9)")
    print("======================================================================")
    print("Rule check: Synthetic demo releases and DEV-14 only. Zero TEST-* items.")
    print("")

    results: dict[str, dict[str, str]] = {
        "AI OFF (Deterministic Only)": {},
        "AI ON (Deterministic + Advisory)": {},
    }

    # ───────────────────────────────────────────────────────────────────
    # PASS 1: AI OFF
    # ───────────────────────────────────────────────────────────────────
    print(">>> MODE 1: AI SUBSYSTEM OFF (SEGEL_AI_ENABLED=0)")
    os.environ["SEGEL_AI_ENABLED"] = "0"

    print("  Executing Act 1: The Golden Path (5-Stamp Attestation)...")
    act1_off = run_act_1_golden_path(ai_mode=False)
    results["AI OFF (Deterministic Only)"]["Act 1: Golden Path"] = "PASS" if act1_off else "FAIL"
    print(f"  Result: {'[PASS]' if act1_off else '[FAIL]'}")

    print("  Executing Act 2: Deterministic Policy Rejection (Privilege Escalation)...")
    act2_off = run_act_2_policy_rejection(ai_mode=False)
    results["AI OFF (Deterministic Only)"]["Act 2: Policy Rejection"] = "PASS" if act2_off else "FAIL"
    print(f"  Result: {'[PASS]' if act2_off else '[FAIL]'}")

    print("  Executing Act 3: Ambiguous Intent on DEV-14 (Silent Inconsistency)...")
    act3_off, act3_off_msg = run_act_3_ambiguous_dev14(ai_mode=False)
    results["AI OFF (Deterministic Only)"]["Act 3: Ambiguous DEV-14"] = "PASS" if act3_off else "FAIL"
    print(f"  Result: {'[PASS]' if act3_off else '[FAIL]'}")
    print(f"    Detail: {act3_off_msg}")

    print("  Executing Act 4: Cryptographic Defense (Tampering & Replay Defense)...")
    act4_off = run_act_4_cryptographic_defense()
    results["AI OFF (Deterministic Only)"]["Act 4: Cryptographic Defense"] = "PASS" if act4_off else "FAIL"
    print(f"  Result: {'[PASS]' if act4_off else '[FAIL]'}")
    print("")

    # ───────────────────────────────────────────────────────────────────
    # PASS 2: AI ON
    # ───────────────────────────────────────────────────────────────────
    print(">>> MODE 2: AI SUBSYSTEM ON (SEGEL_AI_ENABLED=1, qwen3:4b)")
    os.environ["SEGEL_AI_ENABLED"] = "1"
    os.environ["SEGEL_AI_ENDPOINT"] = "http://127.0.0.1:11434"

    print("  Executing Act 1: The Golden Path (5-Stamp Attestation with AI advisory)...")
    act1_on = run_act_1_golden_path(ai_mode=True)
    results["AI ON (Deterministic + Advisory)"]["Act 1: Golden Path"] = "PASS" if act1_on else "FAIL"
    print(f"  Result: {'[PASS]' if act1_on else '[FAIL]'}")

    print("  Executing Act 2: Deterministic Policy Rejection (Privilege Escalation with AI on)...")
    act2_on = run_act_2_policy_rejection(ai_mode=True)
    results["AI ON (Deterministic + Advisory)"]["Act 2: Policy Rejection"] = "PASS" if act2_on else "FAIL"
    print(f"  Result: {'[PASS]' if act2_on else '[FAIL]'}")

    print("  Executing Act 3: Ambiguous Intent on DEV-14 (AI Advisory & Class L6 Detection)...")
    act3_on, act3_on_msg = run_act_3_ambiguous_dev14(ai_mode=True)
    results["AI ON (Deterministic + Advisory)"]["Act 3: Ambiguous DEV-14"] = "PASS" if act3_on else "FAIL"
    print(f"  Result: {'[PASS]' if act3_on else '[FAIL]'}")
    print(f"    Detail: {act3_on_msg}")

    print("  Executing Act 4: Cryptographic Defense (Tampering & Replay Defense with AI on)...")
    act4_on = run_act_4_cryptographic_defense()
    results["AI ON (Deterministic + Advisory)"]["Act 4: Cryptographic Defense"] = "PASS" if act4_on else "FAIL"
    print(f"  Result: {'[PASS]' if act4_on else '[FAIL]'}")
    print("")

    # ───────────────────────────────────────────────────────────────────
    # SUMMARY TABLE
    # ───────────────────────────────────────────────────────────────────
    print("======================================================================")
    print("  DEMO SCENARIO EXECUTION SUMMARY")
    print("======================================================================")
    print(f"{'Act':<35} | {'AI OFF Mode':<12} | {'AI ON Mode':<12}")
    print("-" * 65)

    acts = [
        "Act 1: Golden Path",
        "Act 2: Policy Rejection",
        "Act 3: Ambiguous DEV-14",
        "Act 4: Cryptographic Defense",
    ]

    all_passed = True
    for a in acts:
        st_off = results["AI OFF (Deterministic Only)"].get(a, "UNKNOWN")
        st_on = results["AI ON (Deterministic + Advisory)"].get(a, "UNKNOWN")
        if st_off != "PASS" or st_on != "PASS":
            all_passed = False
        print(f"{a:<35} | {st_off:<12} | {st_on:<12}")

    print("-" * 65)
    overall_status = "ALL ACTS PASSED" if all_passed else "FAILURES DETECTED"
    print(f"Overall Scenario Status: {overall_status}")
    print("======================================================================")

    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(run_full_scenario())
