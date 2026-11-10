# SPDX-License-Identifier: MIT
"""Deterministic packaging and Origin provenance builder.

Per PRD v2.0 §7.3:
- Builder produces a deterministic package from release files.
- Builder generates SLSA-aligned Origin provenance as an in-toto Statement.
- Builder signs the provenance with its own key (separate from Author).
- Package is a tar.gz with sorted entries and fixed metadata.

Per SEC-017:
- Package creation uses sorted paths, fixed mtime, fixed uid/gid.
- SHA-256 digests are computed over the deterministic archive.
"""

from __future__ import annotations

import io
import re
import tarfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from segel_core.canonical import canonical_json
from segel_core.crypto.dsse import DSSEEnvelope, create_envelope
from segel_core.crypto.ed25519 import KeyPair, generate_evidence_id
from segel_core.crypto.hashing import sha256_hex
from segel_core.errors import PackageMalformedError
from segel_core.schemas.attestation import (
    ORIGIN_PREDICATE_TYPE,
    InTotoStatement,
    InTotoSubject,
    OriginPredicate,
)
from segel_core.schemas.binding import BindingBlock, ReleaseSubject
from segel_core.schemas.manifest import Manifest, SubjectDigest

# Fixed metadata for deterministic archives (SEC-017)
FIXED_MTIME = 1700000000  # 2023-11-14T22:13:20Z
FIXED_UID = 0
FIXED_GID = 0
FIXED_UNAME = "segel"
FIXED_GNAME = "segel"

# Limits for security (SEC-023)
MAX_FILE_SIZE = 50 * 1024 * 1024   # 50 MiB per file
MAX_TOTAL_SIZE = 200 * 1024 * 1024  # 200 MiB total
MAX_FILE_COUNT = 500
FORBIDDEN_EXTENSIONS = {".exe", ".dll", ".so", ".sh", ".bat", ".cmd", ".ps1", ".py"}


@dataclass
class BuildResult:
    """Result of a deterministic build."""
    package_bytes: bytes           # The .tar.gz archive
    package_digest: str            # SHA-256 hex of the archive
    manifest: Manifest             # The release manifest
    manifest_bytes: bytes          # Canonical JSON of the manifest
    manifest_digest: str           # SHA-256 hex of manifest bytes
    origin_statement: dict[str, Any]         # The in-toto statement (unsigned)
    origin_envelope: DSSEEnvelope | None = None  # Signed, if builder key provided


def build_release_package(
    files: dict[str, bytes],
    release_id: str,
    sequence: int,
    purpose: str,
    canary_targets: list[str] | None = None,
    general_scope: list[str] | None = None,
) -> BuildResult:
    """Build a deterministic release package from files.

    Args:
        files: Dict of relative_path -> file_contents.
        release_id: Release identifier.
        sequence: Monotonically increasing sequence number.
        purpose: Human-readable release purpose.
        canary_targets: Unit IDs for canary deployment.
        general_scope: Unit IDs for general deployment.

    Returns:
        BuildResult with the package, manifest, and origin statement.

    Raises:
        PackageMalformedError: If files violate security constraints.
    """
    if not files:
        raise PackageMalformedError("Release must contain at least one file")
    if len(files) > MAX_FILE_COUNT:
        raise PackageMalformedError(
            f"Too many files: {len(files)} > {MAX_FILE_COUNT}"
        )

    # Validate files and compute subjects
    subjects: list[SubjectDigest] = []
    total_size = 0

    for path, content in sorted(files.items()):
        _validate_path(path)
        if len(content) > MAX_FILE_SIZE:
            raise PackageMalformedError(
                f"File too large: {path} ({len(content)} bytes > {MAX_FILE_SIZE})"
            )
        total_size += len(content)
        if total_size > MAX_TOTAL_SIZE:
            raise PackageMalformedError(
                f"Total package size exceeds {MAX_TOTAL_SIZE} bytes"
            )

        # Check for forbidden executable extensions (SEC-025)
        ext = Path(path).suffix.lower()
        if ext in FORBIDDEN_EXTENSIONS:
            raise PackageMalformedError(
                f"Forbidden file extension: {path} ({ext}). "
                "SEGEL deploys configuration, not executables."
            )

        subjects.append(SubjectDigest(
            path=path,
            sha256=sha256_hex(content),
            size=len(content),
        ))

    # Build manifest (sanitize control characters per D16 defense-in-depth)
    clean_purpose = re.sub(r"[\x00-\x1f\x7f-\x9f]", "", purpose) if purpose else purpose
    manifest = Manifest(
        release_id=release_id,
        sequence=sequence,
        purpose=clean_purpose,
        subjects=subjects,
        canary_targets=canary_targets or [],
        general_scope=general_scope or [],
    )
    manifest_bytes = canonical_json(manifest)
    manifest_digest = sha256_hex(manifest_bytes)

    # Build deterministic tar.gz
    package_bytes = _build_deterministic_tar(files)
    package_digest = sha256_hex(package_bytes)

    # Build Origin provenance (in-toto Statement, unsigned)
    origin_binding = BindingBlock(
        stamp="origin",
        subject=ReleaseSubject(
            release_id=release_id,
            sequence=sequence,
            manifest_sha256=manifest_digest,
        ),
        trust_root_version=1,  # Set by caller
        policy_version=1,      # Set by caller
        evidence_id=generate_evidence_id(),
    )

    origin_predicate = OriginPredicate(
        binding=origin_binding,
        builder_id="segel-builder/v1",
        builder_domain="local",
        output_digest=package_digest,
    )

    in_toto_subject = InTotoSubject(
        name=f"release/{release_id}@{sequence}",
        digest={"sha256": manifest_digest},
    )

    origin_statement = InTotoStatement(
        subject=[in_toto_subject],
        predicateType=ORIGIN_PREDICATE_TYPE,
        predicate=origin_predicate.model_dump(mode="json"),
    )

    origin_statement_dict = origin_statement.model_dump(by_alias=True, mode="json")

    return BuildResult(
        package_bytes=package_bytes,
        package_digest=package_digest,
        manifest=manifest,
        manifest_bytes=manifest_bytes,
        manifest_digest=manifest_digest,
        origin_statement=origin_statement_dict,
    )


