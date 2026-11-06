# SPDX-License-Identifier: MIT
"""Local Append-Only Cryptographic Hash-Chained Audit Logger.

Per PRD SEC-017 & Decision D3:
- Receiver maintains a local, append-only, hash-chained JSON-lines audit log
  recording verification attempts, deployments, and rollbacks.
- Each entry: seq, timestamp, event_type, data, prev_hash, entry_hash.
- No private keys or secrets are logged.
"""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from segel_core.canonical import canonical_json


class AuditLogger:
    """Hash-chained local JSON-lines audit logger."""

    def __init__(self, audit_dir: Path | str) -> None:
        self.audit_dir = Path(audit_dir)
        self.audit_dir.mkdir(parents=True, exist_ok=True)
        self.log_file = self.audit_dir / "audit.jsonl"
        self._last_seq, self._last_hash = self._inspect_last_entry()

    def _inspect_last_entry(self) -> tuple[int, str]:
        """Read the last entry to initialize sequence and prev_hash."""
        if not self.log_file.exists():
            return 0, "0" * 64
        lines = self.log_file.read_text(encoding="utf-8").strip().splitlines()
        if not lines:
            return 0, "0" * 64
        last_line = lines[-1]
        try:
            entry = json.loads(last_line)
            return entry.get("seq", len(lines)), entry.get("entry_hash", "0" * 64)
        except Exception:
            return len(lines), "0" * 64

    def log(self, event_type: str, data: dict[str, Any]) -> dict[str, Any]:
        """Append an event to the hash-chained audit log."""
        self._last_seq += 1
        entry: dict[str, Any] = {
            "seq": self._last_seq,
            "timestamp": datetime.now(UTC).isoformat(),
            "event_type": event_type,
            "data": data,
            "prev_hash": self._last_hash,
        }
        # Compute entry hash over prev_hash || canonical_json(entry)
        payload = self._last_hash.encode("ascii") + canonical_json(entry)
        entry_hash = hashlib.sha256(payload).hexdigest()
        entry["entry_hash"] = entry_hash
        self._last_hash = entry_hash

        with Path(self.log_file).open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry, sort_keys=True) + "\n")

        return entry

