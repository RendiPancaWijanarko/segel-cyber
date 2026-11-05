# SPDX-License-Identifier: MIT
"""Unit tests for the CLI entry points (segel-approver, segel-witness, segel-receiver)."""

import json
import pytest
from pathlib import Path
from unittest.mock import patch

from approver.cli import main as approver_main
from witness.cli import main as witness_main
from receiver.cli import main as receiver_main
from segel_core.crypto.ed25519 import generate_keypair
from cryptography.hazmat.primitives import serialization


def _dump_key_json(path: Path):
    kp = generate_keypair()
    raw_priv = kp.private_key.private_bytes(
        serialization.Encoding.Raw,
        serialization.PrivateFormat.Raw,
        serialization.NoEncryption(),
    )
    key_dict = {
        "key_id": kp.key_id,
        "private_key_hex": raw_priv.hex(),
        "public_key_b64": kp.key_id,
    }
    path.write_text(json.dumps(key_dict), encoding="utf-8")
    return kp


def test_approver_cli_help():
    with patch("sys.argv", ["segel-approver", "--help"]), pytest.raises(SystemExit) as exc:
        approver_main()
    assert exc.value.code == 0


def test_approver_cli_review(tmp_path):
    key_path = tmp_path / "approver_key.json"
    kp = _dump_key_json(key_path)

    qr_path = tmp_path / "qr_request.json"
    qr_data = {
        "type": "segel_approve_request",
        "release_id": "CLI-TEST-1",
        "seq": 1,
        "purpose": "CLI test",
        "manifest_sha256": "a" * 64,
        "origin_digest": "b" * 64,
        "inspect_digest": "c" * 64,
        "verdict": "PASS",
        "payload_b64": "e30=",  # base64("{}")
        "payload_type": "application/vnd.segel.approve+json",
    }
    qr_path.write_text(json.dumps(qr_data), encoding="utf-8")

    with patch("sys.argv", [
        "segel-approver", "review", str(qr_path),
        "--key", str(key_path),
        "--auto-approve",
    ]):
        approver_main()

    resp_file = qr_path.with_suffix(".response.json")
    assert resp_file.exists()
    resp_data = json.loads(resp_file.read_text(encoding="utf-8"))
    assert resp_data["approved"] is True
    assert resp_data["key_id"] == kp.key_id


def test_witness_cli_help():
    with patch("sys.argv", ["segel-witness", "--help"]), pytest.raises(SystemExit) as exc:
        witness_main()
    assert exc.value.code == 0


def test_witness_cli_cosign_and_status(tmp_path):
    key_path = tmp_path / "witness_key.json"
    kp = _dump_key_json(key_path)

    cp_path = tmp_path / "checkpoint.json"
    cp_data = {
        "origin": "segel-ledger-v1",
        "size": 1,
        "root_hash": "a" * 64,
    }
    cp_path.write_text(json.dumps(cp_data), encoding="utf-8")

    state_path = tmp_path / "witness_state.json"

    # Test cosign
    with patch("sys.argv", [
        "segel-witness", "cosign",
        "--key", str(key_path),
        "--checkpoint", str(cp_path),
        "--state-file", str(state_path),
    ]):
        witness_main()

    assert state_path.exists()
    state_data = json.loads(state_path.read_text(encoding="utf-8"))
    assert state_data["last_checkpoint_size"] == 1

    # Test status
    with patch("sys.argv", [
        "segel-witness", "status",
        "--state-file", str(state_path),
    ]):
        witness_main()


def test_receiver_cli_help():
    with patch("sys.argv", ["segel-receiver", "--help"]), pytest.raises(SystemExit) as exc:
        receiver_main()
    assert exc.value.code == 0


def test_receiver_cli_status(tmp_path):
    state_dir = tmp_path / "receiver_state"
    state_dir.mkdir()
    state_file = state_dir / "receiver_state.json"
    state_file.write_text(json.dumps({
        "unit_id": "test-unit",
        "unit_role": "general",
        "epoch": 2,
        "state_version": 5,
        "recovery_mode": False,
        "highest_sequence": {},
        "observed_checkpoints": {},
    }), encoding="utf-8")

    with patch("sys.argv", [
        "segel-receiver", "status",
        "--state-dir", str(state_dir),
    ]):
        receiver_main()

