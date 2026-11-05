# SPDX-License-Identifier: MIT
"""Phase C Hardening Gap Tests: C5 — AT-030 Real Crash Injection & Journal Recovery.

Requirement: PRD 27.2 Table 50 (AT-030) & FR-083 / SEC-030:
- Power loss or process death (os._exit) at every deployment journal step
  MUST be recoverable upon restart.
- A fresh receiver process starting against an interrupted deployment directory
  MUST automatically replay the journal: either roll back cleanly to the pre-state
  or finish the forward deployment to the target state.
- No partial, corrupted, or inconsistent intermediate files may remain.

Tests:
1. test_c5_at030_positive_control_clean_deployment: Normal deployment succeeds
   and leaves deploy_dir matching target files.
2. test_c5_at030_red_crash_during_staging_recovery: Subprocess crash during staging
   followed by fresh receiver startup must recover cleanly to pre-state.
3. test_c5_at030_red_crash_during_apply_recovery: Subprocess crash during file apply
   followed by fresh receiver startup must recover cleanly to pre-state.
"""

from __future__ import annotations

import hashlib
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

from receiver.adapter.baseline import BaselineAdapter
from receiver.receiver import Receiver, ReceiverState
from tests.adversarial.test_at_NNN import SyntheticLab, _build_valid_candidate


def _dir_digest(directory: Path) -> str:
    """Calculate combined SHA-256 of all files in directory for strict state comparison."""
    h = hashlib.sha256()
    for p in sorted(directory.rglob("*")):
        if p.is_file():
            rel = p.relative_to(directory).as_posix()
            h.update(rel.encode("utf-8"))
            h.update(p.read_bytes())
    return h.hexdigest()


@pytest.mark.gap
def test_c5_at030_positive_control_clean_deployment() -> None:
    """Positive control: Normal clean deployment transitions directory state."""
    lab = SyntheticLab()
    files = {"app.yaml": b"version: 1\n"}
    files, _, passport, _ = _build_valid_candidate(lab, release_id="REL-GAP-030-P", sequence=1, files=files)

    with tempfile.TemporaryDirectory() as td:
        deploy_dir = Path(td) / "deploy"
        deploy_dir.mkdir()
        (deploy_dir / "old.yaml").write_text("old: true\n", encoding="utf-8")
        pre_digest = _dir_digest(deploy_dir)

        receiver = Receiver(
            state=ReceiverState(unit_id="canary-1", unit_role="canary"),
            trust_ctx=lab.trust_ctx,
            receiver_key=lab.canary_keys[0],
            deploy_root=deploy_dir,
        )

        verification, receipt = receiver.verify_and_deploy(passport, files)
        assert receipt is not None
        post_digest = _dir_digest(deploy_dir)
        assert post_digest != pre_digest
        assert (deploy_dir / "app.yaml").read_text(encoding="utf-8") == "version: 1\n"


@pytest.mark.gap
def test_c5_at030_red_crash_during_staging_recovery() -> None:
    """RED TEST: Process death mid-staging leaves persistent journal that recovers to pre-state.

    Per FR-083 & AT-030: If process is killed (kill -9 / os._exit) while staging files,
    a subsequent process restart must detect the unfinished deployment journal and
    restore the directory to the exact pre-crash state.
    """
    with tempfile.TemporaryDirectory() as td:
        deploy_dir = Path(td) / "deploy"
        deploy_dir.mkdir()
        initial_file = deploy_dir / "service.conf"
        initial_file.write_text("status=active\n", encoding="utf-8")
        pre_digest = _dir_digest(deploy_dir)

        # Execute simulated crash script in a separate Python process
        crash_script = f"""
import os, sys, tempfile
from pathlib import Path
from receiver.adapter.baseline import BaselineAdapter

deploy_dir = Path(r"{deploy_dir}")
adapter = BaselineAdapter(deploy_dir)
adapter.snapshot()
adapter.backup()

# Simulate writing partial staged files
stage_dir = deploy_dir / ".segel_stage"
stage_dir.mkdir(exist_ok=True)
(stage_dir / "corrupted_half_written.bin").write_bytes(b"\\x00" * 1024)

# Abrupt crash simulating sudden power failure mid-stage
os._exit(42)
"""
        sub_env = {**os.environ, "PYTHONPATH": str(Path("src").resolve()) + os.pathsep + os.environ.get("PYTHONPATH", "")}
        res = subprocess.run(
            [sys.executable, "-c", crash_script],
            capture_output=True,
            text=True,
            env=sub_env,
        )
        assert res.returncode == 42, "Simulated crash subprocess must exit with 42"

        # A new process/receiver starts up and attempts journal crash recovery
        adapter_recovered = BaselineAdapter(deploy_dir)
        # FR-083 gap: BaselineAdapter does not have persistent disk journal replay
        if hasattr(adapter_recovered, "recover_crash"):
            adapter_recovered.recover_crash()
        else:
            adapter_recovered.rollback()

        # The state must be cleanly restored to pre-crash state, no staging debris left
        assert (deploy_dir / ".segel_stage").exists() is False, (
            "FR-083 Violation: Staged debris was not cleaned up after crash recovery!"
        )
        assert _dir_digest(deploy_dir) == pre_digest, (
            "AT-030 Violation: Crash recovery failed to restore pre-deployment state!"
        )


@pytest.mark.gap
def test_c5_at030_red_crash_during_apply_recovery() -> None:
    """RED TEST: Process death mid-apply leaves persistent journal that recovers cleanly.

    Per FR-083 & AT-030: If power fails while files are being replaced, crash recovery
    must restore original files from backup without data corruption.
    """
    with tempfile.TemporaryDirectory() as td:
        deploy_dir = Path(td) / "deploy"
        deploy_dir.mkdir()
        config_file = deploy_dir / "config.json"
        config_file.write_text('{{"safe": true}}', encoding="utf-8")
        pre_digest = _dir_digest(deploy_dir)

        crash_script = f"""
import os, sys
from pathlib import Path
from receiver.adapter.baseline import BaselineAdapter

deploy_dir = Path(r"{deploy_dir}")
adapter = BaselineAdapter(deploy_dir)
adapter.snapshot()
adapter.backup()

# Simulate partial overwrite before crash
(deploy_dir / "config.json").write_text('{{"corrupted": ', encoding="utf-8")

# Crash mid-apply
os._exit(99)
"""
        sub_env = {**os.environ, "PYTHONPATH": str(Path("src").resolve()) + os.pathsep + os.environ.get("PYTHONPATH", "")}
        res = subprocess.run(
            [sys.executable, "-c", crash_script],
            capture_output=True,
            text=True,
            env=sub_env,
        )
        assert res.returncode == 99

        # Recovery on fresh adapter
        adapter_recovered = BaselineAdapter(deploy_dir)
        if hasattr(adapter_recovered, "recover_crash"):
            adapter_recovered.recover_crash()
        else:
            adapter_recovered.rollback()

        # Config file must be intact and match pre-state
        assert _dir_digest(deploy_dir) == pre_digest, (
            "AT-030 Violation: Crash recovery mid-apply left corrupted file!"
        )
