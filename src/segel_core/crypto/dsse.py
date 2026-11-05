"""
Dead Simple Signing Envelope (DSSE) implementation.

Reference: https://github.com/secure-systems-lab/dsse

DSSE signs exact payload bytes with a payload type, using the
Pre-Authentication Encoding (PAE) to prevent type confusion.

Per SEC-032: Sign the DSSE PAE of exact bytes. Do NOT canonicalise JSON.
Per SEC-007: Count distinct keys, ignore keyid hints, require strict base64.

PAE(payloadType, payload) =
    "DSSEv1" + SP + len(payloadType) + SP + payloadType + SP + len(payload) + SP + payload

where SP = 0x20 (space) and len() is the ASCII decimal byte count.
"""

import base64
import json
from dataclasses import dataclass, field
from typing import Any

from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
)

from segel_core.crypto.ed25519 import (
    PublicKeyInfo,
)
from segel_core.crypto.ed25519 import (
    sign as ed25519_sign,
)
from segel_core.crypto.ed25519 import (
    verify as ed25519_verify,
)
from segel_core.errors import (
    SchemaUnknownError,
    SignatureError,
    ThresholdNotMetError,
)


def pae(payload_type: str, payload: bytes) -> bytes:
    """Compute the DSSE Pre-Authentication Encoding.

    PAE(payloadType, payload) =
        "DSSEv1" SP len(payloadType) SP payloadType SP len(payload) SP payload

    Where SP = 0x20 and len() is ASCII decimal of the byte count.

    Args:
        payload_type: The payload type string (e.g., "application/vnd.segel.manifest+json").
        payload: The exact payload bytes to be signed.

    Returns:
        The PAE bytes to be signed.
    """
    payload_type_bytes = payload_type.encode("utf-8")
    parts = [
        b"DSSEv1",
        b" ",
        str(len(payload_type_bytes)).encode("ascii"),
        b" ",
        payload_type_bytes,
        b" ",
        str(len(payload)).encode("ascii"),
        b" ",
        payload,
    ]
    return b"".join(parts)


@dataclass(frozen=True)
class DSSESignature:
    """A single signature within a DSSE envelope.

    Attributes:
        keyid: Key identifier hint (not trusted for verification, SEC-007).
        sig: Base64-encoded 64-byte Ed25519 signature.
    """
    keyid: str
    sig: str  # Standard base64


