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

import json
from typing import Any

from pydantic import BaseModel


def canonical_json(obj: Any) -> bytes:
    """Serialise an object to canonical JSON bytes.

    - Pydantic models are dumped with ``by_alias=True`` for spec-compatible keys.
    - Dicts are passed through directly.
    - Keys are sorted, ASCII-only separators, no trailing newline.
    """
    if isinstance(obj, BaseModel):
        data = obj.model_dump(by_alias=True, mode="json")
    elif isinstance(obj, dict):
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

