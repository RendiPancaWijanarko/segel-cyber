# SPDX-License-Identifier: MIT
"""Unit tests for AI evaluation test-split guard (AI-4b / B1).

Tests that all scripts in scripts/ai_eval refuse to access TEST-*.json
unless SEGEL_ALLOW_TEST_EVAL=1 is set AND docs/ai_corpus_freeze.txt SHA-256
hashes match.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from scripts.ai_eval.guard import (
    can_read_test_split,
    get_corpus_files,
    guard_read_corpus_file,
    verify_freeze_integrity,
)


def test_default_disallows_test_split(monkeypatch: pytest.MonkeyPatch) -> None:
    """Without SEGEL_ALLOW_TEST_EVAL=1, test split reading is disallowed."""
    monkeypatch.delenv("SEGEL_ALLOW_TEST_EVAL", raising=False)
    allowed, reason = can_read_test_split()
    assert not allowed
    assert "SEGEL_ALLOW_TEST_EVAL=1 is not set" in reason


def test_guard_read_test_file_without_env_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    """Attempting to read TEST-*.json without env var raises PermissionError."""
    monkeypatch.delenv("SEGEL_ALLOW_TEST_EVAL", raising=False)
    test_file = Path("lab/ai_corpus/TEST-01.json")
    with pytest.raises(PermissionError, match="Test split access denied"):
        guard_read_corpus_file(test_file)


def test_get_corpus_files_default_excludes_test_split(monkeypatch: pytest.MonkeyPatch) -> None:
    """By default, get_corpus_files returns only exemplar and dev splits (30 files)."""
    monkeypatch.delenv("SEGEL_ALLOW_TEST_EVAL", raising=False)
    corpus_dir = Path("lab/ai_corpus")
    files = get_corpus_files(corpus_dir)
    assert len(files) == 30
    for f in files:
        assert not f.name.startswith("TEST-")
        assert f.name.startswith("EX-") or f.name.startswith("DEV-")


def test_freeze_integrity_passes_on_current_repo() -> None:
    """docs/ai_corpus_freeze.txt matches the actual test split on disk."""
    valid, msg = verify_freeze_integrity()
    assert valid, f"Freeze verification failed: {msg}"


def test_test_split_allowed_with_env_and_valid_freeze(monkeypatch: pytest.MonkeyPatch) -> None:
    """When SEGEL_ALLOW_TEST_EVAL=1 and freeze matches, test split reading is allowed."""
    monkeypatch.setenv("SEGEL_ALLOW_TEST_EVAL", "1")
    allowed, reason = can_read_test_split()
    assert allowed, f"Expected allowed, got: {reason}"
    data = guard_read_corpus_file(Path("lab/ai_corpus/TEST-01.json"))
    assert data["id"] == "TEST-01"
    assert data["split"] == "test"


def test_freeze_integrity_fails_when_test_file_tampered(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """If a test file hash differs from freeze file, access is denied even with env var."""
    monkeypatch.setenv("SEGEL_ALLOW_TEST_EVAL", "1")
    # Create fake freeze file with invalid hash
    fake_freeze = tmp_path / "fake_freeze.txt"
    fake_freeze.write_text(
        "0000000000000000000000000000000000000000000000000000000000000000  lab/ai_corpus/TEST-01.json\n",
        encoding="utf-8",
    )
    valid, msg = verify_freeze_integrity(freeze_file=fake_freeze)
    assert not valid
    assert "Mismatch" in msg or "hash mismatch" in msg.lower()
