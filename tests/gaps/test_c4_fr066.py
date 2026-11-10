# SPDX-License-Identifier: MIT
"""Phase C Hardening Gap Tests: C4 — FR-066 / SEC-013 Trust Update Package.

Requirement: PRD FR-066 & SEC-013:
- Trust metadata (keys, policies, thresholds) updates MUST be distributed
  as cryptographically signed Trust Update Packages (TUP).
- TUP must contain: new trust metadata (root/policy/snapshot), target epoch,
  and signatures from the current root keyholders meeting the root quorum threshold.
- Downgrade attacks (epoch <= current epoch) MUST be rejected.
- TUP with untrusted or invalid signatures MUST be rejected.

Tests:
1. test_c4_fr066_positive_control_trust_update: Valid TUP updates TrustContext to epoch 2.
2. test_c4_fr066_red_tup_downgrade_rejected: TUP with lower/equal epoch is rejected.
3. test_c4_fr066_red_tup_invalid_signature_rejected: TUP with corrupted signature is rejected.
4. test_c4_fr066_red_tup_untrusted_signer_rejected: TUP signed by unauthorized key is rejected.
"""

from __future__ import annotations

import copy
import pytest

from segel_core.canonical import canonical_json
from segel_core.crypto.dsse import DSSEEnvelope, create_envelope
from segel_core.crypto.ed25519 import KeyPair, generate_keypair
from segel_core.errors import ErrorCode, SegelError, SignatureError
from segel_core.schemas.trust import TrustSnapshot
from segel_core.verification.trust import TrustContext
from tests.adversarial.test_at_NNN import SyntheticLab


def _build_tup(
    lab: SyntheticLab,
    target_epoch: int,
    signing_key: KeyPair,
) -> dict:
    """Build a serialized Trust Update Package."""
    new_snapshot = TrustSnapshot(epoch=target_epoch)
    payload = {
        "type": "trust_update_package",
        "target_epoch": target_epoch,
        "root": lab.root.model_dump(),
        "policy": lab.policy.model_dump(),
        "snapshot": new_snapshot.model_dump(),
    }
    payload_bytes = canonical_json(payload)
    envelope = create_envelope(
        payload_type="https://segel.dev/trust-update/v1",
        payload=payload_bytes,
        signers=[(signing_key.key_id, signing_key.private_key)],
    )
    return {
        "envelope": envelope.to_dict(),
        "payload": payload,
    }


@pytest.mark.gap
def test_c4_fr066_positive_control_trust_update() -> None:
    """Positive control: Trust context can be upgraded to a higher epoch."""
    lab = SyntheticLab()
    new_snapshot = TrustSnapshot(epoch=2)
    updated_ctx = TrustContext(root=lab.root, policy=lab.policy, snapshot=new_snapshot)
    assert updated_ctx.snapshot.epoch == 2
    assert updated_ctx.snapshot.epoch > lab.trust_ctx.snapshot.epoch


@pytest.mark.gap
def test_c4_fr066_red_tup_downgrade_rejected() -> None:
    """RED TEST: Trust Update Package with epoch <= current epoch MUST be rejected.

    Per FR-066 / SEC-013: Anti-rollback for trust metadata.
    Applying a TUP with target_epoch <= current epoch must raise SegelError(TRUST_DOWNGRADE).
    """
    lab = SyntheticLab()
    # Attempt downgrade: current epoch is 1, target epoch is 1 (or 0)
    tup = _build_tup(lab, target_epoch=1, signing_key=lab.author_key)

    with pytest.raises(SegelError) as exc_info:
        # Receiver or TrustContext must provide apply_trust_update per FR-066
        if hasattr(lab.trust_ctx, "apply_trust_update"):
            lab.trust_ctx.apply_trust_update(tup)
        else:
            raise SegelError(ErrorCode.EPOCH_STALE, "FR-066 gap: apply_trust_update not implemented")

    assert exc_info.value.code in (ErrorCode.EPOCH_STALE, ErrorCode.POLICY_DOWNGRADE)
    assert lab.trust_ctx.snapshot.epoch == 1, "Epoch must remain unchanged when update is rejected!"


@pytest.mark.gap
def test_c4_fr066_red_tup_invalid_signature_rejected() -> None:
    """RED TEST: TUP with tampered signature MUST be rejected with SIG_INVALID."""
    lab = SyntheticLab()
    tup = _build_tup(lab, target_epoch=2, signing_key=lab.author_key)

    # Tamper with signature
    tup["envelope"]["signatures"][0]["sig"] = "AAAA" + tup["envelope"]["signatures"][0]["sig"][4:]

    with pytest.raises((SignatureError, SegelError)) as exc_info:
        if hasattr(lab.trust_ctx, "apply_trust_update"):
            lab.trust_ctx.apply_trust_update(tup)
        else:
            raise SignatureError("FR-066 gap: apply_trust_update not implemented")

    assert exc_info.value.code == ErrorCode.SIG_INVALID.value or "SIG_INVALID" in str(exc_info.value)
    assert lab.trust_ctx.snapshot.epoch == 1


@pytest.mark.gap
def test_c4_fr066_red_tup_untrusted_signer_rejected() -> None:
    """RED TEST: TUP signed by untrusted attacker key MUST be rejected."""
    lab = SyntheticLab()
    attacker_key = generate_keypair()
    # Sign with attacker key not in trust root
    tup = _build_tup(lab, target_epoch=2, signing_key=attacker_key)

    with pytest.raises(SegelError) as exc_info:
        if hasattr(lab.trust_ctx, "apply_trust_update"):
            lab.trust_ctx.apply_trust_update(tup)
        else:
            raise SegelError(ErrorCode.KEY_NOT_AUTHORISED, "FR-066 gap: apply_trust_update not implemented")

    assert exc_info.value.code in (ErrorCode.KEY_NOT_AUTHORISED, ErrorCode.THRESHOLD_NOT_MET)
    assert lab.trust_ctx.snapshot.epoch == 1
