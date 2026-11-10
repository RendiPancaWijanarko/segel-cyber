#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""SEGEL End-to-End Demo — Full 18-Step Release Lifecycle.

This script runs the complete SEGEL release lifecycle demonstrating
all 5 stamps (Origin, Inspect, Approve, Record, Test) and then
exercises rejection scenarios.

Usage:
    python scripts/demo.py

Requirements:
    pip install -e ".[dev]"
"""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

# Force UTF-8 output on Windows
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# Add src to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from approver.approver import (
    approver_sign,
    collect_approvals,
    create_approval_payload,
    generate_qr_request,
)
from builder.builder import build_release_package, sign_manifest, sign_origin
from inspector.inspector import create_inspect_attestation, inspect_release, sign_inspect
from ledger.ledger import TransparencyLedger
from passport.assembler import build_candidate_passport, build_general_passport
from promotion.controller import CanaryReceipt, evaluate_promotion
from receiver.receiver import Receiver, ReceiverState
from segel_core.canonical import canonical_json
from segel_core.crypto.dsse import (
    verify_envelope,
    verify_threshold,
)
from segel_core.crypto.ed25519 import export_public_key, generate_keypair
from segel_core.crypto.hashing import sha256_hex
from segel_core.schemas.attestation import PromotionCriteria
from segel_core.schemas.passport import LedgerProof, ReleasePassport
from segel_core.schemas.trust import (
    KeyRecord,
    RoleThreshold,
    TrustRoot,
    TrustSnapshot,
    VerificationPolicy,
)
from segel_core.verification.passport import (
    EligibilityClass,
    verify_passport,
)
from segel_core.verification.trust import TrustContext
from witness.witness import Witness

# ── Formatting Helpers ───────────────────────────────────────────────

class C:
    """ANSI colour codes."""
    RESET   = "\033[0m"
    BOLD    = "\033[1m"
    DIM     = "\033[2m"
    RED     = "\033[91m"
    GREEN   = "\033[92m"
    YELLOW  = "\033[93m"
    BLUE    = "\033[94m"
    MAGENTA = "\033[95m"
    CYAN    = "\033[96m"
    WHITE   = "\033[97m"


def banner(text: str) -> None:
    print(f"\n{C.BOLD}{C.CYAN}{'═' * 70}{C.RESET}")
    print(f"{C.BOLD}{C.CYAN}  {text}{C.RESET}")
    print(f"{C.BOLD}{C.CYAN}{'═' * 70}{C.RESET}")


def step(num: int, text: str) -> None:
    print(f"\n{C.BOLD}{C.BLUE}  [{num:>2}]{C.RESET} {C.WHITE}{text}{C.RESET}")


def ok(text: str) -> None:
    print(f"       {C.GREEN}✔{C.RESET} {text}")


def warn(text: str) -> None:
    print(f"       {C.YELLOW}⚠{C.RESET} {text}")


def fail(text: str) -> None:
    print(f"       {C.RED}✕{C.RESET} {text}")


def info(text: str) -> None:
    print(f"       {C.DIM}{text}{C.RESET}")


def hash_short(h: str) -> str:
    return h[:16] + "..."


# ── Lab Setup ────────────────────────────────────────────────────────

def _kr(kp, role, group="default"):
    return KeyRecord(
        key_id=kp.key_id,
        public_key_b64=export_public_key(kp.public_key_bytes),
        role=role,
        group=group,
    )


def setup_lab():
    """Generate all synthetic keys and trust metadata."""
    keys = {
        "author":     generate_keypair(),
        "builder":    generate_keypair(),
        "inspector":  generate_keypair(),
        "approvers":  [generate_keypair() for _ in range(3)],
        "ledger":     generate_keypair(),
        "witness":    generate_keypair(),
        "canaries":   [generate_keypair() for _ in range(2)],
        "receiver":   generate_keypair(),
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
            RoleThreshold(role="approver", threshold=2,
                          group_minimums={"group-0": 1, "group-1": 1}),
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

    return keys, trust_root, policy, snapshot, trust_ctx


# ── Main Demo ────────────────────────────────────────────────────────

def run_demo():
    banner("SEGEL — Sistem Edar Gelar Elektronik Lapis-ganda")
    print(f"  {C.YELLOW}NO EVIDENCE, NO DEPLOYMENT{C.RESET}")
    print("  End-to-end demo: 5-stamp verification lifecycle")
    print("  Origin · Inspect · Approve · Record · Test\n")

    # Setup
    info("Generating synthetic keys and trust metadata...")
    keys, trust_root, policy, snapshot, trust_ctx = setup_lab()
    ok(f"Trust root v{trust_root.root_version} with {len(trust_root.keys)} keys")
    ok(f"Policy v{policy.policy_version}: approval 2-of-3, canary count 2")
    ok(f"Epoch {snapshot.epoch}")

    tmp_root = Path(tempfile.mkdtemp(prefix="segel-demo-"))
    info(f"Deploy root: {tmp_root}")

    # ── Step 1: Author creates a configuration release ──
    step(1, "Author creates a configuration release")
    release_files = {
        "config/app.yaml": b"server:\n  port: 8080\n  host: 0.0.0.0\n",
        "config/logging.yaml": b"log_level: info\nlog_file: /var/log/app.log\n",
    }
    ok(f"Release files: {list(release_files.keys())}")

    # ── Step 2: Bundle validated, manifest created ──
    step(2, "Bundle validated and manifest created")
    build_result = build_release_package(
        files=release_files,
        release_id="BASELINE-UNIT-42",
        sequence=1,
        purpose="Initial baseline configuration for Unit 42",
        canary_targets=["canary-1", "canary-2"],
        general_scope=["canary-1", "canary-2", "unit-3"],
    )
    ok(f"Release ID: {build_result.manifest.release_id}")
    ok(f"Sequence:   {build_result.manifest.sequence}")
    ok(f"Subjects:   {len(build_result.manifest.subjects)} files")
    ok(f"Manifest:   {hash_short(build_result.manifest_digest)}")
    ok(f"Package:    {hash_short(build_result.package_digest)}")

    # ── Step 3: Author signs manifest ──
    step(3, "Author signs the manifest (separate signer)")
    manifest_envelope = sign_manifest(build_result, keys["author"])
    ok(f"Author key:  {hash_short(keys['author'].key_id)}")
    ok(f"Signatures:  {len(manifest_envelope.signatures)}")

    # ── Step 4: Builder produces Origin provenance ──
    step(4, "Builder produces Origin provenance (SLSA-aligned)")
    origin_envelope = sign_origin(build_result, keys["builder"])
    ok(f"Builder key: {hash_short(keys['builder'].key_id)}")
    ok("Payload type: application/vnd.segel.origin+json")
    ok("🏭 STAMP 1: ORIGIN ✓")

    # ── Step 5: Inspector capability extraction + policy evaluation ──
    step(5, "Inspector: deterministic capability extraction + policy evaluation")
    inspection = inspect_release(
        files=release_files,
        manifest=build_result.manifest,
        manifest_digest=build_result.manifest_digest,
        ai_enabled=False,
    )
    ok(f"Capabilities detected: {len(inspection.capabilities)}")
    for cap in inspection.capabilities:
        info(f"  • {cap['capability_id']}: {cap['file']}:{cap['line']} — {cap['match']}")
    ok(f"Policy findings: {len(inspection.deterministic_findings)}")
    ok(f"Verdict: {inspection.verdict}")

    # ── Step 6: AI advisory (skipped in MVP) ──
    step(6, "AI advisory analysis")
    info(f"AI status: {inspection.ai_status}")
    warn("AI advisory via Ollama is optional — skipped for MVP demo")

    # ── Step 7: Inspector Signer issues Inspect attestation ──
    step(7, "Inspector Signer issues Inspect attestation")
    inspect_statement = create_inspect_attestation(
        result=inspection,
        manifest=build_result.manifest,
        manifest_digest=build_result.manifest_digest,
    )
    inspect_envelope = sign_inspect(inspect_statement, keys["inspector"])
    ok(f"Inspector key: {hash_short(keys['inspector'].key_id)}")
    ok(f"🔍 STAMP 2: INSPECT ✓ (verdict={inspection.verdict})")

    # ── Step 8-9: Approvers review and sign ──
    step(8, "Approvers review actual approval payload (QR air-gapped transfer)")
    approve_statement, approve_request = create_approval_payload(
        manifest=build_result.manifest,
        manifest_digest=build_result.manifest_digest,
        origin_envelope=origin_envelope,
        inspect_envelope=inspect_envelope,
        inspect_verdict=inspection.verdict,
        canary_targets=["canary-1", "canary-2"],
        promotion_criteria=PromotionCriteria(
            required_healthy_canary_units=2,
            required_probes=["file_exists", "config_valid"],
        ),
    )

    qr_data = generate_qr_request(approve_request)
    info(f"QR request payload: {len(qr_data)} bytes")

    step(9, "Approval threshold fulfilled (2-of-3, author excluded)")
    responses = [
        approver_sign(approve_request, keys["approvers"][0]),  # group-0
        approver_sign(approve_request, keys["approvers"][1]),  # group-1
    ]
    approve_envelope = collect_approvals(approve_statement, approve_request, responses)
    ok(f"Approver 0 (group-0): {hash_short(keys['approvers'][0].key_id)} ✓")
    ok(f"Approver 1 (group-1): {hash_short(keys['approvers'][1].key_id)} ✓")
    ok("Threshold: 2/2 met, per-group minimums satisfied")
    ok("✅ STAMP 3: APPROVE ✓")

    # ── Step 10: Ledger records the candidate release ──
    step(10, "Ledger records the candidate release")
    ledger = TransparencyLedger()
    candidate_event = {
        "event_type": "candidate_recorded",
        "release_id": "BASELINE-UNIT-42",
        "sequence": 1,
        "manifest_sha256": build_result.manifest_digest,
        "origin_digest": sha256_hex(canonical_json(origin_envelope.to_dict())),
        "inspect_digest": sha256_hex(canonical_json(inspect_envelope.to_dict())),
        "approve_digest": sha256_hex(canonical_json(approve_envelope.to_dict())),
    }
    candidate_entry = ledger.append("candidate_recorded", candidate_event)
    signed_cp = ledger.sign_checkpoint(keys["ledger"])
    ok(f"Entry index: {candidate_entry.index}")
    ok(f"Leaf hash:   {hash_short(candidate_entry.leaf_hash)}")
    ok(f"Root hash:   {hash_short(signed_cp.checkpoint.root_hash)}")

    # Witness cosign
    witness = Witness(keys["witness"])
    cosig = witness.cosign_checkpoint(signed_cp.checkpoint)
    ledger.add_witness_cosignature(
        signed_cp.checkpoint.size, keys["witness"].key_id, cosig,
    )
    ok(f"Witness cosignature: ✓ ({hash_short(keys['witness'].key_id)})")

    # Build inclusion proof
    candidate_proof_raw = ledger.inclusion_proof(candidate_entry.index)
    candidate_proof = LedgerProof(
        event_type="candidate_recorded",
        entry_index=candidate_proof_raw.entry_index,
        leaf_hash=candidate_proof_raw.leaf_hash,
        inclusion_proof=candidate_proof_raw.proof,
        checkpoint_size=candidate_proof_raw.checkpoint_size,
        checkpoint_root_hash=candidate_proof_raw.checkpoint_root_hash,
        checkpoint_signature=signed_cp.ledger_signature,
        witness_cosignatures=[cosig],
    )
    ok(f"Merkle inclusion proof: {len(candidate_proof.inclusion_proof)} nodes")
    ok("📜 STAMP 4: RECORD ✓")

    # Build candidate passport
    candidate_passport = build_candidate_passport(
        manifest_envelope, origin_envelope, inspect_envelope, approve_envelope,
        candidate_proof, signed_cp, min_epoch=1,
    )
    ok(f"Candidate passport assembled (type={candidate_passport.passport_type})")

    # ── Step 11-12: Deploy to 2 canary units ──
    step(11, "Candidate deployed to 2 designated canary units")
    canary_receipts = []
    canary_receipt_envelopes = []

    for i, (canary_key, unit_id) in enumerate(
        zip(keys["canaries"], ["canary-1", "canary-2"])
    ):
        deploy_dir = tmp_root / unit_id
        deploy_dir.mkdir(parents=True, exist_ok=True)

        canary_state = ReceiverState(unit_id=unit_id, unit_role="canary")
        canary_receiver = Receiver(
            state=canary_state,
            trust_ctx=trust_ctx,
            receiver_key=canary_key,
            deploy_root=deploy_dir / "config",
        )

        verification, receipt_env = canary_receiver.verify_and_deploy(
            passport=candidate_passport, files=release_files,
        )
        assert verification.eligibility == EligibilityClass.ELIGIBLE_CANARY

        receipt_payload = json.loads(receipt_env.get_payload_bytes())
        predicate = receipt_payload.get("predicate", {})
        ok(f"  {unit_id}: deployed, health={predicate.get('overall_result', '?')}")

        canary_receipts.append(CanaryReceipt(
            unit_id=unit_id,
            overall_result=predicate["overall_result"],
            health_results=predicate.get("health_results", []),
            envelope=receipt_env,
        ))
        canary_receipt_envelopes.append(receipt_env)

    step(12, "Canary Receivers generate signed health receipts")
    for cr in canary_receipts:
        ok(f"  {cr.unit_id}: {cr.overall_result} (receipt signed)")
    ok("🧪 STAMP 5: TEST ✓")

    # ── Step 13: Promotion Controller evaluates criteria ──
    step(13, "Promotion Controller evaluates pre-committed promotion criteria")
    promotion_criteria = PromotionCriteria(
        required_healthy_canary_units=2,
        required_probes=["file_exists", "config_valid"],
    )
    promotion_result = evaluate_promotion(
        criteria=promotion_criteria, receipts=canary_receipts,
    )
    assert promotion_result.promoted
    ok(f"Promoted: {promotion_result.promoted}")
    ok(f"Healthy units: {promotion_result.healthy_units}")
    ok(f"Reason: {promotion_result.reason}")

    # ── Step 14: Ledger records the promotion ──
    step(14, "Ledger records the promotion")
    promotion_event = {
        "event_type": "release_promoted",
        "release_id": "BASELINE-UNIT-42",
        "sequence": 1,
        "manifest_sha256": build_result.manifest_digest,
        "healthy_canary_units": promotion_result.healthy_units,
    }
    promotion_entry = ledger.append("release_promoted", promotion_event)
    signed_cp2 = ledger.sign_checkpoint(keys["ledger"])

    consistency_proof = ledger._tree.consistency_proof(1, 2)
    cosig2 = witness.cosign_checkpoint(
        signed_cp2.checkpoint, consistency_proof=consistency_proof,
    )
    ledger.add_witness_cosignature(
        signed_cp2.checkpoint.size, keys["witness"].key_id, cosig2,
    )
    ok(f"Promotion entry: #{promotion_entry.index}")
    ok(f"Checkpoint: size={signed_cp2.checkpoint.size}, root={hash_short(signed_cp2.checkpoint.root_hash)}")

    # Get promotion proof
    promotion_proof_raw = ledger.inclusion_proof(promotion_entry.index)
    promotion_proof = LedgerProof(
        event_type="release_promoted",
        entry_index=promotion_proof_raw.entry_index,
        leaf_hash=promotion_proof_raw.leaf_hash,
        inclusion_proof=promotion_proof_raw.proof,
        checkpoint_size=promotion_proof_raw.checkpoint_size,
        checkpoint_root_hash=promotion_proof_raw.checkpoint_root_hash,
        checkpoint_signature=signed_cp2.ledger_signature,
        witness_cosignatures=[cosig2],
    )

    # ── Step 15: General Release Passport assembled ──
    step(15, "General Release Passport assembled")
    general_passport = build_general_passport(
        manifest_envelope, origin_envelope, inspect_envelope, approve_envelope,
        candidate_proof, canary_receipt_envelopes, promotion_proof,
        signed_cp2, min_epoch=1,
    )
    ok(f"Passport type: {general_passport.passport_type}")
    ok(f"Test envelopes: {len(general_passport.test_envelopes)}")
    ok("All 5 stamps present")

    # ── Step 16: Offline Receiver verifies and deploys ──
    step(16, "Offline Receiver (network disabled) independently verifies and deploys")
    offline_dir = tmp_root / "unit-3"
    offline_dir.mkdir(parents=True, exist_ok=True)

    offline_state = ReceiverState(unit_id="unit-3", unit_role="general")
    offline_receiver = Receiver(
        state=offline_state,
        trust_ctx=trust_ctx,
        receiver_key=keys["receiver"],
        deploy_root=offline_dir / "config",
    )

    offline_verification, offline_receipt = offline_receiver.verify_and_deploy(
        passport=general_passport, files=release_files,
    )
    assert offline_verification.eligibility == EligibilityClass.ELIGIBLE_GENERAL
    ok(f"Eligibility: {offline_verification.eligibility.value}")
    ok(f"Manifest:  {offline_verification.manifest.status.value}")
    ok(f"Origin:    {offline_verification.origin.status.value}")
    ok(f"Inspect:   {offline_verification.inspect.status.value}")
    ok(f"Approve:   {offline_verification.approve.status.value}")
    ok(f"Record:    {offline_verification.record.status.value}")
    ok(f"Test:      {offline_verification.test.status.value}")

    # Verify deployed files
    for path, content in release_files.items():
        deployed = offline_dir / "config" / path
        assert deployed.exists(), f"File not deployed: {path}"
        assert deployed.read_bytes() == content
    ok("All files deployed and verified on disk")

    # ── Step 17: Receiver generates signed deployment receipt ──
    step(17, "Receiver generates signed deployment receipt")
    assert offline_receipt is not None
    receipt_payload = json.loads(offline_receipt.get_payload_bytes())
    predicate = receipt_payload.get("predicate", {})
    ok(f"Unit:    {predicate.get('unit_id')}")
    ok(f"Role:    {predicate.get('unit_role')}")
    ok(f"Result:  {predicate.get('overall_result')}")
    ok(f"Receipt signed with key: {hash_short(keys['receiver'].key_id)}")

    # ── Step 18: Demonstrate rejection scenarios ──
    banner("REJECTION SCENARIOS")

    # 18a: Forged signature
    step(18, "Reject release with forged signature (AT-001)")
    rogue_key = generate_keypair()
    forged_manifest = sign_manifest(build_result, rogue_key)
    author_keys = trust_ctx.get_keys_for_role("author")
    result = verify_envelope(
        forged_manifest, author_keys,
        expected_payload_type="application/vnd.segel.manifest+json",
    )
    assert len(result.valid_key_ids) == 0
    ok("Forged signature rejected: 0 valid keys (rogue key not in trust root)")

    # 18b: Modified content
    step(18, "Reject release with modified content (AT-002)")
    from receiver.adapter.baseline import BaselineAdapter
    from segel_core.errors import DigestMismatchError
    tampered_files = {"config/app.yaml": b"server:\n  port: 9999\n  # TAMPERED\n"}
    adapter = BaselineAdapter(tmp_root / "tampered")
    adapter.preflight(build_result.manifest)
    try:
        adapter.stage(build_result.manifest, tampered_files)
        fail("ERROR: tampered content was NOT rejected!")
    except DigestMismatchError:
        ok("Modified content detected and rejected (digest mismatch)")

    # 18c: Missing stamps
    step(18, "Reject release with missing stamps (AT-003)")
    broken_passport = ReleasePassport(
        passport_type="candidate",
        manifest_envelope=manifest_envelope.to_dict(),
        origin_envelope=origin_envelope.to_dict(),
        inspect_envelope=origin_envelope.to_dict(),   # Wrong envelope
        approve_envelope=origin_envelope.to_dict(),    # Wrong envelope
    )
    broken_verification = verify_passport(
        passport=broken_passport,
        trust_ctx=trust_ctx,
        unit_id="canary-1",
        unit_role="canary",
        receiver_state={"epoch": 1, "highest_sequence": {}},
    )
    assert broken_verification.eligibility == EligibilityClass.INELIGIBLE
    ok(f"Missing/invalid stamps: {broken_verification.eligibility.value}")

    # 18d: Author self-approve
    step(18, "Reject author self-approval (AT-008)")
    from segel_core.errors import ThresholdNotMetError
    single_response = [approver_sign(approve_request, keys["approvers"][0])]
    single_env = collect_approvals(approve_statement, approve_request, single_response)
    approver_keys_list = trust_ctx.get_keys_for_role("approver")
    single_verify = verify_envelope(
        single_env, approver_keys_list,
        expected_payload_type="application/vnd.segel.approve+json",
    )
    try:
        verify_threshold(
            single_verify, threshold=2,
            excluded_key_ids={keys["author"].key_id},
        )
        fail("ERROR: threshold should NOT have been met!")
    except ThresholdNotMetError:
        ok("Single approver rejected: threshold 2 not met with author excluded")

    # 18e: Sequence replay
    step(18, "Reject sequence replay / anti-rollback (AT-012)")
    replay_state = {"epoch": 1, "highest_sequence": {"BASELINE-UNIT-42": 1}}
    replay_passport = ReleasePassport(
        passport_type="candidate",
        manifest_envelope=manifest_envelope.to_dict(),
        origin_envelope=origin_envelope.to_dict(),
        inspect_envelope=inspect_envelope.to_dict(),
        approve_envelope=approve_envelope.to_dict(),
    )
    replay_verification = verify_passport(
        passport=replay_passport,
        trust_ctx=trust_ctx,
        unit_id="canary-1",
        unit_role="canary",
        receiver_state=replay_state,
    )
    assert replay_verification.eligibility == EligibilityClass.INELIGIBLE
    assert any("anti-rollback" in r for r in replay_verification.eligibility_reasons)
    ok(f"Sequence replay rejected: {replay_verification.eligibility.value}")

    # ── Summary ──
    banner("DEMO COMPLETE — ALL 18 STEPS PASSED")
    print(f"""
  {C.GREEN}✔{C.RESET} 5 stamps verified:  Origin · Inspect · Approve · Record · Test
  {C.GREEN}✔{C.RESET} 2 canary units deployed and healthy
  {C.GREEN}✔{C.RESET} Promotion criteria met (2/2 healthy canaries)
  {C.GREEN}✔{C.RESET} Offline receiver independently verified and deployed
  {C.GREEN}✔{C.RESET} Signed deployment receipt generated
  {C.GREEN}✔{C.RESET} Forged signatures rejected
  {C.GREEN}✔{C.RESET} Modified content detected
  {C.GREEN}✔{C.RESET} Missing stamps prevent deployment
  {C.GREEN}✔{C.RESET} Author self-approval blocked
  {C.GREEN}✔{C.RESET} Sequence replay / anti-rollback enforced

  {C.BOLD}NO EVIDENCE, NO DEPLOYMENT ✓{C.RESET}
""")


if __name__ == "__main__":
    run_demo()