@dataclass(frozen=True)
class DSSEEnvelope:
    """A DSSE envelope containing a payload and its signatures.

    Per the DSSE spec, the envelope contains:
    - payloadType: Media type of the payload
    - payload: Base64-encoded payload bytes
    - signatures: List of (keyid, sig) pairs

    Attributes:
        payload_type: The media type string.
        payload: Base64-encoded payload.
        signatures: List of DSSESignature objects.
    """
    payload_type: str
    payload: str  # Standard base64
    signatures: list[DSSESignature]

    def get_payload_bytes(self) -> bytes:
        """Decode and return the raw payload bytes.

        Raises:
            SignatureError: If the base64 is invalid or non-canonical.
        """
        try:
            raw = base64.b64decode(self.payload, validate=True)
        except Exception as e:
            raise SignatureError(
                f"Invalid base64 in DSSE payload: {e}",
            ) from e
        # Verify canonical base64
        canonical = base64.b64encode(raw).decode("ascii")
        if canonical != self.payload:
            raise SignatureError("Non-canonical base64 in DSSE payload")
        return raw

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a JSON-compatible dictionary."""
        return {
            "payloadType": self.payload_type,
            "payload": self.payload,
            "signatures": [
                {"keyid": s.keyid, "sig": s.sig}
                for s in self.signatures
            ],
        }

    def to_json(self) -> str:
        """Serialize to a JSON string (deterministic key order)."""
        return json.dumps(self.to_dict(), sort_keys=True, separators=(",", ":"))

    def to_bytes(self) -> bytes:
        """Serialize to JSON bytes."""
        return self.to_json().encode("utf-8")

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "DSSEEnvelope":
        """Deserialize from a dictionary.

        Raises:
            SchemaUnknownError: If required fields are missing.
        """
        try:
            payload_type = data["payloadType"]
            payload = data["payload"]
            signatures = [
                DSSESignature(keyid=s.get("keyid", ""), sig=s["sig"])
                for s in data["signatures"]
            ]
        except (KeyError, TypeError) as e:
            raise SchemaUnknownError(
                f"Invalid DSSE envelope structure: {e}",
                {"error": str(e)},
            ) from e
        return cls(
            payload_type=payload_type,
            payload=payload,
            signatures=signatures,
        )

    @classmethod
    def from_json(cls, json_str: str) -> "DSSEEnvelope":
        """Deserialize from a JSON string."""
        try:
            data = json.loads(json_str)
        except json.JSONDecodeError as e:
            raise SchemaUnknownError(
                f"Invalid JSON in DSSE envelope: {e}",
            ) from e
        return cls.from_dict(data)

    @classmethod
    def from_bytes(cls, data: bytes) -> "DSSEEnvelope":
        """Deserialize from JSON bytes."""
        return cls.from_json(data.decode("utf-8"))


def create_envelope(
    payload_type: str,
    payload: bytes,
    signers: list[tuple[str, Ed25519PrivateKey]],
) -> DSSEEnvelope:
    """Create a signed DSSE envelope.

    Per SEC-032: Signs the PAE of exact payload bytes. No JSON canonicalization.

    Args:
        payload_type: The media type for this payload.
        payload: The exact payload bytes. These are what gets signed.
        signers: List of (keyid_hint, private_key) pairs. Each will produce
                 one signature over the PAE.

    Returns:
        A DSSEEnvelope with all signatures.
    """
    pae_bytes = pae(payload_type, payload)
    payload_b64 = base64.b64encode(payload).decode("ascii")

    signatures = []
    for keyid_hint, private_key in signers:
        sig_bytes = ed25519_sign(private_key, pae_bytes)
        sig_b64 = base64.b64encode(sig_bytes).decode("ascii")
        signatures.append(DSSESignature(keyid=keyid_hint, sig=sig_b64))

    return DSSEEnvelope(
        payload_type=payload_type,
        payload=payload_b64,
        signatures=signatures,
    )


def add_signature(
    envelope: DSSEEnvelope,
    keyid_hint: str,
    private_key: Ed25519PrivateKey,
) -> DSSEEnvelope:
    """Add a signature to an existing DSSE envelope.

    Used for threshold approval: multiple approvers sign the same payload.

    Args:
        envelope: The existing envelope.
        keyid_hint: Hint for the new signer.
        private_key: The new signer's private key.

    Returns:
        A new DSSEEnvelope with the additional signature.
    """
    payload_bytes = envelope.get_payload_bytes()
    pae_bytes = pae(envelope.payload_type, payload_bytes)
    sig_bytes = ed25519_sign(private_key, pae_bytes)
    sig_b64 = base64.b64encode(sig_bytes).decode("ascii")

    new_sigs = list(envelope.signatures) + [
        DSSESignature(keyid=keyid_hint, sig=sig_b64)
    ]
    return DSSEEnvelope(
        payload_type=envelope.payload_type,
        payload=envelope.payload,
        signatures=new_sigs,
    )


@dataclass
class VerificationResult:
    """Result of verifying a DSSE envelope.

    Attributes:
        valid_key_ids: Set of key_ids (SHA-256 of public key) whose signatures verified.
        invalid_count: Number of signatures that failed verification.
        payload_type: The payload type from the envelope.
        payload: The decoded payload bytes.
    """
    valid_key_ids: set[str] = field(default_factory=set)
    invalid_count: int = 0
    payload_type: str = ""
    payload: bytes = b""


def verify_envelope(
    envelope: DSSEEnvelope,
    authorised_keys: list[PublicKeyInfo],
    expected_payload_type: str | None = None,
) -> VerificationResult:
    """Verify a DSSE envelope against a set of authorised public keys.

    Per SEC-007:
    - Uses authorised keys only
    - Ignores keyid hints (they are not trusted)
    - Counts distinct keys (duplicate sigs from one key counted once)
    - Requires strict base64 encoding
    - Checks the payload type if expected_payload_type is given

    Args:
        envelope: The DSSE envelope to verify.
        authorised_keys: List of public keys authorised for this operation.
        expected_payload_type: If set, the payload type must match exactly.

    Returns:
        VerificationResult with the set of valid key_ids.

    Raises:
        SignatureError: If base64 decoding fails or payload type mismatches.
    """
    # Check payload type
    if expected_payload_type is not None and envelope.payload_type != expected_payload_type:
        raise SignatureError(
            f"Payload type mismatch: expected '{expected_payload_type}', "
            f"got '{envelope.payload_type}'",
            {
                "expected": expected_payload_type,
                "actual": envelope.payload_type,
            },
        )

    # Decode payload with strict base64
    payload_bytes = envelope.get_payload_bytes()
    pae_bytes = pae(envelope.payload_type, payload_bytes)

    result = VerificationResult(
        payload_type=envelope.payload_type,
        payload=payload_bytes,
    )

    # Try every signature against every authorised key
    # Per SEC-007: ignore keyid, try all keys
    for sig_entry in envelope.signatures:
        # Strict base64 for signature
        try:
            sig_raw = base64.b64decode(sig_entry.sig, validate=True)
        except Exception:
            result.invalid_count += 1
            continue

        # Verify canonical base64
        canonical = base64.b64encode(sig_raw).decode("ascii")
        if canonical != sig_entry.sig:
            result.invalid_count += 1
            continue

        # Try against each authorised key
        sig_verified = False
        for key_info in authorised_keys:
            try:
                ed25519_verify(key_info.public_key, sig_raw, pae_bytes)
                # Success - record this distinct key_id
                result.valid_key_ids.add(key_info.key_id)
                sig_verified = True
                break  # Don't try more keys for this signature
            except SignatureError:
                continue

        if not sig_verified:
            result.invalid_count += 1

    return result


def verify_threshold(
    result: VerificationResult,
    threshold: int,
    excluded_key_ids: set[str] | None = None,
) -> set[str]:
    """Check that the verification result meets the required threshold.

    Per SEC-001: Author key MUST NOT count toward approval threshold.
    Per AT-006: Duplicate signatures from one key counted once.

    Args:
        result: The verification result from verify_envelope.
        threshold: Minimum number of distinct valid signers required.
        excluded_key_ids: Key IDs to exclude (e.g., the author's key).

    Returns:
        The set of valid, non-excluded key_ids that count.

    Raises:
        ThresholdNotMetError: If the threshold is not met.
    """
    excluded = excluded_key_ids or set()
    counting_keys = result.valid_key_ids - excluded

    if len(counting_keys) < threshold:
        raise ThresholdNotMetError(
            f"Approval threshold not met: {len(counting_keys)} of {threshold} required "
            f"distinct authorised signers verified",
            {
                "valid_count": len(counting_keys),
                "threshold": threshold,
                "excluded_count": len(result.valid_key_ids & excluded),
            },
        )

    return counting_keys

