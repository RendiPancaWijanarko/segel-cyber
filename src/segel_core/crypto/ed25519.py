"""
Ed25519 key management and signing operations.

Uses the `cryptography` library (SEC-030: vetted library, never implement primitives).
Key identity is SHA-256 of the raw 32-byte public key (SEC-033).
Keys come from the OS CSPRNG (SEC-037).
"""

import base64
import hashlib
import os
from dataclasses import dataclass

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)

from segel_core.errors import SignatureError


def _compute_key_id(public_key_bytes: bytes) -> str:
    """Compute key identity as hex-encoded SHA-256 of the raw 32-byte public key.

    Per SEC-033: Key identity is the SHA-256 of the raw public key.
    The envelope keyid is a hint only.
    """
    return hashlib.sha256(public_key_bytes).hexdigest()


@dataclass(frozen=True)
class KeyPair:
    """An Ed25519 key pair with its computed identity.

    Attributes:
        private_key: The Ed25519 private key object.
        public_key: The Ed25519 public key object.
        public_key_bytes: Raw 32-byte public key.
        key_id: SHA-256 hex digest of the raw public key bytes.
    """
    private_key: Ed25519PrivateKey
    public_key: Ed25519PublicKey
    public_key_bytes: bytes
    key_id: str


@dataclass(frozen=True)
class PublicKeyInfo:
    """Public key information without the private key.

    Attributes:
        public_key: The Ed25519 public key object.
        public_key_bytes: Raw 32-byte public key.
        key_id: SHA-256 hex digest of the raw public key bytes.
        role: The role this key is authorised for (e.g., 'author', 'approver').
        algorithm: Algorithm identifier (always 'ed25519' for now).
    """
    public_key: Ed25519PublicKey
    public_key_bytes: bytes
    key_id: str
    role: str = ""
    algorithm: str = "ed25519"


def generate_keypair() -> KeyPair:
    """Generate a new Ed25519 key pair using the OS CSPRNG (SEC-037).

    Returns:
        A KeyPair with the private key, public key, raw bytes, and computed key_id.
    """
    private_key = Ed25519PrivateKey.generate()
    public_key = private_key.public_key()
    public_key_bytes = public_key.public_bytes(
        serialization.Encoding.Raw,
        serialization.PublicFormat.Raw,
    )
    key_id = _compute_key_id(public_key_bytes)
    return KeyPair(
        private_key=private_key,
        public_key=public_key,
        public_key_bytes=public_key_bytes,
        key_id=key_id,
    )


def public_key_from_bytes(raw_bytes: bytes) -> PublicKeyInfo:
    """Load a public key from raw 32-byte Ed25519 public key bytes.

    Args:
        raw_bytes: Exactly 32 bytes of Ed25519 public key.

    Returns:
        PublicKeyInfo with the loaded key and computed identity.

    Raises:
        SignatureError: If the bytes are not a valid Ed25519 public key.
    """
    if len(raw_bytes) != 32:
        raise SignatureError(
            f"Ed25519 public key must be exactly 32 bytes, got {len(raw_bytes)}",
            {"length": len(raw_bytes)},
        )
    try:
        public_key = Ed25519PublicKey.from_public_bytes(raw_bytes)
    except Exception as e:
        raise SignatureError(
            f"Invalid Ed25519 public key bytes: {e}",
            {"error": str(e)},
        ) from e
    key_id = _compute_key_id(raw_bytes)
    return PublicKeyInfo(
        public_key=public_key,
        public_key_bytes=raw_bytes,
        key_id=key_id,
    )


def sign(private_key: Ed25519PrivateKey, data: bytes) -> bytes:
    """Sign data with an Ed25519 private key.

    Args:
        private_key: The signing key.
        data: The exact bytes to sign.

    Returns:
        64-byte Ed25519 signature.
    """
    return private_key.sign(data)


def verify(public_key: Ed25519PublicKey, signature: bytes, data: bytes) -> None:
    """Verify an Ed25519 signature.

    Args:
        public_key: The verification key.
        signature: 64-byte signature.
        data: The exact bytes that were signed.

    Raises:
        SignatureError: If the signature is invalid.
    """
    if len(signature) != 64:
        raise SignatureError(
            f"Ed25519 signature must be exactly 64 bytes, got {len(signature)}",
            {"length": len(signature)},
        )
    try:
        public_key.verify(signature, data)
    except InvalidSignature as e:
        raise SignatureError(
            "Ed25519 signature verification failed",
            {"error": str(e)},
        ) from e


