# SPDX-License-Identifier: MIT
"""Subprocess worker for AI Inspector integration.

Executed as an isolated process via `python -m inspector.ai.worker` per PRD v2.0 §7.5.
Strictly isolated from signing keys, attestation generation, and release desk.
Communicates via stdin/stdout JSON.
Enforces loopback endpoint gating and JSON-schema structured output with Ollama.
"""

from __future__ import annotations

import json
import sys
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

__all__ = [
    "JSON_SCHEMA",
    "LOOPBACK_HOSTS",
    "main",
    "validate_endpoint_loopback",
]

LOOPBACK_HOSTS = frozenset({"127.0.0.1", "localhost", "::1", "[::1]"})

JSON_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "purpose_class": {
            "type": "string",
            "enum": ["L1", "L2", "L3", "L4", "L5", "L6"],
        },
        "ambiguous": {"type": "boolean"},
        "reason": {"type": "string"},
    },
    "required": ["purpose_class", "ambiguous", "reason"],
    "additionalProperties": False,
}


def validate_endpoint_loopback(endpoint: str) -> str:
    """Validate that the given endpoint URL points to a loopback host.

    Rejects any non-loopback host to enforce sandbox isolation.

    Args:
        endpoint: The base URL string (e.g. 'http://127.0.0.1:11434').

    Returns:
        The validated endpoint string.

    Raises:
        ValueError: If scheme is not http/https or host is non-loopback.
    """
    try:
        parsed = urllib.parse.urlparse(endpoint)
    except Exception as exc:
        raise ValueError(f"Invalid endpoint URL: {exc}") from exc

    if parsed.scheme not in {"http", "https"}:
        raise ValueError(f"Invalid scheme in endpoint: {parsed.scheme}")

    hostname = parsed.hostname
    if not hostname or hostname.lower() not in LOOPBACK_HOSTS:
        raise ValueError(f"Non-loopback host rejected: {hostname}")

    return endpoint


def _fetch_model_digest(endpoint: str, model: str, timeout_s: float) -> tuple[str, str | None]:
    """Query /api/tags to get the model digest."""
    try:
        tags_req = urllib.request.Request(f"{endpoint}/api/tags", method="GET")  # noqa: S310
        with urllib.request.urlopen(tags_req, timeout=timeout_s) as resp:  # noqa: S310 # nosec B310
            tags_data = json.loads(resp.read().decode("utf-8"))
            models = tags_data.get("models", [])
            for m in models:
                m_name = m.get("name", "")
                if m_name == model or m_name.startswith(f"{model}:"):
                    return str(m.get("digest", "")), None
            if models:
                return str(models[0].get("digest", "")), None
            return "", None
    except urllib.error.URLError as exc:
        err_str = str(exc)
        code = "TIMEOUT" if "timed out" in err_str.lower() else "CONNECTION_REFUSED"
        return "", code
    except Exception:
        return "", None


def main() -> int:
    """Worker entry point reading JSON request from stdin and writing JSON result to stdout."""
    try:
        raw_in = sys.stdin.read()
        if not raw_in.strip():
            sys.stdout.write(
                json.dumps({
                    "success": False,
                    "model_id": "",
                    "model_digest": "",
                    "raw_response": None,
                    "content": "",
                    "error": "Empty input to worker",
                    "error_code": "EMPTY_INPUT",
                })
            )
            return 0

        req_data = json.loads(raw_in)
        endpoint = str(req_data.get("endpoint", "http://127.0.0.1:11434"))
        model = str(req_data.get("model", "qwen3:4b"))
        system_prompt = str(req_data.get("system_prompt", ""))
        user_prompt = str(req_data.get("user_prompt", ""))
        timeout_s = float(req_data.get("timeout_s", 30.0))

        # Enforce loopback endpoint check
        validate_endpoint_loopback(endpoint)
    except Exception as exc:
        err_msg = str(exc)
        err_code = "ENDPOINT_NOT_LOOPBACK" if "Non-loopback" in err_msg else "INVALID_REQUEST"
        sys.stdout.write(
            json.dumps({
                "success": False,
                "model_id": "",
                "model_digest": "",
                "raw_response": None,
                "content": "",
                "error": err_msg,
                "error_code": err_code,
            })
        )
        return 0

    # 1. Check tags for model digest
    model_digest, tags_err_code = _fetch_model_digest(
        endpoint, model, timeout_s=min(timeout_s, 5.0)
    )
    if tags_err_code == "CONNECTION_REFUSED":
        sys.stdout.write(
            json.dumps({
                "success": False,
                "model_id": model,
                "model_digest": "",
                "raw_response": None,
                "content": "",
                "error": "Connection refused when contacting Ollama",
                "error_code": "CONNECTION_REFUSED",
            })
        )
        return 0

    # 2. Query /api/chat with structured JSON schema per D11
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "format": JSON_SCHEMA,
        "stream": False,
        "think": False,
        "keep_alive": "30m",
        "options": {
            "temperature": 0,
            "seed": 1,
            "num_ctx": 2048,
            "num_predict": 200,
        },
    }

    try:
        req = urllib.request.Request(  # noqa: S310
            f"{endpoint}/api/chat",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=timeout_s) as resp:  # noqa: S310 # nosec B310
            data = json.loads(resp.read().decode("utf-8"))
            msg = data.get("message", {})
            content = msg.get("content", "")
            sys.stdout.write(
                json.dumps({
                    "success": True,
                    "model_id": model,
                    "model_digest": model_digest,
                    "raw_response": data,
                    "content": content,
                    "error": None,
                    "error_code": None,
                })
            )
            return 0
    except TimeoutError:
        sys.stdout.write(
            json.dumps({
                "success": False,
                "model_id": model,
                "model_digest": model_digest,
                "raw_response": None,
                "content": "",
                "error": "Ollama query timed out",
                "error_code": "TIMEOUT",
            })
        )
        return 0
    except urllib.error.URLError as exc:
        err_str = str(exc)
        err_code = "TIMEOUT" if "timed out" in err_str.lower() else "CONNECTION_REFUSED"
        sys.stdout.write(
            json.dumps({
                "success": False,
                "model_id": model,
                "model_digest": model_digest,
                "raw_response": None,
                "content": "",
                "error": err_str,
                "error_code": err_code,
            })
        )
        return 0
    except Exception as exc:
        sys.stdout.write(
            json.dumps({
                "success": False,
                "model_id": model,
                "model_digest": model_digest,
                "raw_response": None,
                "content": "",
                "error": str(exc),
                "error_code": "WORKER_ERROR",
            })
        )
        return 0


if __name__ == "__main__":
    sys.exit(main())
