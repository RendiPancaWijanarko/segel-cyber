# SPDX-License-Identifier: MIT
"""Canonical serialisation for SEGEL.

Per SEC-007: All signed payloads use canonical JSON serialisation.
This means:
  - Sorted keys
  - No unnecessary whitespace
  - UTF-8 encoding
  - No trailing newline in the serialised bytes

This module provides helpers that every component MUST use when
producing bytes to be signed or hashed.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any

from pydantic import BaseModel


def canonical_json(obj: Any) -> bytes:
    """Serialise an object to canonical JSON bytes.

    - Pydantic models are dumped with ``by_alias=True`` for spec-compatible keys.
    - Dicts and lists are passed through directly.
    - Keys are sorted, ASCII-only separators, no trailing newline.
    """
    data: Any
    if isinstance(obj, BaseModel):
        data = obj.model_dump(by_alias=True, mode="json")
    elif isinstance(obj, (dict, list)):
        data = obj
    else:
        raise TypeError(f"Cannot canonicalise {type(obj).__name__}")
    return json.dumps(
        data,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


def canonical_json_str(obj: Any) -> str:
    """Serialise an object to a canonical JSON string."""
    return canonical_json(obj).decode("utf-8")


def compute_acknowledgement_digest(finding_ids: list[str]) -> str:
    """Compute SHA-256 digest of the canonical sorted list of acknowledged finding IDs.

    Per PRD v2.0 FR-026, FR-032, and Decision D8.
    """
    unique_sorted = sorted({str(fid) for fid in finding_ids})
    canonical_bytes = canonical_json(unique_sorted)
    return hashlib.sha256(canonical_bytes).hexdigest()


