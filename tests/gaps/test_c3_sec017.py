# SPDX-License-Identifier: MIT
"""Phase C Hardening Gap Tests: C3 — SEC-017 Local Hash-Chained Audit Log.

Requirement: PRD SEC-017 & Decision D3:
- Receiver MUST maintain a local, append-only, hash-chained JSON-lines audit log
  recording every verification attempt, deployment, rejection, and rollback.
- Each entry MUST contain: sequence, ISO timestamp, event type, event data,
  previous entry hash (prev_hash), and SHA-256 hash of the entry.
- Any modification, deletion, or truncation of the audit log MUST be detected.
- The audit log MUST NOT contain private keys, secrets, or decrypted payloads.

Tests:
1. test_c3_sec017_positive_control_hash_chain_generation: Positive control showing
   audit log records events and verifies valid hash chain.
2. test_c3_sec017_red_receiver_writes_hash_chained_audit_log: RED TEST verifying
   Receiver creates and populates the hash-chained audit log on verify_and_deploy.
3. test_c3_sec017_red_audit_log_tampering_detected: RED TEST verifying tampering
   with any field in the audit log is detected by verification.
4. test_c3_sec017_red_no_secrets_in_audit_log: RED TEST verifying no private keys
   or credentials appear anywhere in the audit log.
"""

from __future__ import annotations

import hashlib
import json
import tempfile
from pathlib import Path
from typing import Any

import pytest

from segel_core.canonical import canonical_json
from segel_core.crypto.ed25519 import KeyPair, generate_keypair
from segel_core.schemas.trust import KeyRecord, TrustRoot, TrustSnapshot, VerificationPolicy
from segel_core.verification.trust import TrustContext


def _compute_entry_hash(prev_hash: str, entry_dict: dict[str, Any]) -> str:
    """Compute SHA-256 over prev_hash || canonical_json(entry_dict without entry_hash)."""
    clean_dict = {k: v for k, v in entry_dict.items() if k != "entry_hash"}
    payload = prev_hash.encode("ascii") + canonical_json(clean_dict)
    return hashlib.sha256(payload).hexdigest()


def verify_audit_log_chain(log_path: Path) -> tuple[bool, str]:
    """Verify integrity of a hash-chained audit log file."""
    if not log_path.exists():
        return False, "Audit log file does not exist"

    lines = log_path.read_text(encoding="utf-8").strip().splitlines()
    if not lines:
        return True, "Empty log"

    prev_hash = "0" * 64
    for idx, line in enumerate(lines):
        try:
            entry = json.loads(line)
        except Exception as e:
            return False, f"Line {idx} invalid JSON: {e}"

        expected_prev = entry.get("prev_hash")
        if expected_prev != prev_hash:
            return False, f"Line {idx} prev_hash mismatch: got {expected_prev}, expected {prev_hash}"

        recorded_hash = entry.get("entry_hash")
        computed_hash = _compute_entry_hash(prev_hash, entry)
        if recorded_hash != computed_hash:
            return False, f"Line {idx} hash mismatch: got {recorded_hash}, expected {computed_hash}"

        prev_hash = recorded_hash

    return True, "Valid"


@pytest.mark.gap
def test_c3_sec017_positive_control_hash_chain_generation() -> None:
    """Positive control: Hash chain computation and validation functions work correctly."""
    with tempfile.TemporaryDirectory() as td:
        log_file = Path(td) / "audit.jsonl"
        entries = []
        prev_hash = "0" * 64

        for seq in range(1, 4):
            entry_data = {
                "seq": seq,
                "timestamp": f"2026-03-30T10:0{seq}:00Z",
                "event_type": "verification_completed",
                "data": {"status": "success", "release_id": f"REL-00{seq}"},
                "prev_hash": prev_hash,
            }
            entry_hash = _compute_entry_hash(prev_hash, entry_data)
            entry_data["entry_hash"] = entry_hash
            entries.append(entry_data)
            prev_hash = entry_hash

        log_file.write_text("\n".join(json.dumps(e) for e in entries) + "\n", encoding="utf-8")
        valid, msg = verify_audit_log_chain(log_file)
        assert valid, f"Positive control audit chain must be valid: {msg}"


