"""
DSSE tests including the official DSSE test vector.

Per SEC-040: Tests MUST include the official DSSE vector.
"""

import base64
import json
import pytest

from segel_core.crypto.ed25519 import generate_keypair, PublicKeyInfo
from segel_core.crypto.dsse import (
    pae,
    create_envelope,
    add_signature,
    verify_envelope,
    verify_threshold,
    DSSEEnvelope,
    DSSESignature,
)
from segel_core.errors import SignatureError, ThresholdNotMetError, SchemaUnknownError


class TestPAE:
    """Test Pre-Authentication Encoding."""

    def test_pae_empty(self):
        """PAE with empty type and empty payload."""
        result = pae("", b"")
        expected = b"DSSEv1 0  0 "
        assert result == expected

    def test_pae_with_type(self):
        """PAE with a type and empty payload."""
        result = pae("application/json", b"")
        expected = b"DSSEv1 16 application/json 0 "
        assert result == expected

    def test_pae_with_payload(self):
        """PAE with type and payload."""
        result = pae("text/plain", b"hello")
        expected = b"DSSEv1 10 text/plain 5 hello"
        assert result == expected

    def test_pae_official_vector(self):
        """Official DSSE PAE test vector.
        
        From https://github.com/secure-systems-lab/dsse/blob/master/protocol.md
        
        PAE("http://example.com/HelloWorld", "hello world") should produce:
        "DSSEv1 29 http://example.com/HelloWorld 11 hello world"
        """
        result = pae("http://example.com/HelloWorld", b"hello world")
        expected = b"DSSEv1 29 http://example.com/HelloWorld 11 hello world"
        assert result == expected


class TestEnvelopeCreation:
    """Test DSSE envelope creation and serialization."""

    def test_create_single_signer(self):
        kp = generate_keypair()
        payload = b'{"test": true}'
        payload_type = "application/vnd.segel.manifest+json"

        envelope = create_envelope(
            payload_type=payload_type,
            payload=payload,
            signers=[(kp.key_id, kp.private_key)],
        )

        assert envelope.payload_type == payload_type
        assert len(envelope.signatures) == 1
        assert envelope.signatures[0].keyid == kp.key_id
        assert envelope.get_payload_bytes() == payload

    def test_create_multiple_signers(self):
        kps = [generate_keypair() for _ in range(3)]
        payload = b"multi-signer payload"
        payload_type = "application/vnd.segel.approve+json"

        envelope = create_envelope(
            payload_type=payload_type,
            payload=payload,
            signers=[(kp.key_id, kp.private_key) for kp in kps],
        )

        assert len(envelope.signatures) == 3

    def test_add_signature(self):
        kp1 = generate_keypair()
        kp2 = generate_keypair()
        payload = b"threshold payload"

        envelope = create_envelope(
            payload_type="test",
            payload=payload,
            signers=[(kp1.key_id, kp1.private_key)],
        )
        assert len(envelope.signatures) == 1

        envelope2 = add_signature(envelope, kp2.key_id, kp2.private_key)
        assert len(envelope2.signatures) == 2
        # Original unchanged
        assert len(envelope.signatures) == 1

    def test_serialization_roundtrip(self):
        kp = generate_keypair()
        payload = b'{"data": "value"}'

        envelope = create_envelope("test/type", payload, [(kp.key_id, kp.private_key)])

        # To dict and back
        d = envelope.to_dict()
        restored = DSSEEnvelope.from_dict(d)
        assert restored.payload_type == envelope.payload_type
        assert restored.payload == envelope.payload
        assert len(restored.signatures) == 1

        # To JSON and back
        j = envelope.to_json()
        restored2 = DSSEEnvelope.from_json(j)
        assert restored2.payload_type == envelope.payload_type

        # To bytes and back
        b = envelope.to_bytes()
        restored3 = DSSEEnvelope.from_bytes(b)
        assert restored3.get_payload_bytes() == payload