def export_private_key_encrypted(
    private_key: Ed25519PrivateKey,
    passphrase: bytes,
) -> bytes:
    """Export a private key encrypted with a passphrase using scrypt KDF.

    Per SEC-016: Private keys MUST be encrypted at rest.
    Per SEC-038: Use memory-hard KDF.

    Args:
        private_key: The key to export.
        passphrase: The encryption passphrase.

    Returns:
        PEM-encoded encrypted private key bytes.
    """
    return private_key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.BestAvailableEncryption(passphrase),
    )


def import_private_key_encrypted(
    data: bytes,
    passphrase: bytes,
) -> KeyPair:
    """Import a private key from encrypted PEM.

    Args:
        data: PEM-encoded encrypted private key.
        passphrase: The decryption passphrase.

    Returns:
        A KeyPair.

    Raises:
        SignatureError: If decryption or parsing fails.
    """
    try:
        private_key = serialization.load_pem_private_key(data, passphrase)
        if not isinstance(private_key, Ed25519PrivateKey):
            raise SignatureError(
                "Key is not Ed25519",
                {"type": type(private_key).__name__},
            )
        public_key = private_key.public_key()
        public_key_bytes = public_key.public_bytes(
            serialization.Encoding.Raw,
            serialization.PublicFormat.Raw,
        )
        return KeyPair(
            private_key=private_key,
            public_key=public_key,
            public_key_bytes=public_key_bytes,
            key_id=_compute_key_id(public_key_bytes),
        )
    except SignatureError:
        raise
    except Exception as e:
        raise SignatureError(
            f"Failed to import private key: {e}",
            {"error": str(e)},
        ) from e


def import_private_key(raw_bytes: bytes) -> KeyPair:
    """Import an unencrypted private key from raw 32-byte seed.

    Note: In production, use import_private_key_encrypted (SEC-016).
    This function is provided for CLI and dev/demo tooling.
    """
    if len(raw_bytes) != 32:
        raise SignatureError(
            f"Ed25519 private key seed must be exactly 32 bytes, got {len(raw_bytes)}",
            {"length": len(raw_bytes)},
        )
    try:
        private_key = Ed25519PrivateKey.from_private_bytes(raw_bytes)
        public_key = private_key.public_key()
        public_key_bytes = public_key.public_bytes(
            serialization.Encoding.Raw,
            serialization.PublicFormat.Raw,
        )
        return KeyPair(
            private_key=private_key,
            public_key=public_key,
            public_key_bytes=public_key_bytes,
            key_id=_compute_key_id(public_key_bytes),
        )
    except Exception as e:
        raise SignatureError(
            f"Failed to import private key from bytes: {e}",
            {"error": str(e)},
        ) from e


def export_public_key(public_key_bytes: bytes) -> str:
    """Export a public key as base64-encoded raw bytes.

    Args:
        public_key_bytes: Raw 32-byte Ed25519 public key.

    Returns:
        Standard base64 encoding of the raw public key.
    """
    return base64.b64encode(public_key_bytes).decode("ascii")


def import_public_key(b64_key: str) -> PublicKeyInfo:
    """Import a public key from base64-encoded raw bytes.

    Per SEC-007: Require strict base64 encoding.

    Args:
        b64_key: Standard base64-encoded 32-byte public key.

    Returns:
        PublicKeyInfo.

    Raises:
        SignatureError: If decoding or parsing fails.
    """
    # Strict base64: reject non-canonical encodings (AT-031)
    try:
        raw = base64.b64decode(b64_key, validate=True)
    except Exception as e:
        raise SignatureError(
            f"Non-canonical or invalid base64 encoding: {e}",
            {"error": str(e), "input_length": len(b64_key)},
        ) from e

    # Re-encode to check canonical form
    canonical = base64.b64encode(raw).decode("ascii")
    if canonical != b64_key:
        raise SignatureError(
            "Non-canonical base64 encoding rejected",
            {"given": b64_key, "canonical": canonical},
        )

    return public_key_from_bytes(raw)


def generate_evidence_id() -> str:
    """Generate a random 128-bit evidence ID using the OS CSPRNG (SEC-037).

    Returns:
        Hex-encoded 128-bit random identifier.
    """
    return os.urandom(16).hex()

