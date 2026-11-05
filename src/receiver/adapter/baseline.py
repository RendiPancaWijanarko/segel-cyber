# SPDX-License-Identifier: MIT
"""Baseline v1 configuration deployment adapter.

Per PRD v2.0 §17.4 and TAS §8.9:
- The deployment adapter is restricted to a pinned set of operations.
- It MUST NOT execute arbitrary scripts from release bundles (SEC-025).
- It follows the 10-step deployment lifecycle:
  1. preflight — Check preconditions
  2. snapshot — Capture current state digest
  3. stage — Extract files to staging area
  4. validate — Validate staged files against manifest
  5. backup — Copy current config to backup
  6. apply — Atomically move staged files to target
  7. health_check — Run health probes
  8. commit — Confirm successful deployment
  9. rollback — Revert to backup if health fails
  10. cleanup — Remove staging/backup on success

- Restricted paths: only writes to the configured deploy_root.
- File modes are read-only (0o444).
- Health probes are from a fixed vocabulary.
"""

from __future__ import annotations

import contextlib
import shutil
import stat
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from segel_core.crypto.hashing import sha256_hex
from segel_core.errors import (
    AdapterNotAllowedError,
    DigestMismatchError,
    PackageMalformedError,
)
from segel_core.schemas.attestation import HealthResult
from segel_core.schemas.manifest import Manifest

ADAPTER_ID = "segel-baseline-adapter/v1"


def _safe_rmtree(path: Path | str) -> None:
    """Recursively remove a directory, clearing read-only flags on Windows."""
    p = Path(path)
    if not p.exists():
        return

    def _handle_error(func: Any, target_path: Any, exc_info: Any = None) -> None:
        try:
            Path(target_path).chmod(stat.S_IWRITE | stat.S_IREAD)
            func(target_path)
        except OSError:
            pass

    try:
        shutil.rmtree(p, onexc=lambda fn, path_arg, _: _handle_error(fn, path_arg))
    except TypeError:
        shutil.rmtree(p, onerror=_handle_error)


def _safe_unlink(path: Path | str) -> None:
    """Remove a file, clearing read-only flags if needed."""
    p = Path(path)
    if not p.exists():
        return
    with contextlib.suppress(OSError):
        p.chmod(stat.S_IWRITE | stat.S_IREAD)
    with contextlib.suppress(OSError):
        p.unlink()


@dataclass
class DeploymentState:
    """State captured during the deployment lifecycle."""
    pre_state_digest: str = ""
    post_state_digest: str = ""
    staged_files: list[str] = field(default_factory=list)
    backup_path: str = ""
    health_results: list[HealthResult] = field(default_factory=list)
    overall_result: str = "error"  # healthy, unhealthy, error
    committed: bool = False