class TestEnvelopeVerification:
    """Test DSSE envelope verification."""

    def test_verify_valid_single_signature(self):
        kp = generate_keypair()
        payload = b"secure payload"
        key_info = PublicKeyInfo(
            public_key=kp.public_key,
            public_key_bytes=kp.public_key_bytes,
            key_id=kp.key_id,
            role="author",
        )

        envelope = create_envelope(
            "application/vnd.segel.manifest+json",
            payload,
            [(kp.key_id, kp.private_key)],
        )

        result = verify_envelope(
            envelope,
            [key_info],
            expected_payload_type="application/vnd.segel.manifest+json",
        )
        assert kp.key_id in result.valid_key_ids
        assert result.payload == payload
        assert result.invalid_count == 0

    def test_verify_ignores_keyid_hint(self):
        """SEC-007: Verification ignores keyid hints and tries all keys."""
        kp = generate_keypair()
        key_info = PublicKeyInfo(
            public_key=kp.public_key,
            public_key_bytes=kp.public_key_bytes,
            key_id=kp.key_id,
        )

        # Create envelope with a WRONG keyid hint
        envelope = create_envelope(
            "test",
            b"payload",
            [("WRONG_HINT", kp.private_key)],
        )

        result = verify_envelope(envelope, [key_info])
        # Should still verify because we try all keys, not just the hinted one
        assert kp.key_id in result.valid_key_ids

    def test_verify_rejects_wrong_payload_type(self):
        kp = generate_keypair()
        envelope = create_envelope("type/A", b"payload", [(kp.key_id, kp.private_key)])

        with pytest.raises(SignatureError, match="Payload type mismatch"):
            verify_envelope(
                envelope,
                [PublicKeyInfo(
                    public_key=kp.public_key,
                    public_key_bytes=kp.public_key_bytes,
                    key_id=kp.key_id,
                )],
                expected_payload_type="type/B",
            )

    def test_verify_counts_distinct_keys_only(self):
        """AT-006: Duplicate signatures from one key counted once."""
        kp = generate_keypair()
        key_info = PublicKeyInfo(
            public_key=kp.public_key,
            public_key_bytes=kp.public_key_bytes,
            key_id=kp.key_id,
        )

        envelope = create_envelope(
            "test",
            b"payload",
            [(kp.key_id, kp.private_key)],
        )
        # Add same signer again
        envelope = add_signature(envelope, kp.key_id, kp.private_key)
        assert len(envelope.signatures) == 2

        result = verify_envelope(envelope, [key_info])
        # Both signatures verify, but only ONE distinct key_id
        assert len(result.valid_key_ids) == 1
        assert result.invalid_count == 0

    def test_verify_unauthorised_key_not_counted(self):
        """AT-005: Signature from unauthorised key not counted."""
        kp_auth = generate_keypair()
        kp_unauth = generate_keypair()
        key_info_auth = PublicKeyInfo(
            public_key=kp_auth.public_key,
            public_key_bytes=kp_auth.public_key_bytes,
            key_id=kp_auth.key_id,
        )

        # Sign with unauthorised key
        envelope = create_envelope(
            "test",
            b"payload",
            [(kp_unauth.key_id, kp_unauth.private_key)],
        )

        result = verify_envelope(envelope, [key_info_auth])
        assert len(result.valid_key_ids) == 0
        assert result.invalid_count == 1

    def test_verify_rejects_non_canonical_base64_signature(self):
        """AT-031: Non-canonical base64 rejected."""
        kp = generate_keypair()
        key_info = PublicKeyInfo(
            public_key=kp.public_key,
            public_key_bytes=kp.public_key_bytes,
            key_id=kp.key_id,
        )

        envelope = create_envelope("test", b"payload", [(kp.key_id, kp.private_key)])
        # Tamper with the base64 encoding to make it non-canonical
        bad_sig = envelope.signatures[0].sig + "="  # Extra padding
        tampered = DSSEEnvelope(
            payload_type=envelope.payload_type,
            payload=envelope.payload,
            signatures=[DSSESignature(keyid=kp.key_id, sig=bad_sig)],
        )

        result = verify_envelope(tampered, [key_info])
        assert len(result.valid_key_ids) == 0
        assert result.invalid_count == 1

    def test_single_byte_mutation_breaks_verification(self):
        """AT-002: Modified payload detected."""
        kp = generate_keypair()
        key_info = PublicKeyInfo(
            public_key=kp.public_key,
            public_key_bytes=kp.public_key_bytes,
            key_id=kp.key_id,
        )

        payload = b"immutable payload data"
        envelope = create_envelope("test", payload, [(kp.key_id, kp.private_key)])

        # Tamper with the payload (modify one byte)
        raw = base64.b64decode(envelope.payload)
        mutated = bytearray(raw)
        mutated[0] ^= 0x01
        tampered_payload = base64.b64encode(bytes(mutated)).decode("ascii")

        tampered = DSSEEnvelope(
            payload_type=envelope.payload_type,
            payload=tampered_payload,
            signatures=envelope.signatures,
        )

        result = verify_envelope(tampered, [key_info])
        assert len(result.valid_key_ids) == 0


