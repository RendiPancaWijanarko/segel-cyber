# SPDX-License-Identifier: MIT
"""Test-split access guard for AI evaluation scripts.

Per PRD v2.0, TAS, and docs/ai_decisions.md (D9, D9b, D14):
All scripts under scripts/ai_eval MUST refuse to access TEST-*.json unless:
1. Environment variable SEGEL_ALLOW_TEST_EVAL=1 is set.
2. The SHA-256 of every test file exactly matches docs/ai_corpus_freeze.txt.

By default, all scripts load and evaluate exemplar and dev items only.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent.parent
DEFAULT_FREEZE_FILE = WORKSPACE_ROOT / "docs" / "ai_corpus_freeze.txt"
DEFAULT_CORPUS_DIR = WORKSPACE_ROOT / "lab" / "ai_corpus"
ENV_VAR_ALLOW_TEST = "SEGEL_ALLOW_TEST_EVAL"


def verify_freeze_integrity(
    freeze_file: Path | str | None = None,
    workspace_root: Path | str | None = None,
) -> tuple[bool, str]:
    """Verify that every TEST-*.json file matches the frozen hash in docs/ai_corpus_freeze.txt."""
    ws = Path(workspace_root) if workspace_root else WORKSPACE_ROOT
    ff = Path(freeze_file) if freeze_file else (ws / "docs" / "ai_corpus_freeze.txt")

    if not ff.exists():
        return False, f"Freeze file not found: {ff}"

    lines = ff.read_text(encoding="utf-8").strip().splitlines()
    expected_hashes: dict[str, str] = {}
    expected_concat: str | None = None

    for line in lines:
        cleaned = line.strip()
        if not cleaned or cleaned.startswith("#"):
            continue
        parts = cleaned.split()
        if len(parts) == 2:
            sha, rel_path = parts
            if rel_path == "test_split_concatenation":
                expected_concat = sha
            else:
                expected_hashes[rel_path] = sha

    if not expected_hashes:
        return False, f"No test hashes found in freeze file: {ff}"

    concat_bytes = b""
    for rel_path in sorted(expected_hashes.keys()):
        file_path = ws / rel_path
        if not file_path.exists():
            return False, f"Missing frozen test file: {rel_path}"
        content = file_path.read_bytes()
        actual_sha = hashlib.sha256(content).hexdigest()
        exp_sha = expected_hashes[rel_path]
        if actual_sha != exp_sha:
            return (
                False,
                f"Hash mismatch for {rel_path}: actual {actual_sha} != expected {exp_sha}",
            )
        concat_bytes += content

    if expected_concat is not None:
        actual_concat = hashlib.sha256(concat_bytes).hexdigest()
        if actual_concat != expected_concat:
            return (
                False,
                f"Test split concatenation mismatch: {actual_concat} != {expected_concat}",
            )

    return True, f"Verified {len(expected_hashes)} test files against freeze"


def can_read_test_split(
    workspace_root: Path | str | None = None,
    freeze_file: Path | str | None = None,
) -> tuple[bool, str]:
    """Check whether reading test split is permitted under current environment and freeze."""
    if os.environ.get(ENV_VAR_ALLOW_TEST) != "1":
        return False, f"{ENV_VAR_ALLOW_TEST}=1 is not set"

    valid, msg = verify_freeze_integrity(freeze_file=freeze_file, workspace_root=workspace_root)
    if not valid:
        return False, f"Corpus freeze integrity check failed: {msg}"

    return True, "Test split access authorized"


def guard_read_corpus_file(
    file_path: Path | str,
    workspace_root: Path | str | None = None,
) -> dict[str, Any]:
    """Safely read a corpus JSON file, enforcing the test split guard."""
    path = Path(file_path)
    is_test = path.name.startswith("TEST-")

    # If it is a test file, enforce guard
    if is_test:
        allowed, reason = can_read_test_split(workspace_root=workspace_root)
        if not allowed:
            raise PermissionError(
                f"Test split access denied for '{path.name}': {reason}. "
                f"Default is exemplar and dev only."
            )

    content = path.read_text(encoding="utf-8")
    data = json.loads(content)

    # Secondary check on content split field
    if data.get("split") == "test" and not is_test:
        allowed, reason = can_read_test_split(workspace_root=workspace_root)
        if not allowed:
            raise PermissionError(
                f"Test split item '{data.get('id', path.name)}' denied: {reason}."
            )

    return data


def get_corpus_files(
    corpus_dir: Path | str,
    include_test: bool = False,
    workspace_root: Path | str | None = None,
) -> list[Path]:
    """Return list of corpus files to process, defaulting to exemplar and dev only."""
    dir_path = Path(corpus_dir)
    if not dir_path.exists():
        raise FileNotFoundError(f"Corpus directory not found: {dir_path}")

    all_json = sorted(dir_path.glob("*.json"))
    default_files = [
        f for f in all_json if f.name.startswith("EX-") or f.name.startswith("DEV-")
    ]

    if not include_test:
        return default_files

    # Test split requested: verify permission
    allowed, reason = can_read_test_split(workspace_root=workspace_root)
    if not allowed:
        raise PermissionError(
            f"Cannot include test split files: {reason}. "
            f"Set {ENV_VAR_ALLOW_TEST}=1 and ensure freeze integrity."
        )

    return all_json
