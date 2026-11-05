# SPDX-License-Identifier: MIT
"""Phase B Mutation Testing Runner for SEGEL.

Executes each minimal mutation in an isolated, throw-away git worktree (.worktree_temp).
Verifies whether the target test fails (mutant killed) or passes (mutant survived),
records any collateral test failures across the adversarial suite,
and prints the final mutation table and score.
"""

from __future__ import annotations

import io
import os
import subprocess
import sys
from pathlib import Path

# Ensure UTF-8 output even on Windows consoles
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

MUTATIONS = [
    {
        "at_id": "AT-001",
        "file": "src/segel_core/crypto/dsse.py",
        "line": 329,
        "target": """            try:
                ed25519_verify(key_info.public_key, sig_raw, pae_bytes)
                # Success - record this distinct key_id
                result.valid_key_ids.add(key_info.key_id)
                sig_verified = True
                break  # Don't try more keys for this signature
            except SignatureError:
                continue""",
        "replacement": """            # MUTATION AT-001: accept all signatures unconditionally
            result.valid_key_ids.add(key_info.key_id)
            sig_verified = True
            break""",
        "test_name": "test_at_001_invalid_signature_on_envelope",
        "description": "Skip Ed25519 DSSE signature verification (accept all signatures)",
    },
    {
        "at_id": "AT-002",
        "file": "src/receiver/adapter/baseline.py",
        "line": 180,
        "target": "            if computed != subject.sha256:",
        "replacement": "            if False:  # MUTATION AT-002",
        "test_name": "test_at_002_manifest_or_bundle_modified_by_one_byte",
        "description": "Skip bundle file staging digest verification against manifest",
    },
    {
        "at_id": "AT-003",
        "file": "src/segel_core/verification/passport.py",
        "line": 228,
        "target": "        origin_env = DSSEEnvelope.from_dict(passport.origin_envelope)",
        "replacement": """        if not passport.origin_envelope:
            result.origin = StampResult("origin", StampStatus.VALID, "Bypassed")
            continue_origin = False
        else:
            continue_origin = True
            origin_env = DSSEEnvelope.from_dict(passport.origin_envelope)
        if not continue_origin:
            pass
        else:""",
        "test_name": "test_at_003_each_stamp_missing_in_turn",
        "description": "Treat missing origin envelope as valid in verify_passport",
    },
    {
        "at_id": "AT-004",
        "file": "src/segel_core/verification/passport.py",
        "line": 498,
        "target": "    if binding.subject.sequence != expected_subject.sequence:",
        "replacement": "    if False:  # MUTATION AT-004",
        "test_name": "test_at_004_approval_replayed_on_another_sequence",
        "description": "Skip sequence binding equality check in _check_binding",
    },
    {
        "at_id": "AT-007",
        "file": "src/segel_core/verification/passport.py",
        "line": 524,
        "target": "        if actual < minimum:",
        "replacement": "        if False:  # MUTATION AT-007",
        "test_name": "test_at_007_threshold_or_group_minimum_not_met",
        "description": "Skip approver group minimum quorum check in _check_group_minimums",
    },
    {
        "at_id": "AT-009",
        "file": "src/segel_core/verification/trust.py",
        "line": 244,
        "target": '    if receiver_epoch < required_min_epoch and freshness_mode == "strict":',
        "replacement": "    if False:  # MUTATION AT-009",
        "test_name": "test_at_009_receiver_epoch_lower_than_min_epoch_in_strict_mode",
        "description": "Skip receiver epoch floor check in check_min_epoch (strict mode)",
    },
    {
        "at_id": "AT-012",
        "file": "src/segel_core/verification/passport.py",
        "line": 553,
        "target": "    if manifest.sequence <= highest_seq:",
        "replacement": "    if False:  # MUTATION AT-012",
        "test_name": "test_at_012_release_sequence_not_higher_than_highest_accepted",
        "description": "Skip sequence anti-rollback check in _determine_eligibility",
    },
    {
        "at_id": "AT-013",
        "file": "src/segel_core/verification/passport.py",
        "line": 301,
        "target": "            if inspect_policy_ver < min_policy:",
        "replacement": "            if False:  # MUTATION AT-013",
        "test_name": "test_at_013_lower_policy_version_or_epoch_rejected",
        "description": "Skip minimum inspect policy version floor check in verify_passport",
    },
    {
        "at_id": "AT-014",
        "file": "src/receiver/receiver.py",
        "line": 131,
        "target": "        if self._state.recovery_mode:",
        "replacement": "        if False:  # MUTATION AT-014",
        "test_name": "test_at_014_corrupted_receiver_state_recovery_mode",
        "description": "Skip receiver recovery_mode fail-closed check",
    },
    {
        "at_id": "AT-015",
        "file": "src/inspector/inspector.py",
        "line": 87,
        "target": '        "severity": "reject",',
        "replacement": '        "severity": "pass",  # MUTATION AT-015',
        "test_name": "test_at_015_release_adds_forbidden_capability",
        "description": "Demote privilege_escalation policy rule from reject to pass",
    },
    {
        "at_id": "AT-020",
        "file": "src/witness/witness.py",
        "line": 77,
        "target": "            if checkpoint.root_hash != self._state.last_checkpoint_root_hash:",
        "replacement": "            if False:  # MUTATION AT-020",
        "test_name": "test_at_020_non_extending_or_conflicting_checkpoint_fork",
        "description": "Skip witness checkpoint root fork detection on same size",
    },
    {
        "at_id": "AT-021",
        "file": "src/segel_core/crypto/hashing.py",
        "line": 205,
        "target": "    if node != expected_root:",
        "replacement": "    if False:  # MUTATION AT-021",
        "test_name": "test_at_021_inclusion_proof_for_different_leaf_or_tree",
        "description": "Skip root comparison in verify_inclusion_from_hash",
    },
    {
        "at_id": "AT-023",
        "file": "src/segel_core/verification/passport.py",
        "line": 396,
        "target": "        if actual_witnesses < required_witnesses:",
        "replacement": "        if False:  # MUTATION AT-023",
        "test_name": "test_at_023_witness_cosignature_missing_where_policy_requires",
        "description": "Skip required witness cosignatures count check",
    },
    {
        "at_id": "AT-027",
        "file": "src/builder/builder.py",
        "line": 254,
        "target": "    if not path:",
        "replacement": "    return  # MUTATION AT-027: skip _validate_path",
        "test_name": "test_at_027_path_traversal_absolute_path_symlink_escape",
        "description": "Bypass path traversal, absolute path, and null-byte checks in builder",
    },
    {
        "at_id": "AT-028",
        "file": "src/builder/builder.py",
        "line": 105,
        "target": "        if total_size > MAX_TOTAL_SIZE:",
        "replacement": "        if False:  # MUTATION AT-028",
        "test_name": "test_at_028_decompression_bomb",
        "description": "Skip MAX_TOTAL_SIZE total package size check in builder",
    },
    {
        "at_id": "AT-031",
        "file": "src/segel_core/crypto/ed25519.py",
        "line": 292,
        "target": "    if canonical != b64_key:",
        "replacement": "    if False:  # MUTATION AT-031",
        "test_name": "test_at_031_non_canonical_base64_or_encoding_malleability",
        "description": "Skip canonical base64 strict equality check in import_public_key",
    },
    {
        "at_id": "AT-033",
        "file": "src/segel_core/verification/passport.py",
        "line": 589,
        "target": '            if unit_role == "canary":',
        "replacement": "            if True:  # MUTATION AT-033",
        "test_name": "test_at_033_candidate_passport_presented_to_non_canary_unit",
        "description": "Allow non-canary unit to accept candidate passport",
    },
    {
        "at_id": "AT-034",
        "file": "src/segel_core/verification/passport.py",
        "line": 423,
        "target": "            if passport.record_promotion_proof is None:",
        "replacement": "            if False:  # MUTATION AT-034",
        "test_name": "test_at_034_general_passport_without_promotion_record",
        "description": "Skip record_promotion_proof requirement for general passport",
    },
    {
        "at_id": "AT-035",
        "file": "src/segel_core/verification/passport.py",
        "line": 503,
        "target": "    if binding.subject.manifest_sha256 != expected_subject.manifest_sha256:",
        "replacement": "    if False:  # MUTATION AT-035",
        "test_name": "test_at_035_evidence_from_release_a_used_in_release_b",
        "description": "Skip manifest_sha256 subject binding verification",
    },
    {
        "at_id": "AT-040",
        "file": "src/segel_core/verification/passport.py",
        "line": 300,
        "target": "            min_policy = trust_ctx.policy.min_inspect_policy_version",
        "replacement": "            min_policy = 0  # MUTATION AT-040",
        "test_name": "test_at_040_inspect_policy_version_below_configured_minimum",
        "description": "Set min_inspect_policy_version floor to 0 (allow policy downgrade)",
    },
    {
        "at_id": "AT-041",
        "file": "src/segel_core/verification/passport.py",
        "line": 604,
        "target": "        if manifest.general_scope and unit_id not in manifest.general_scope:",
        "replacement": "        if False:  # MUTATION AT-041",
        "test_name": "test_at_041_release_scope_excludes_this_unit",
        "description": "Skip general_scope exclusion check in _determine_eligibility",
    },
    {
        "at_id": "AT-045",
        "file": "src/segel_core/verification/passport.py",
        "line": 546,
        "target": "    if trust_ctx.is_release_held(manifest.release_id, manifest.sequence):",
        "replacement": "    if False:  # MUTATION AT-045",
        "test_name": "test_at_045_hold_present_in_held_snapshot_refused_with_held",
        "description": "Skip held releases check in _determine_eligibility",
    },
]