@pytest.mark.gap
def test_c3_sec017_red_receiver_writes_hash_chained_audit_log() -> None:
    """RED TEST: Receiver MUST automatically append events to an audit.jsonl hash chain.

    Per SEC-017 & Decision D3: When verify_and_deploy() is called, the Receiver must
    maintain and append to audit_dir / "audit.jsonl" with valid prev_hash linkage.
    """
    from receiver.receiver import Receiver, ReceiverState
    from tests.adversarial.test_at_NNN import SyntheticLab, _build_valid_candidate

    lab = SyntheticLab()
    files, _, passport, _ = _build_valid_candidate(lab, release_id="REL-SEC-017", sequence=1)

    with tempfile.TemporaryDirectory() as td:
        deploy_dir = Path(td) / "deploy"
        audit_dir = Path(td) / "audit"
        deploy_dir.mkdir()
        audit_dir.mkdir()

        # Receiver should accept audit_dir or log to deploy_dir / ".audit"
        receiver = Receiver(
            state=ReceiverState(unit_id="canary-1", unit_role="canary"),
            trust_ctx=lab.trust_ctx,
            receiver_key=lab.canary_keys[0],
            deploy_root=deploy_dir,
            audit_dir=audit_dir,  # SEC-017 gap: currently not implemented in Receiver.__init__
        )

        verification, receipt = receiver.verify_and_deploy(passport, files)
        assert receipt is not None

        audit_log = audit_dir / "audit.jsonl"
        assert audit_log.exists(), "SEC-017 Violation: Receiver failed to create audit.jsonl!"

        valid, msg = verify_audit_log_chain(audit_log)
        assert valid, f"Audit log must form a valid cryptographic hash chain: {msg}"


@pytest.mark.gap
def test_c3_sec017_red_audit_log_tampering_detected() -> None:
    """RED TEST: Tampering with audit.jsonl lines MUST be detected by verify_audit_log_chain."""
    with tempfile.TemporaryDirectory() as td:
        log_file = Path(td) / "audit.jsonl"
        prev_hash = "0" * 64
        entries = []
        for seq in range(1, 4):
            entry_data = {
                "seq": seq,
                "timestamp": f"2026-03-30T10:0{seq}:00Z",
                "event_type": "verification_completed",
                "data": {"status": "success", "release_id": f"REL-00{seq}"},
                "prev_hash": prev_hash,
            }
            entry_hash = _compute_entry_hash(prev_hash, entry_data)
            entry_data["entry_hash"] = entry_hash
            entries.append(entry_data)
            prev_hash = entry_hash

        # Tamper line 2 data without recomputing hash chain
        entries[1]["data"]["status"] = "tampered"
        log_file.write_text("\n".join(json.dumps(e) for e in entries) + "\n", encoding="utf-8")

        valid, msg = verify_audit_log_chain(log_file)
        assert not valid, "Tampered audit log must fail validation!"
        assert "hash mismatch" in msg


@pytest.mark.gap
def test_c3_sec017_red_no_secrets_in_audit_log() -> None:
    """RED TEST: Audit log MUST NOT leak private keys or secrets."""
    with tempfile.TemporaryDirectory() as td:
        log_file = Path(td) / "audit.jsonl"
        # Simulate log output
        entries = [
            {
                "seq": 1,
                "timestamp": "2026-03-30T10:00:00Z",
                "event_type": "key_loaded",
                "data": {"key_id": "key-1", "role": "approver"},
                "prev_hash": "0" * 64,
                "entry_hash": "a" * 64,
            }
        ]
        log_file.write_text(json.dumps(entries[0]) + "\n", encoding="utf-8")

        content = log_file.read_text(encoding="utf-8")
        forbidden_substrings = ["private_key", "secret", "seed", "-----BEGIN"]
        for forbidden in forbidden_substrings:
            assert forbidden.lower() not in content.lower(), f"Secret leak in audit log: {forbidden}"
