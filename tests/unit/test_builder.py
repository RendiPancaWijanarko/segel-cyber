# SPDX-License-Identifier: MIT
"""Unit tests for the Builder component.

Tests deterministic packaging, manifest generation, Origin provenance,
and security validation (paths, extensions, sizes).
"""

import json
import tarfile
import io
from pathlib import Path

import pytest

from builder.builder import (
    build_release_package,
    sign_origin,
    sign_manifest,
    _build_deterministic_tar,
    _validate_path,
    FIXED_MTIME,
    FORBIDDEN_EXTENSIONS,
    MAX_FILE_COUNT,
    MAX_FILE_SIZE,
)
from segel_core.crypto.ed25519 import generate_keypair
from segel_core.crypto.dsse import verify_envelope
from segel_core.crypto.hashing import sha256_hex
from segel_core.errors import PackageMalformedError


class TestBuildReleasePackage:
    """Test build_release_package()."""

    def test_basic_build(self):
        files = {"config/a.yaml": b"key: value\n"}
        result = build_release_package(
            files=files, release_id="TEST-1", sequence=1,
            purpose="test", canary_targets=["c1"], general_scope=["c1"],
        )
        assert result.manifest.release_id == "TEST-1"
        assert result.manifest.sequence == 1
        assert len(result.manifest.subjects) == 1
        assert result.manifest.subjects[0].path == "config/a.yaml"
        assert result.manifest.subjects[0].sha256 == sha256_hex(b"key: value\n")
        assert result.manifest.subjects[0].size == 11
        assert len(result.manifest_digest) == 64
        assert len(result.package_digest) == 64

    def test_multiple_files_sorted(self):
        files = {
            "config/z.yaml": b"z",
            "config/a.yaml": b"a",
            "config/m.yaml": b"m",
        }
        result = build_release_package(
            files=files, release_id="SORT-1", sequence=1,
            purpose="test sort", canary_targets=[], general_scope=[],
        )
        paths = [s.path for s in result.manifest.subjects]
        assert paths == ["config/a.yaml", "config/m.yaml", "config/z.yaml"]

    def test_deterministic_build(self):
        """Same input produces same output."""
        files = {"config/a.yaml": b"value: 1\n", "config/b.yaml": b"value: 2\n"}
        kwargs = dict(
            files=files, release_id="DET-1", sequence=1,
            purpose="determinism", canary_targets=["c1"], general_scope=["c1"],
        )
        r1 = build_release_package(**kwargs)
        r2 = build_release_package(**kwargs)
        assert r1.manifest_digest == r2.manifest_digest
        assert r1.package_digest == r2.package_digest

    def test_empty_files_rejected(self):
        with pytest.raises(PackageMalformedError, match="at least one file"):
            build_release_package(
                files={}, release_id="EMPTY-1", sequence=1,
                purpose="empty", canary_targets=[], general_scope=[],
            )

    def test_forbidden_extension_rejected(self):
        for ext in [".exe", ".dll", ".sh", ".py", ".bat", ".cmd", ".ps1", ".so"]:
            with pytest.raises(PackageMalformedError, match="Forbidden file extension"):
                build_release_package(
                    files={f"bad/script{ext}": b"data"},
                    release_id="EXT-1", sequence=1,
                    purpose="test", canary_targets=[], general_scope=[],
                )

    def test_path_traversal_rejected(self):
        with pytest.raises(PackageMalformedError, match="traversal"):
            build_release_package(
                files={"../etc/passwd": b"data"},
                release_id="PATH-1", sequence=1,
                purpose="test", canary_targets=[], general_scope=[],
            )

    def test_absolute_path_rejected(self):
        with pytest.raises(PackageMalformedError, match="Absolute"):
            build_release_package(
                files={"/etc/passwd": b"data"},
                release_id="ABS-1", sequence=1,
                purpose="test", canary_targets=[], general_scope=[],
            )

    def test_null_byte_rejected(self):
        with pytest.raises(PackageMalformedError, match="Null byte"):
            build_release_package(
                files={"config/a\x00.yaml": b"data"},
                release_id="NULL-1", sequence=1,
                purpose="test", canary_targets=[], general_scope=[],
            )

    def test_backslash_rejected(self):
        with pytest.raises(PackageMalformedError, match="Backslash"):
            build_release_package(
                files={"config\\a.yaml": b"data"},
                release_id="BS-1", sequence=1,
                purpose="test", canary_targets=[], general_scope=[],
            )

    def test_origin_statement_structure(self):
        files = {"config/a.yaml": b"key: value\n"}
        result = build_release_package(
            files=files, release_id="ORIGIN-1", sequence=1,
            purpose="test origin", canary_targets=["c1"], general_scope=["c1"],
        )
        stmt = result.origin_statement
        assert stmt["_type"] == "https://in-toto.io/Statement/v1"
        assert len(stmt["subject"]) == 1
        assert stmt["subject"][0]["name"] == "release/ORIGIN-1@1"
        assert "sha256" in stmt["subject"][0]["digest"]
        assert stmt["predicateType"] == "https://segel.dev/attestation/origin/v1"
        pred = stmt["predicate"]
        assert pred["binding"]["stamp"] == "origin"
        assert pred["binding"]["subject"]["release_id"] == "ORIGIN-1"
        assert pred["builder_id"] == "segel-builder/v1"