def run_cmd(cmd: str, cwd: str | None = None, env: dict[str, str] | None = None) -> tuple[int, str]:
    full_env = os.environ.copy()
    if env:
        full_env.update(env)
    proc = subprocess.run(
        cmd,
        cwd=cwd,
        env=full_env,
        shell=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    return proc.returncode, proc.stdout + proc.stderr


def main() -> None:
    worktree_rel = ".worktree_temp"
    worktree_path = Path(worktree_rel).resolve()
    pytest_bin = Path(r".venv\Scripts\pytest.exe").resolve()

    print(f"Starting Phase B Mutation Testing across {len(MUTATIONS)} sound tests...")
    print("=" * 80)

    results = []

    for idx, m in enumerate(MUTATIONS, start=1):
        at_id = m["at_id"]
        rel_file = m["file"]
        line = m["line"]
        target = m["target"]
        replacement = m["replacement"]
        test_name = m["test_name"]
        desc = m["description"]

        print(f"\n[{idx}/{len(MUTATIONS)}] Mutating {at_id} ({rel_file}:{line})...", flush=True)
        print(f"  Target: {desc}", flush=True)

        # 1. Clean any existing worktree
        if Path(worktree_rel).exists():
            run_cmd(f"git worktree remove --force {worktree_rel}")

        # 2. Add detached worktree
        rc, out = run_cmd(f"git worktree add --detach {worktree_rel} hardening/p2b-p5")
        if rc != 0:
            print(f"  ERROR creating worktree: {out}")
            continue

        try:
            target_file = worktree_path / rel_file
            content = target_file.read_text(encoding="utf-8")
            if target not in content:
                print(f"  ERROR: target string not found in {rel_file}:{line}")
                results.append({
                    "at_id": at_id,
                    "mutation": f"{rel_file}:{line}",
                    "killed": False,
                    "other_failures": ["TARGET_NOT_FOUND"],
                    "desc": desc,
                })
                continue

            # Apply mutation in worktree only
            mutated_content = content.replace(target, replacement, 1)
            target_file.write_text(mutated_content, encoding="utf-8")

            # Run target test in worktree with worktree isolation
            worktree_env = {
                "PYTHONPATH": f"{worktree_path / 'src'}{os.pathsep}{worktree_path}"
            }
            target_test_cmd = f'"{pytest_bin}" "{worktree_path}/tests/adversarial/test_at_NNN.py" -k {test_name} -q --tb=no'
            rc_target, out_target = run_cmd(target_test_cmd, cwd=str(worktree_path), env=worktree_env)
            target_failed = (rc_target != 0)

            # Run full AT suite in worktree to detect other failures
            full_test_cmd = f'"{pytest_bin}" "{worktree_path}/tests/adversarial/test_at_NNN.py" -q --tb=no'
            rc_full, out_full = run_cmd(full_test_cmd, cwd=str(worktree_path), env=worktree_env)

            # Parse failed tests from full run
            other_fails = []
            for line_out in out_full.splitlines():
                if line_out.startswith("FAILED") and "::" in line_out:
                    failed_fn = line_out.split("::")[-1].split()[0]
                    if failed_fn != test_name:
                        other_fails.append(failed_fn)

            # Remove known pre-existing defects from other_fails (AT-010, AT-024, AT-029, AT-039)
            known_baseline_fails = {
                "test_at_010_revoked_key_index_ordering",
                "test_at_024_canary_unhealthy_or_criteria_unmet",
                "test_at_029_two_concurrent_deployments_on_one_target",
                "test_at_039_adapter_missing_from_pinned_allowlist",
            }
            collateral_failures = [f for f in other_fails if f not in known_baseline_fails]

            status_str = "KILLED (Test Failed as Expected)" if target_failed else "SURVIVED (Test Passed despite Mutation!)"
            print(f"  Result: {status_str}", flush=True)
            if collateral_failures:
                print(f"  Collateral test failures: {', '.join(collateral_failures)}", flush=True)

            results.append({
                "at_id": at_id,
                "mutation": f"{rel_file}:{line}",
                "killed": target_failed,
                "other_failures": collateral_failures,
                "desc": desc,
            })

        finally:
            # 3. Discard throw-away worktree
            run_cmd(f"git worktree remove --force {worktree_rel}")

    # Print summary table and mutation score
    print("\n" + "=" * 80)
    print("PHASE B MUTATION TESTING RESULTS")
    print("=" * 80)
    print(f"{'AT ID':<8} | {'Mutation (File:Line)':<42} | {'Killed?':<8} | {'Collateral Failures':<25}")
    print("-" * 90)

    killed_count = 0
    for r in results:
        killed_text = "YES" if r["killed"] else "NO"
        if r["killed"]:
            killed_count += 1
        collateral_text = ", ".join(r["other_failures"]) if r["other_failures"] else "None"
        print(f"{r['at_id']:<8} | {r['mutation']:<42} | {killed_text:<8} | {collateral_text:<25}")

    total = len(results)
    score = (killed_count / total * 100) if total > 0 else 0.0

    print("-" * 90)
    print(f"Total Mutants Tested: {total}")
    print(f"Mutants Killed:       {killed_count}")
    print(f"Mutants Survived:     {total - killed_count}")
    print(f"Mutation Score:       {score:.2f}%")
    print("=" * 80)


if __name__ == "__main__":
    main()