class TestThresholdVerification:
    """Test threshold and separation of duties."""

    def test_threshold_met(self):
        kps = [generate_keypair() for _ in range(3)]
        keys = [
            PublicKeyInfo(
                public_key=kp.public_key,
                public_key_bytes=kp.public_key_bytes,
                key_id=kp.key_id,
                role="approver",
            )
            for kp in kps
        ]

        envelope = create_envelope(
            "test",
            b"payload",
            [(kp.key_id, kp.private_key) for kp in kps[:2]],
        )

        result = verify_envelope(envelope, keys)
        counting = verify_threshold(result, threshold=2)
        assert len(counting) == 2

    def test_threshold_not_met(self):
        """AT-007: Threshold not met."""
        kp = generate_keypair()
        key_info = PublicKeyInfo(
            public_key=kp.public_key,
            public_key_bytes=kp.public_key_bytes,
            key_id=kp.key_id,
        )

        envelope = create_envelope("test", b"payload", [(kp.key_id, kp.private_key)])
        result = verify_envelope(envelope, [key_info])

        with pytest.raises(ThresholdNotMetError, match="1 of 2"):
            verify_threshold(result, threshold=2)

    def test_author_excluded_from_count(self):
        """AT-008: Author key used as approver is excluded."""
        author_kp = generate_keypair()
        approver_kp = generate_keypair()
        keys = [
            PublicKeyInfo(
                public_key=author_kp.public_key,
                public_key_bytes=author_kp.public_key_bytes,
                key_id=author_kp.key_id,
                role="approver",
            ),
            PublicKeyInfo(
                public_key=approver_kp.public_key,
                public_key_bytes=approver_kp.public_key_bytes,
                key_id=approver_kp.key_id,
                role="approver",
            ),
        ]

        envelope = create_envelope(
            "test",
            b"payload",
            [
                (author_kp.key_id, author_kp.private_key),
                (approver_kp.key_id, approver_kp.private_key),
            ],
        )

        result = verify_envelope(envelope, keys)
        assert len(result.valid_key_ids) == 2

        # With author excluded, only 1 counts
        counting = verify_threshold(
            result,
            threshold=1,
            excluded_key_ids={author_kp.key_id},
        )
        assert author_kp.key_id not in counting
        assert approver_kp.key_id in counting

        # Threshold 2 fails with author excluded
        with pytest.raises(ThresholdNotMetError):
            verify_threshold(
                result,
                threshold=2,
                excluded_key_ids={author_kp.key_id},
            )

    def test_duplicate_signer_counted_once_for_threshold(self):
        """AT-006 + AT-008: Duplicate key counted once."""
        kp = generate_keypair()
        key_info = PublicKeyInfo(
            public_key=kp.public_key,
            public_key_bytes=kp.public_key_bytes,
            key_id=kp.key_id,
        )

        envelope = create_envelope("test", b"payload", [(kp.key_id, kp.private_key)])
        envelope = add_signature(envelope, kp.key_id, kp.private_key)
        assert len(envelope.signatures) == 2

        result = verify_envelope(envelope, [key_info])
        assert len(result.valid_key_ids) == 1

        with pytest.raises(ThresholdNotMetError):
            verify_threshold(result, threshold=2)


class TestEnvelopeParsing:
    """Test malformed envelope handling."""

    def test_from_dict_missing_fields(self):
        with pytest.raises(SchemaUnknownError):
            DSSEEnvelope.from_dict({"payloadType": "test"})  # missing payload, signatures

    def test_from_json_invalid_json(self):
        with pytest.raises(SchemaUnknownError):
            DSSEEnvelope.from_json("not json")

    def test_from_dict_empty_signatures(self):
        envelope = DSSEEnvelope.from_dict({
            "payloadType": "test",
            "payload": base64.b64encode(b"data").decode(),
            "signatures": [],
        })
        assert len(envelope.signatures) == 0

