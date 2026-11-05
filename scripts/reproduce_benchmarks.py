#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""
Repeatable benchmark harness for SEGEL performance claims.

Measures:
1. Offline passport verification (Candidate and General passports)
2. Transparency Ledger append (SQLite WAL mode + RFC 6962 Merkle log)
3. Bundle package build & SHA-256 digest
4. Ed25519 Cryptographic primitives (KeyGen, Sign, Verify)

Outputs comprehensive statistics: Mean, Median, P90, P95, P99, Min, Max, and Throughput (ops/sec).
"""

from __future__ import annotations

import statistics
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

# Add src to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from approver.approver import approver_sign, collect_approvals, create_approval_payload
from builder.builder import build_release_package, sign_manifest, sign_origin
from inspector.inspector import create_inspect_attestation, inspect_release, sign_inspect
from ledger.ledger import TransparencyLedger
from passport.assembler import build_candidate_passport, build_general_passport
from receiver.receiver import Receiver
from segel_core.crypto.ed25519 import export_public_key, generate_keypair, sign, verify
from segel_core.schemas.passport import LedgerProof
from segel_core.schemas.trust import KeyRecord, RoleThreshold, TrustRoot, VerificationPolicy
from segel_core.verification.passport import verify_passport
from segel_core.verification.trust import TrustContext
from witness.witness import Witness


def format_stats(latencies_ms: list[float], name: str) -> dict[str, float | str]:
    latencies_sorted = sorted(latencies_ms)
    n = len(latencies_sorted)
    mean_val = statistics.mean(latencies_sorted)
    median_val = statistics.median(latencies_sorted)
    p90_val = latencies_sorted[int(n * 0.90)]
    p95_val = latencies_sorted[int(n * 0.95)]
    p99_val = latencies_sorted[int(n * 0.99)]
    min_val = latencies_sorted[0]
    max_val = latencies_sorted[-1]
    throughput = 1000.0 / mean_val if mean_val > 0 else 0.0

    print(f"\n--- {name} (N={n} iterations) ---")
    print(f"  Throughput: {throughput:,.1f} ops/sec")
    print(f"  Mean Latency:   {mean_val:.4f} ms")
    print(f"  Median Latency: {median_val:.4f} ms")
    print(f"  P90 Latency:    {p90_val:.4f} ms")
    print(f"  P95 Latency:    {p95_val:.4f} ms")
    print(f"  P99 Latency:    {p99_val:.4f} ms")
    print(f"  Min / Max:      {min_val:.4f} ms / {max_val:.4f} ms")

    return {
        "name": name,
        "n": n,
        "throughput_ops_sec": throughput,
        "mean_ms": mean_val,
        "median_ms": median_val,
        "p90_ms": p90_val,
        "p95_ms": p95_val,
        "p99_ms": p99_val,
        "min_ms": min_val,
        "max_ms": max_val,
    }


def run_benchmarks() -> dict[str, Any]:
    print("=================================================================")
    print("  SEGEL REPEATABLE PERFORMANCE BENCHMARK HARNESS")
    print("=================================================================")
    results = {}

    # Setup environment
    author_key = generate_keypair()
    builder_key = generate_keypair()
    inspector_key = generate_keypair()
    approver1_key = generate_keypair()
    approver2_key = generate_keypair()
    ledger_key = generate_keypair()
    witness_key = generate_keypair()
    receiver_key = generate_keypair()

    trust_root = TrustRoot(
        root_version=1,
        epoch=1,
        keys=[
            KeyRecord(
                key_id=author_key.key_id,
                role="author",
                public_key_b64=export_public_key(author_key.public_key_bytes),
            ),
            KeyRecord(
                key_id=builder_key.key_id,
                role="builder",
                public_key_b64=export_public_key(builder_key.public_key_bytes),
            ),
            KeyRecord(
                key_id=inspector_key.key_id,
                role="inspector_signer",
                public_key_b64=export_public_key(inspector_key.public_key_bytes),
            ),
            KeyRecord(
                key_id=approver1_key.key_id,
                role="approver",
                group="ops",
                public_key_b64=export_public_key(approver1_key.public_key_bytes),
            ),
            KeyRecord(
                key_id=approver2_key.key_id,
                role="approver",
                group="sec",
                public_key_b64=export_public_key(approver2_key.public_key_bytes),
            ),
            KeyRecord(
                key_id=ledger_key.key_id,
                role="ledger",
                public_key_b64=export_public_key(ledger_key.public_key_bytes),
            ),
            KeyRecord(
                key_id=witness_key.key_id,
                role="witness",
                public_key_b64=export_public_key(witness_key.public_key_bytes),
            ),
            KeyRecord(
                key_id=receiver_key.key_id,
                role="receiver",
                public_key_b64=export_public_key(receiver_key.public_key_bytes),
            ),
        ],
        roles=[
            RoleThreshold(role="approver", threshold=2, group_minimums={"ops": 1, "sec": 1}),
        ],
    )
    policy = VerificationPolicy(
        policy_version=1,
        min_inspect_policy_version=1,
        witness_cosignature_count=1,
        canary_required_count=1,
        freshness_mode="strict",
    )
    trust_ctx = TrustContext(root=trust_root, policy=policy)

    # 1. Benchmark: Ed25519 Primitives
    print("\n1. Measuring Ed25519 Cryptographic Primitives...")
    # Warmup
    for _ in range(20):
        kp = generate_keypair()
        sig = sign(kp.private_key, b"warmup")
        verify(kp.public_key, sig, b"warmup")

    # KeyGen
    keygen_times = []
    keys_pool = []
    for _ in range(200):
        t0 = time.perf_counter()
        kp = generate_keypair()
        keygen_times.append((time.perf_counter() - t0) * 1000)
        keys_pool.append(kp)
    results["ed25519_keygen"] = format_stats(keygen_times, "Ed25519 Key Generation")

    # Sign
    data = b"Realistic release manifest digest and DSSE pre-authentication payload bytes"
    sign_times = []
    sigs = []
    bench_key = keys_pool[0]
    for _ in range(500):
        t0 = time.perf_counter()
        s = sign(bench_key.private_key, data)
        sign_times.append((time.perf_counter() - t0) * 1000)
        sigs.append(s)
    results["ed25519_sign"] = format_stats(sign_times, "Ed25519 Signature Generation")

    # Verify
    verify_times = []
    for s in sigs:
        t0 = time.perf_counter()
        verify(bench_key.public_key, s, data)
        verify_times.append((time.perf_counter() - t0) * 1000)
    results["ed25519_verify"] = format_stats(verify_times, "Ed25519 Signature Verification")

    # 2. Benchmark: Transparency Ledger Append (SQLite + WAL + Merkle Tree)
    print("\n2. Measuring Transparency Ledger Append Latency...")
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        bench_db_path = f.name

    ledger = TransparencyLedger(bench_db_path)
    # Warmup
    for i in range(20):
        ledger.append("candidate_recorded", {"warmup": i})

    ledger_append_times = []
    for i in range(300):
        event_data = {
            "release_id": f"BENCH-{i}",
            "sequence": i + 1,
            "manifest_sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
            "entry_timestamp": time.time(),
        }
        t0 = time.perf_counter()
        ledger.append("candidate_recorded", event_data)
        ledger_append_times.append((time.perf_counter() - t0) * 1000)

    results["ledger_append"] = format_stats(ledger_append_times, "Ledger Append (SQLite WAL)")
    ledger.close()

    # 3. Benchmark: Bundle Package Build
    print("\n3. Measuring Bundle Packaging & Hashing...")
    sample_files = {
        "config/app.yaml": b"server:\n  port: 8080\n  host: 0.0.0.0\n",
        "config/logging.yaml": b"log_level: info\nlog_file: /var/log/app.log\n",
        "config/database.yaml": b"pool_size: 10\ntimeout: 30\n",
    }
    # Warmup
    for _ in range(10):
        build_release_package(sample_files, "BENCH-0", 1, "warmup")

    bundle_times = []
    for i in range(150):
        t0 = time.perf_counter()
        build_release_package(sample_files, f"BENCH-{i}", i + 1, "benchmark release")
        bundle_times.append((time.perf_counter() - t0) * 1000)
    results["bundle_build"] = format_stats(bundle_times, "Deterministic Bundle Build")

    # 4. Benchmark: Full Offline Passport Verification
    print("\n4. Measuring Full Offline Release Passport Verification...")
    # Prepare realistic candidate release & passport
    build_res = build_release_package(
        sample_files,
        "BENCH-PASSPORT",
        1,
        "verification bench",
        canary_targets=["canary-1"],
        general_scope=["unit-general"],
    )
    author_manifest_env = sign_manifest(build_res, author_key)
    origin_env = sign_origin(build_res, builder_key)
    inspect_result = inspect_release(sample_files, build_res.manifest, build_res.manifest_digest)
    inspect_stmt = create_inspect_attestation(
        inspect_result, build_res.manifest, build_res.manifest_digest
    )
    inspect_env = sign_inspect(inspect_stmt, inspector_key)

    statement_dict, approval_req = create_approval_payload(
        build_res.manifest,
        build_res.manifest_digest,
        origin_env,
        inspect_env,
        inspect_result.verdict,
    )
    sig1 = approver_sign(approval_req, approver1_key)
    sig2 = approver_sign(approval_req, approver2_key)
    approve_env = collect_approvals(statement_dict, approval_req, [sig1, sig2])

    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        l_db = f.name
    ledger2 = TransparencyLedger(l_db)
    witness = Witness(witness_key)
    reg_entry = ledger2.append("candidate_recorded", statement_dict)
    cp = ledger2.sign_checkpoint(ledger_key)
    cosig = witness.cosign_checkpoint(cp.checkpoint, consistency_proof=None)
    ledger2.add_witness_cosignature(cp.checkpoint.size, witness_key.key_id, cosig)
    inc_proof_raw = ledger2.inclusion_proof(reg_entry.index)
    signed_cp = ledger2.get_latest_checkpoint()
    assert signed_cp is not None

    candidate_proof = LedgerProof(
        event_type="candidate_recorded",
        entry_index=inc_proof_raw.entry_index,
        leaf_hash=inc_proof_raw.leaf_hash,
        inclusion_proof=inc_proof_raw.proof,
        checkpoint_size=inc_proof_raw.checkpoint_size,
        checkpoint_root_hash=inc_proof_raw.checkpoint_root_hash,
        checkpoint_signature=signed_cp.ledger_signature,
        witness_cosignatures=[cosig],
    )

    passport = build_candidate_passport(
        manifest_envelope=author_manifest_env,
        origin_envelope=origin_env,
        inspect_envelope=inspect_env,
        approve_envelope=approve_env,
        candidate_proof=candidate_proof,
        signed_checkpoint=signed_cp,
        min_epoch=1,
    )

    receiver_state = {"epoch": 1, "highest_sequence": {"BENCH-PASSPORT": 0}}

    # Warmup
    for _ in range(20):
        verify_passport(
            passport=passport,
            trust_ctx=trust_ctx,
            unit_id="canary-1",
            unit_role="canary",
            receiver_state=receiver_state,
            bundle_digest=build_res.package_digest,
        )

    verify_passport_times = []
    for _ in range(300):
        t0 = time.perf_counter()
        v_res = verify_passport(
            passport=passport,
            trust_ctx=trust_ctx,
            unit_id="canary-1",
            unit_role="canary",
            receiver_state=receiver_state,
            bundle_digest=build_res.package_digest,
        )
        verify_passport_times.append((time.perf_counter() - t0) * 1000)
        assert v_res.all_stamps_valid

    results["passport_verification"] = format_stats(
        verify_passport_times, "Full Offline Passport Verification (Candidate: 4 Stamps + Proofs)"
    )

    # 5. Benchmark: General Passport Verification (5 Stamps including Canary Test receipts)
    print("\n5. Measuring Full Offline General Passport Verification (5 Stamps)...")
    from receiver.receiver import ReceiverState
    with tempfile.TemporaryDirectory() as deploy_dir:
        rec_state = ReceiverState(unit_id="canary-1", unit_role="canary")
        rec = Receiver(
            state=rec_state,
            trust_ctx=trust_ctx,
            receiver_key=receiver_key,
            deploy_root=deploy_dir,
        )
        rec_ver, receipt_env = rec.verify_and_deploy(
            passport=passport,
            files=sample_files,
        )
        assert receipt_env is not None

    # Record promotion in ledger
    promo_entry = ledger2.append(
        "release_promoted", {"release_id": "BENCH-PASSPORT", "sequence": 1}
    )
    cp2 = ledger2.sign_checkpoint(ledger_key)
    promo_proof_raw = ledger2.inclusion_proof(promo_entry.index)
    promo_proof = LedgerProof(
        event_type="release_promoted",
        entry_index=promo_proof_raw.entry_index,
        leaf_hash=promo_proof_raw.leaf_hash,
        inclusion_proof=promo_proof_raw.proof,
        checkpoint_size=promo_proof_raw.checkpoint_size,
        checkpoint_root_hash=promo_proof_raw.checkpoint_root_hash,
        checkpoint_signature=cp2.ledger_signature,
        witness_cosignatures=[cosig],
    )

    gen_passport = build_general_passport(
        manifest_envelope=author_manifest_env,
        origin_envelope=origin_env,
        inspect_envelope=inspect_env,
        approve_envelope=approve_env,
        candidate_proof=candidate_proof,
        test_envelopes=[receipt_env],
        promotion_proof=promo_proof,
        signed_checkpoint=cp2,
        min_epoch=1,
    )

    gen_state = {"epoch": 1, "highest_sequence": {"BENCH-PASSPORT": 0}}
    # Warmup
    for _ in range(20):
        verify_passport(
            passport=gen_passport,
            trust_ctx=trust_ctx,
            unit_id="unit-general",
            unit_role="general",
            receiver_state=gen_state,
            bundle_digest=build_res.package_digest,
        )

    verify_gen_times = []
    for _ in range(300):
        t0 = time.perf_counter()
        vg_res = verify_passport(
            passport=gen_passport,
            trust_ctx=trust_ctx,
            unit_id="unit-general",
            unit_role="general",
            receiver_state=gen_state,
            bundle_digest=build_res.package_digest,
        )
        verify_gen_times.append((time.perf_counter() - t0) * 1000)
        assert vg_res.all_stamps_valid

    results["general_passport_verification"] = format_stats(
        verify_gen_times, "Full Offline General Passport Verification (All 5 Stamps + Proofs)"
    )
    ledger2.close()

    print("\n=================================================================")
    print("  ALL BENCHMARKS COMPLETE")
    print("=================================================================")
    return results


if __name__ == "__main__":
    run_benchmarks()