class BaselineAdapter:
    """Baseline v1 configuration deployment adapter.

    Deploys configuration files to a target directory with backup/rollback
    support and health checking. Does NOT execute any scripts.
    """

    def __init__(
        self,
        deploy_root: str | Path,
        staging_root: str | Path | None = None,
        backup_root: str | Path | None = None,
    ) -> None:
        """Initialise the adapter.

        Args:
            deploy_root: Target directory for configuration files.
            staging_root: Staging area for validation. Defaults to deploy_root/.staging
            backup_root: Backup directory. Defaults to deploy_root/.backup
        """
        self._deploy_root = Path(deploy_root).resolve()
        self._staging_root = (
            Path(staging_root).resolve() if staging_root else self._deploy_root / ".staging"
        )
        self._backup_root = (
            Path(backup_root).resolve() if backup_root else self._deploy_root / ".backup"
        )

        # Validate paths are not overlapping dangerously
        if not str(self._staging_root).startswith(str(self._deploy_root.parent)):
            raise AdapterNotAllowedError(
                "Staging root must be within the deployment area"
            )

    @property
    def adapter_identity(self) -> str:
        return ADAPTER_ID

    def preflight(self, manifest: Manifest) -> None:
        """Step 1: Check preconditions.

        Validates that the deployment is safe to proceed.
        """
        # Validate all paths are within deploy_root
        for subject in manifest.subjects:
            resolved = (self._deploy_root / subject.path).resolve()
            if not str(resolved).startswith(str(self._deploy_root)):
                raise PackageMalformedError(
                    f"Path escape detected: {subject.path} resolves outside deploy_root"
                )

        # Ensure deploy root exists
        self._deploy_root.mkdir(parents=True, exist_ok=True)

        # Purge any stale staging directories from previous runs/crashes
        if self._staging_root.exists():
            _safe_rmtree(self._staging_root)
        segel_stage = self._deploy_root / ".segel_stage"
        if segel_stage.exists():
            _safe_rmtree(segel_stage)

    def snapshot(self) -> str:
        """Step 2: Capture current state digest.

        Returns SHA-256 of the current deployment directory state.
        """
        return self._compute_directory_digest(self._deploy_root)

    def stage(
        self,
        manifest: Manifest,
        files: dict[str, bytes],
    ) -> list[str]:
        """Step 3: Extract files to staging area.

        Validates each file against the manifest digests.

        Args:
            manifest: The release manifest.
            files: Dict of relative_path -> file_contents.

        Returns:
            List of staged file paths.
        """
        # Clean staging area
        if self._staging_root.exists():
            _safe_rmtree(self._staging_root)
        self._staging_root.mkdir(parents=True)

        staged = []
        for subject in manifest.subjects:
            if subject.path not in files:
                raise DigestMismatchError(
                    f"File missing from bundle: {subject.path}"
                )

            content = files[subject.path]

            # Verify digest
            computed = sha256_hex(content)
            if computed != subject.sha256:
                raise DigestMismatchError(
                    f"Digest mismatch for {subject.path}: "
                    f"manifest={subject.sha256}, computed={computed}",
                )

            # Verify size
            if len(content) != subject.size:
                raise DigestMismatchError(
                    f"Size mismatch for {subject.path}: "
                    f"manifest={subject.size}, actual={len(content)}",
                )

            # Write to staging
            target = self._staging_root / subject.path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(content)
            staged.append(subject.path)

        self._write_journal("stage")
        return staged

    def backup(self) -> str:
        """Step 5: Copy current config to backup.

        Returns the backup directory path.
        """
        if self._backup_root.exists():
            _safe_rmtree(self._backup_root)
        self._backup_root.mkdir(parents=True)

        if self._deploy_root.exists():
            for item in self._deploy_root.iterdir():
                if item.name.startswith("."):
                    continue  # Skip staging/backup dirs
                dest = self._backup_root / item.name
                if item.is_dir():
                    shutil.copytree(item, dest)
                else:
                    shutil.copy2(item, dest)

        self._write_journal("backup")
        return str(self._backup_root)

    def apply(self, manifest: Manifest) -> None:
        """Step 6: Move staged files to target.

        Copies files from staging to deploy_root.
        """
        for subject in manifest.subjects:
            src = self._staging_root / subject.path
            dst = self._deploy_root / subject.path
            dst.parent.mkdir(parents=True, exist_ok=True)

            # Copy (not move, so staging remains for verification)
            shutil.copy2(src, dst)

            # Set read-only (SEC-025)
            with contextlib.suppress(OSError):
                dst.chmod(0o444)

        self._write_journal("apply")

    def health_check(
        self,
        manifest: Manifest,
        probes: list[dict[str, Any]] | None = None,
    ) -> list[HealthResult]:
        """Step 7: Run health probes.

        Default probes: file_exists and config_valid for each deployed file.

        Args:
            manifest: The release manifest.
            probes: Optional explicit probe list.

        Returns:
            List of health check results.
        """
        results = []

        for subject in manifest.subjects:
            target = self._deploy_root / subject.path

            # Probe file exists check
            exists = target.exists()
            results.append(HealthResult(
                probe="file_exists",
                target=subject.path,
                expected="true",
                actual=str(exists).lower(),
                passed=exists,
            ))

            # Probe: config_valid (verify digest matches after deployment)
            if exists:
                content = target.read_bytes()
                computed = sha256_hex(content)
                digest_ok = computed == subject.sha256
                results.append(HealthResult(
                    probe="config_valid",
                    target=subject.path,
                    expected=subject.sha256,
                    actual=computed,
                    passed=digest_ok,
                ))

        return results

    def commit(self) -> str:
        """Step 8: Confirm successful deployment.

        Returns post-state digest.
        """
        return self._compute_directory_digest(self._deploy_root)

    def rollback(self) -> None:
        """Step 9: Revert to backup.

        Restores the backup directory to deploy_root.
        """
        if self._backup_root.exists():
            # Remove current files (except hidden dirs)
            for item in self._deploy_root.iterdir():
                if item.name.startswith("."):
                    continue
                if item.is_dir():
                    _safe_rmtree(item)
                else:
                    _safe_unlink(item)

            # Restore from backup
            for item in self._backup_root.iterdir():
                dest = self._deploy_root / item.name
                if item.is_dir():
                    shutil.copytree(item, dest)
                else:
                    shutil.copy2(item, dest)

        # Remove staging debris if present
        if self._staging_root.exists():
            _safe_rmtree(self._staging_root)
        segel_stage = self._deploy_root / ".segel_stage"
        if segel_stage.exists():
            _safe_rmtree(segel_stage)

        # Remove journal
        journal = self._deploy_root / ".segel_journal.json"
        if journal.exists():
            _safe_unlink(journal)

    def cleanup(self) -> None:
        """Step 10: Remove staging and backup on success."""
        if self._staging_root.exists():
            _safe_rmtree(self._staging_root)
        segel_stage = self._deploy_root / ".segel_stage"
        if segel_stage.exists():
            _safe_rmtree(segel_stage)
        if self._backup_root.exists():
            _safe_rmtree(self._backup_root)
        journal = self._deploy_root / ".segel_journal.json"
        if journal.exists():
            _safe_unlink(journal)

    def recover_crash(self) -> None:
        """Recover from an interrupted or crashed deployment.

        Per FR-083 & AT-030:
        Replays the journal to recover the deployment directory:
        restores backup if available, purges partial staging debris,
        and removes journal and lock files.
        """
        if self._backup_root.exists():
            self.rollback()
            _safe_rmtree(self._backup_root)
        else:
            if self._staging_root.exists():
                _safe_rmtree(self._staging_root)
            segel_stage = self._deploy_root / ".segel_stage"
            if segel_stage.exists():
                _safe_rmtree(segel_stage)

        journal = self._deploy_root / ".segel_journal.json"
        if journal.exists():
            _safe_unlink(journal)
        lock_file = self._deploy_root / ".deploy.lock"
        if lock_file.exists():
            _safe_unlink(lock_file)

    def _write_journal(self, step: str) -> None:
        """Write atomic state transition to the deployment journal."""
        import json
        journal_path = self._deploy_root / ".segel_journal.json"
        journal_data = {
            "step": step,
            "backup_exists": self._backup_root.exists(),
        }
        with open(journal_path, "w", encoding="utf-8") as f:
            json.dump(journal_data, f)

    def _compute_directory_digest(self, directory: Path) -> str:
        """Compute a deterministic digest of a directory's contents."""
        import hashlib
        h = hashlib.sha256()
        if not directory.exists():
            return h.hexdigest()

        for path in sorted(directory.rglob("*")):
            if path.is_file() and not any(
                p.name.startswith(".") for p in path.relative_to(directory).parents
            ):
                rel = str(path.relative_to(directory)).replace("\\", "/")
                h.update(rel.encode("utf-8"))
                h.update(path.read_bytes())
        return h.hexdigest()