class TestSignManifest:
    """Test sign_manifest()."""

    def test_sign_produces_valid_envelope(self):
        files = {"config/a.yaml": b"key: value\n"}
        result = build_release_package(
            files=files, release_id="SIG-1", sequence=1,
            purpose="test", canary_targets=[], general_scope=[],
        )
        author_key = generate_keypair()
        env = sign_manifest(result, author_key)
        assert len(env.signatures) == 1
        assert env.payload_type == "application/vnd.segel.manifest+json"

        # Verify
        from segel_core.crypto.ed25519 import PublicKeyInfo
        pub = PublicKeyInfo(
            key_id=author_key.key_id,
            public_key=author_key.public_key,
            public_key_bytes=author_key.public_key_bytes,
        )
        vr = verify_envelope(
            env, [pub],
            expected_payload_type="application/vnd.segel.manifest+json",
        )
        assert author_key.key_id in vr.valid_key_ids


class TestSignOrigin:
    """Test sign_origin()."""

    def test_sign_produces_valid_envelope(self):
        files = {"config/a.yaml": b"key: value\n"}
        result = build_release_package(
            files=files, release_id="ORG-1", sequence=1,
            purpose="test", canary_targets=[], general_scope=[],
        )
        builder_key = generate_keypair()
        env = sign_origin(result, builder_key)
        assert len(env.signatures) == 1
        assert env.payload_type == "application/vnd.segel.origin+json"


class TestDeterministicTar:
    """Test _build_deterministic_tar()."""

    def test_fixed_metadata(self):
        files = {"config/a.yaml": b"data"}
        tar_bytes = _build_deterministic_tar(files)
        buf = io.BytesIO(tar_bytes)
        with tarfile.open(fileobj=buf, mode="r:gz") as tar:
            for member in tar.getmembers():
                assert member.mtime == FIXED_MTIME
                assert member.uid == 0
                assert member.gid == 0
                assert member.uname == "segel"
                assert member.gname == "segel"
                assert member.mode == 0o644

    def test_sorted_entries(self):
        files = {"z.yaml": b"z", "a.yaml": b"a", "m.yaml": b"m"}
        tar_bytes = _build_deterministic_tar(files)
        buf = io.BytesIO(tar_bytes)
        with tarfile.open(fileobj=buf, mode="r:gz") as tar:
            names = tar.getnames()
            assert names == ["a.yaml", "m.yaml", "z.yaml"]

    def test_deterministic_output(self):
        files = {"a.yaml": b"data1", "b.yaml": b"data2"}
        t1 = _build_deterministic_tar(files)
        t2 = _build_deterministic_tar(files)
        assert t1 == t2


class TestValidatePath:
    """Test _validate_path()."""

    def test_valid_paths(self):
        for path in ["config/app.yaml", "data/test.json", "a.yaml"]:
            _validate_path(path)  # Should not raise

    def test_empty_path(self):
        with pytest.raises(PackageMalformedError, match="Empty"):
            _validate_path("")

    def test_absolute_unix(self):
        with pytest.raises(PackageMalformedError, match="Absolute"):
            _validate_path("/etc/passwd")

    def test_absolute_windows(self):
        with pytest.raises(PackageMalformedError, match="Absolute"):
            _validate_path("\\Windows\\System32")

    def test_traversal(self):
        with pytest.raises(PackageMalformedError, match="traversal"):
            _validate_path("../outside")

    def test_null_byte(self):
        with pytest.raises(PackageMalformedError, match="Null byte"):
            _validate_path("file\x00.yaml")

    def test_backslash(self):
        with pytest.raises(PackageMalformedError, match="Backslash"):
            _validate_path("config\\file.yaml")

