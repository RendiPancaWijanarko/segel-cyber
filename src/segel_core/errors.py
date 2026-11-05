"""
SEGEL Core Error Types and Stable Error Codes.

Every verification failure produces a typed error with a stable code
that tests and users can rely on. Error codes follow Appendix E of PRD v2.0.

All errors are fail-closed: an error means the release is ineligible
and the reason is always explained.
"""

from enum import StrEnum
from typing import Any


class ErrorCode(StrEnum):
    """Stable error codes per PRD v2.0 Appendix E.

    These codes are part of the public interface and MUST NOT change
    without a schema version bump.
    """
    SIG_INVALID = "SIG_INVALID"
    DIGEST_MISMATCH = "DIGEST_MISMATCH"
    STAMP_MISSING = "STAMP_MISSING"
    THRESHOLD_NOT_MET = "THRESHOLD_NOT_MET"
    KEY_NOT_AUTHORISED = "KEY_NOT_AUTHORISED"
    SUBJECT_MISMATCH = "SUBJECT_MISMATCH"
    SEQUENCE_REPLAY = "SEQUENCE_REPLAY"
    EPOCH_STALE = "EPOCH_STALE"
    KEY_REVOKED = "KEY_REVOKED"
    STATE_CORRUPT = "STATE_CORRUPT"
    CHECKPOINT_FORK = "CHECKPOINT_FORK"
    PROOF_INVALID = "PROOF_INVALID"
    SCOPE_MISMATCH = "SCOPE_MISMATCH"
    ADAPTER_NOT_ALLOWED = "ADAPTER_NOT_ALLOWED"
    SCHEMA_UNKNOWN = "SCHEMA_UNKNOWN"
    PACKAGE_MALFORMED = "PACKAGE_MALFORMED"
    RESOURCE_LIMIT = "RESOURCE_LIMIT"
    HELD = "HELD"
    POLICY_DOWNGRADE = "POLICY_DOWNGRADE"
    AI_FAILED = "AI_FAILED"  # Informational, not a security block


class SegelError(Exception):
    """Base exception for all SEGEL Core errors.

    Every error carries:
    - code: a stable ErrorCode
    - message: human-readable explanation
    - details: optional structured data for diagnostics
    """

    def __init__(self, code: ErrorCode, message: str, details: dict[str, Any] | None = None):
        self.code = code
        self.message = message
        self.details = details or {}
        super().__init__(f"[{code.value}] {message}")


class SignatureError(SegelError):
    """Raised when a cryptographic signature is invalid."""

    def __init__(self, message: str, details: dict[str, Any] | None = None):
        super().__init__(ErrorCode.SIG_INVALID, message, details)


class DigestMismatchError(SegelError):
    """Raised when a digest does not match expected value."""

    def __init__(self, message: str, details: dict[str, Any] | None = None):
        super().__init__(ErrorCode.DIGEST_MISMATCH, message, details)


class StampMissingError(SegelError):
    """Raised when a required stamp is not present."""

    def __init__(self, message: str, details: dict[str, Any] | None = None):
        super().__init__(ErrorCode.STAMP_MISSING, message, details)


class ThresholdNotMetError(SegelError):
    """Raised when approval threshold is not satisfied."""

    def __init__(self, message: str, details: dict[str, Any] | None = None):
        super().__init__(ErrorCode.THRESHOLD_NOT_MET, message, details)


class KeyNotAuthorisedError(SegelError):
    """Raised when a key is not authorised for the attempted operation."""

    def __init__(self, message: str, details: dict[str, Any] | None = None):
        super().__init__(ErrorCode.KEY_NOT_AUTHORISED, message, details)


class SubjectMismatchError(SegelError):
    """Raised when evidence binding does not match the release identity."""

    def __init__(self, message: str, details: dict[str, Any] | None = None):
        super().__init__(ErrorCode.SUBJECT_MISMATCH, message, details)


class SequenceReplayError(SegelError):
    """Raised when a release sequence is not higher than the highest accepted."""

    def __init__(self, message: str, details: dict[str, Any] | None = None):
        super().__init__(ErrorCode.SEQUENCE_REPLAY, message, details)


class EpochStaleError(SegelError):
    """Raised when receiver epoch is lower than required min_epoch."""

    def __init__(self, message: str, details: dict[str, Any] | None = None):
        super().__init__(ErrorCode.EPOCH_STALE, message, details)


class KeyRevokedError(SegelError):
    """Raised when a key has been revoked."""

    def __init__(self, message: str, details: dict[str, Any] | None = None):
        super().__init__(ErrorCode.KEY_REVOKED, message, details)


class StateCorruptError(SegelError):
    """Raised when receiver state is corrupted or inconsistent."""

    def __init__(self, message: str, details: dict[str, Any] | None = None):
        super().__init__(ErrorCode.STATE_CORRUPT, message, details)


class CheckpointForkError(SegelError):
    """Raised when a checkpoint does not extend the stored one (possible fork)."""

    def __init__(self, message: str, details: dict[str, Any] | None = None):
        super().__init__(ErrorCode.CHECKPOINT_FORK, message, details)


class ProofInvalidError(SegelError):
    """Raised when a Merkle proof does not verify."""

    def __init__(self, message: str, details: dict[str, Any] | None = None):
        super().__init__(ErrorCode.PROOF_INVALID, message, details)


class ScopeMismatchError(SegelError):
    """Raised when a release scope does not include this unit."""

    def __init__(self, message: str, details: dict[str, Any] | None = None):
        super().__init__(ErrorCode.SCOPE_MISMATCH, message, details)


class AdapterNotAllowedError(SegelError):
    """Raised when an adapter is not in the pinned allowlist."""

    def __init__(self, message: str, details: dict[str, Any] | None = None):
        super().__init__(ErrorCode.ADAPTER_NOT_ALLOWED, message, details)


class SchemaUnknownError(SegelError):
    """Raised when an unknown schema version or critical field is encountered."""

    def __init__(self, message: str, details: dict[str, Any] | None = None):
        super().__init__(ErrorCode.SCHEMA_UNKNOWN, message, details)


class PackageMalformedError(SegelError):
    """Raised when a package fails validation (path traversal, decompression bomb, etc.)."""

    def __init__(self, message: str, details: dict[str, Any] | None = None):
        super().__init__(ErrorCode.PACKAGE_MALFORMED, message, details)


class ResourceLimitError(SegelError):
    """Raised when a resource limit is exceeded (disk, memory, etc.)."""

    def __init__(self, message: str, details: dict[str, Any] | None = None):
        super().__init__(ErrorCode.RESOURCE_LIMIT, message, details)


class HeldError(SegelError):
    """Raised when a release is held."""

    def __init__(self, message: str, details: dict[str, Any] | None = None):
        super().__init__(ErrorCode.HELD, message, details)


class PolicyDowngradeError(SegelError):
    """Raised when a policy version is lower than the current one."""

    def __init__(self, message: str, details: dict[str, Any] | None = None):
        super().__init__(ErrorCode.POLICY_DOWNGRADE, message, details)

