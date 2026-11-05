# SPDX-License-Identifier: MIT
"""Phase C Hardening Gap Tests: C1 — SEC-004 Key Separation.

Requirement: PRD SEC-004 & Decision D1:
- Release Desk MUST NOT possess, store, or generate approver private keys.
- Approver signing MUST be delegated to an external signer process.

Tests:
1. test_c1_sec004_positive_control_external_signer: Positive control verifying
   an external signer service can sign approval requests without Release Desk
   possessing the private keys.
2. test_c1_sec004_red_static_ast_release_desk_has_no_approver_private_keys:
   AST analysis of src/release_desk/ ensuring no generate_keypair or approver_keys
   are stored or called.
3. test_c1_sec004_red_runtime_release_desk_state_has_no_private_keys:
   Runtime inspection of Release Desk state ensuring no KeyPair or Ed25519PrivateKey
   objects are held for approvers.
"""

from __future__ import annotations

import ast
from pathlib import Path
from typing import Any

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from approver.approver import (
    ApprovalRequest,
    approver_sign,
    create_approval_payload,
)
from builder.builder import sign_origin
from inspector.inspector import create_inspect_attestation, inspect_release, sign_inspect
from segel_core.crypto.ed25519 import KeyPair, generate_keypair
from segel_core.schemas.manifest import Manifest, SubjectDigest


@pytest.mark.gap
def test_c1_sec004_positive_control_external_signer() -> None:
    """Positive control: External signer process can sign approval without Release Desk holding key."""
    from tests.adversarial.test_at_NNN import SyntheticLab, _build_valid_candidate

    lab = SyntheticLab()
    files, build, _, _ = _build_valid_candidate(lab, release_id="REL-SEC-004", sequence=1)
    origin_env = sign_origin(build, lab.builder_key)
    inspection = inspect_release(files, build.manifest, build.manifest_digest, ai_enabled=False)
    inspect_stmt = create_inspect_attestation(inspection, build.manifest, build.manifest_digest)
    inspect_env = sign_inspect(inspect_stmt, lab.inspector_key)

    _, approve_req = create_approval_payload(
        manifest=build.manifest,
        manifest_digest=build.manifest_digest,
        origin_envelope=origin_env,
        inspect_envelope=inspect_env,
        inspect_verdict="PASS",
    )

    # The external approver signer holds the approver key
    external_approver_key = generate_keypair()
    resp = approver_sign(approve_req, external_approver_key)

    assert resp.approved is True
    assert resp.approver_key_id == external_approver_key.key_id
    assert resp.signature_b64 is not None


@pytest.mark.gap
def test_c1_sec004_red_static_ast_release_desk_has_no_approver_private_keys() -> None:
    """RED TEST: AST analysis of src/release_desk/ proves Release Desk holds no approver private keys.

    Per SEC-004 & Decision D1, approver private keys MUST NOT be generated or stored
    inside the Release Desk process.
    """
    release_desk_dir = Path("src/release_desk")
    py_files = list(release_desk_dir.glob("*.py"))
    assert py_files, "Release desk source files must exist"

    violations: list[str] = []

    for py_file in py_files:
        tree = ast.parse(py_file.read_text(encoding="utf-8"), filename=str(py_file))
        for node in ast.walk(tree):
            # Check for approver_keys attribute assignments
            if isinstance(node, ast.Attribute) and node.attr == "approver_keys":
                violations.append(f"{py_file.name}:{node.lineno} references 'approver_keys'")
            # Check for direct calls to generate_keypair in release_desk for approvers
            if isinstance(node, ast.Call):
                func_name = ""
                if isinstance(node.func, ast.Name):
                    func_name = node.func.id
                elif isinstance(node.func, ast.Attribute):
                    func_name = node.func.attr
                if func_name == "generate_keypair":
                    violations.append(
                        f"{py_file.name}:{node.lineno} calls generate_keypair() inside Release Desk"
                    )

    assert not violations, (
        f"SEC-004 Violation: Release Desk contains approver private keys or generation logic:\n"
        + "\n".join(violations)
    )


@pytest.mark.gap
def test_c1_sec004_red_runtime_release_desk_state_has_no_private_keys() -> None:
    """RED TEST: Runtime inspection of Release Desk state proves no approver private keys are in memory.

    Per SEC-004, the running Release Desk application state MUST NOT hold KeyPair
    or Ed25519PrivateKey objects for approvers.
    """
    from release_desk.app import demo

    # Traverse demo state and ensure no approver private keys exist
    assert not hasattr(demo, "approver_keys") or demo.approver_keys is None, (
        "SEC-004 Violation: demo.approver_keys is stored in Release Desk process state!"
    )

    # Check that demo state does not contain any private key instances
    for attr_name in dir(demo):
        if attr_name.startswith("_"):
            continue
        val = getattr(demo, attr_name)
        if isinstance(val, (KeyPair, Ed25519PrivateKey)):
            pytest.fail(f"SEC-004 Violation: demo.{attr_name} holds a private key in Release Desk!")
        if isinstance(val, (list, tuple, set)):
            for item in val:
                if isinstance(item, (KeyPair, Ed25519PrivateKey)):
                    pytest.fail(
                        f"SEC-004 Violation: demo.{attr_name} contains private keys in Release Desk!"
                    )