def sign_origin(
    build_result: BuildResult,
    builder_key: KeyPair,
) -> DSSEEnvelope:
    """Sign the Origin provenance with the builder's key.

    Args:
        build_result: Result from build_release_package.
        builder_key: The builder's signing key.

    Returns:
        A DSSE envelope wrapping the signed Origin attestation.
    """
    payload = canonical_json(build_result.origin_statement)

    envelope = create_envelope(
        payload_type="application/vnd.segel.origin+json",
        payload=payload,
        signers=[(builder_key.key_id, builder_key.private_key)],
    )

    build_result.origin_envelope = envelope
    return envelope


def sign_manifest(
    build_result: BuildResult,
    author_key: KeyPair,
) -> DSSEEnvelope:
    """Sign the manifest with the author's key.

    Args:
        build_result: Result from build_release_package.
        author_key: The author's signing key.

    Returns:
        A DSSE envelope wrapping the signed manifest.
    """
    return create_envelope(
        payload_type="application/vnd.segel.manifest+json",
        payload=build_result.manifest_bytes,
        signers=[(author_key.key_id, author_key.private_key)],
    )


def _build_deterministic_tar(files: dict[str, bytes]) -> bytes:
    """Build a deterministic tar.gz archive.

    Per SEC-017: sorted paths, fixed mtime, fixed uid/gid.
    """
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tar:
        for path in sorted(files.keys()):
            content = files[path]
            info = tarfile.TarInfo(name=path)
            info.size = len(content)
            info.mtime = FIXED_MTIME
            info.uid = FIXED_UID
            info.gid = FIXED_GID
            info.uname = FIXED_UNAME
            info.gname = FIXED_GNAME
            info.mode = 0o644
            tar.addfile(info, io.BytesIO(content))
    return buf.getvalue()


def _validate_path(path: str) -> None:
    """Validate a file path for security.

    Per SEC-023: Reject path traversal, absolute paths, etc.
    """
    if not path:
        raise PackageMalformedError("Empty file path")
    if path.startswith(("/", "\\")):
        raise PackageMalformedError(f"Absolute path not allowed: {path}")
    if ".." in path.split("/") or ".." in path.split("\\"):
        raise PackageMalformedError(f"Path traversal not allowed: {path}")
    if "\x00" in path:
        raise PackageMalformedError(f"Null byte in path: {path!r}")
    # Normalise to forward slashes only
    if "\\" in path:
        raise PackageMalformedError(
            f"Backslash in path not allowed (use forward slash): {path}"
        )

