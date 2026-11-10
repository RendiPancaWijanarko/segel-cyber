# SPDX-License-Identifier: MIT
"""AI Inspector Client — parent orchestration of the AI worker subprocess.

Handles purpose sanitisation, prompt freeze verification, environment scrubbing,
worker subprocess lifecycle management with parent timeout killing, response schema
validation, retry on malformed JSON, and finding derivation via derive.py.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

from inspector.ai.derive import derive_ai_findings
from inspector.ai.worker import validate_endpoint_loopback
from segel_core.schemas.attestation import InspectFinding

__all__ = [
    "build_scrubbed_env",
    "load_prompt_template",
    "run_ai_worker",
    "sanitize_purpose",
    "validate_ai_response",
    "verify_prompt_freeze",
]

# Root of the SEGEL repository
REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_PROMPT_FILE = REPO_ROOT / "docs" / "evaluation" / "modelcheck_prompt.txt"
DEFAULT_FREEZE_FILE = REPO_ROOT / "docs" / "ai_prompt_freeze.txt"

FORBIDDEN_ENV_SUBSTRINGS = frozenset({
    "KEY",
    "TOKEN",
    "SECRET",
    "PRIVATE",
    "PASSWORD",
    "PASSWD",
    "CREDENTIAL",
})

ALLOWED_ENV_EXCEPTIONS = frozenset({"PATHEXT", "PYTHONPATH"})


def build_scrubbed_env(env: dict[str, str] | None = None) -> dict[str, str]:
    """Build a scrubbed execution environment for the AI worker subprocess.

    Retains only essential Windows/OS execution variables and strips any key,
    secret, token, credential, or private material per PRD v2.0 §7.5.

    Args:
        env: Environment dict to scrub, defaults to os.environ.

    Returns:
        Cleaned environment dictionary.
    """
    source_env = dict(os.environ if env is None else env)
    scrubbed: dict[str, str] = {}

    for k, v in source_env.items():
        k_upper = k.upper()
        # Check forbidden substrings unless explicitly whitelisted
        if k_upper not in ALLOWED_ENV_EXCEPTIONS and any(
            sub in k_upper for sub in FORBIDDEN_ENV_SUBSTRINGS
        ):
            continue

        scrubbed[k] = v

    # Ensure PYTHONPATH includes repo src directory so worker module can be found
    src_dir = str(REPO_ROOT / "src")
    existing_pythonpath = scrubbed.get("PYTHONPATH", "")
    if existing_pythonpath:
        if src_dir not in existing_pythonpath.split(os.pathsep):
            scrubbed["PYTHONPATH"] = f"{src_dir}{os.pathsep}{existing_pythonpath}"
    else:
        scrubbed["PYTHONPATH"] = src_dir

    return scrubbed


def sanitize_purpose(purpose: str | None) -> str:
    """Sanitise declared release purpose.

    Strips control characters, collapses whitespace sequences to single spaces,
    and caps length at 300 characters per PRD v2.0 §7.5.

    Args:
        purpose: Raw purpose string from release manifest.

    Returns:
        Sanitised purpose string.
    """
    if purpose is None:
        return ""
    text = str(purpose)
    # Strip ASCII and Unicode control characters (0x00-0x1F, 0x7F-0x9F)
    text = re.sub(r"[\x00-\x1f\x7f-\x9f]", "", text)
    # Collapse all whitespace sequences to a single space and strip edges
    text = re.sub(r"\s+", " ", text).strip()
    # Cap at 300 characters
    return text[:300].strip()


def verify_prompt_freeze(
    prompt_file_path: Path | str,
    freeze_file_path: Path | str,
) -> tuple[bool, str]:
    """Verify that runtime prompt template matches the frozen SHA-256 digest.

    Args:
        prompt_file_path: Path to modelcheck_prompt.txt.
        freeze_file_path: Path to ai_prompt_freeze.txt.

    Returns:
        Tuple of (is_valid, prompt_sha256).
    """
    p_file = Path(prompt_file_path)
    f_file = Path(freeze_file_path)

    if not p_file.exists() or not f_file.exists():
        return False, ""

    try:
        freeze_first_line = f_file.read_text(encoding="utf-8").strip().splitlines()[0]
        expected_digest = freeze_first_line.split()[0].strip().lower()

        # Normalize line endings to LF before hashing
        raw_prompt = p_file.read_bytes()
        norm_prompt = raw_prompt.replace(b"\r\n", b"\n")
        actual_digest = hashlib.sha256(norm_prompt).hexdigest().lower()

        return (actual_digest == expected_digest, actual_digest)
    except Exception:
        return False, ""


def load_prompt_template(prompt_file_path: Path | str) -> tuple[str, str]:
    """Parse modelcheck_prompt.txt into system prompt and user template."""
    p_file = Path(prompt_file_path)
    text = p_file.read_text(encoding="utf-8").replace("\r\n", "\n")

    sys_marker = "=== SYSTEM PROMPT ==="
    user_marker = "=== USER PROMPT TEMPLATE ==="

    if sys_marker not in text or user_marker not in text:
        raise ValueError(f"Prompt file missing section markers: {p_file}")

    parts = text.split(user_marker, 1)
    system_part = parts[0].replace(sys_marker, "").strip()
    user_part = parts[1].strip()

    return system_part, user_part


def validate_ai_response(content_str: str) -> tuple[bool, dict[str, Any] | None, str]:
    """Validate JSON response from Ollama against the expected schema.

    Enforces:
    - Valid JSON object
    - Exactly keys: 'purpose_class', 'ambiguous', 'reason' (no extra properties)
    - purpose_class in L1..L6
    - ambiguous is a boolean
    - reason is a string <= 160 characters

    Returns:
        Tuple of (is_valid, parsed_dict, error_code).
    """
    if not isinstance(content_str, str) or not content_str.strip():
        return False, None, "MALFORMED_JSON"

    try:
        parsed = json.loads(content_str)
    except Exception:
        return False, None, "MALFORMED_JSON"

    if not isinstance(parsed, dict):
        return False, None, "INVALID_SCHEMA"

    expected_keys = {"purpose_class", "ambiguous", "reason"}
    if set(parsed.keys()) != expected_keys:
        return False, None, "INVALID_SCHEMA"

    purpose_class = parsed.get("purpose_class")
    if purpose_class not in {"L1", "L2", "L3", "L4", "L5", "L6"}:
        return False, None, "INVALID_CLASS"

    ambiguous = parsed.get("ambiguous")
    if type(ambiguous) is not bool:
        return False, None, "INVALID_SCHEMA"

    reason = parsed.get("reason")
    if not isinstance(reason, str) or len(reason) > 160:
        return False, None, "INVALID_SCHEMA"

    return True, parsed, ""


def _invoke_worker_subprocess(
    worker_req: dict[str, Any],
    clean_env: dict[str, str],
    timeout_s: float,
) -> tuple[dict[str, Any] | None, str]:
    """Execute worker subprocess with parent-enforced timeout and tree kill."""
    proc = subprocess.Popen(
        [sys.executable, "-m", "inspector.ai.worker"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=clean_env,
        text=True,
    )

    try:
        # Give subprocess a slight buffer beyond worker internal timeout to avoid premature kill
        process_timeout = max(timeout_s + 5.0, 10.0)
        stdout_data, _ = proc.communicate(
            input=json.dumps(worker_req),
            timeout=process_timeout,
        )
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.communicate()
        return None, "TIMEOUT"

    if not stdout_data or not stdout_data.strip():
        return None, "WORKER_COMMUNICATION_FAILED"

    try:
        res = json.loads(stdout_data.strip())
        return res, ""
    except Exception:
        return None, "MALFORMED_JSON"


def run_ai_worker(
    purpose: str,
    capabilities: list[dict[str, Any]],
    endpoint: str = "http://127.0.0.1:11434",
    model: str = "qwen3:4b",
    timeout_s: float = 30.0,
    prompt_file: Path | str | None = None,
    freeze_file: Path | str | None = None,
) -> tuple[list[InspectFinding], str, str, str, str, str, str, str]:
    """Execute AI purpose analysis in an isolated worker subprocess.

    Args:
        purpose: Declared purpose string from manifest.
        capabilities: Detected capabilities in release candidate.
        endpoint: Loopback Ollama endpoint URL.
        model: AI model tag.
        timeout_s: Execution timeout in seconds.
        prompt_file: Path to prompt template file.
        freeze_file: Path to prompt freeze file.

    Returns:
        Tuple of (findings, ai_status, ai_error_code, ai_model_id,
        ai_model_digest, ai_prompt_digest, ai_class, ai_reason).
    """
    # 1. Loopback endpoint validation
    try:
        validate_endpoint_loopback(endpoint)
    except ValueError:
        return ([], "failed", "ENDPOINT_NOT_LOOPBACK", model, "", "", "", "")

    # 2. Verify prompt template against freeze file
    pf = Path(prompt_file) if prompt_file else DEFAULT_PROMPT_FILE
    ff = Path(freeze_file) if freeze_file else DEFAULT_FREEZE_FILE

    freeze_ok, prompt_digest = verify_prompt_freeze(pf, ff)
    if not freeze_ok:
        return ([], "failed", "PROMPT_FROZEN_MISMATCH", model, "", prompt_digest, "", "")

    # 3. Load prompt template
    try:
        system_prompt, user_template = load_prompt_template(pf)
    except Exception:
        return ([], "failed", "PROMPT_LOAD_ERROR", model, "", prompt_digest, "", "")

    # 4. Input builder: sanitise purpose and render prompt
    sanitized = sanitize_purpose(purpose)
    user_prompt = user_template.format(purpose=sanitized)

    # 5. Build scrubbed environment
    clean_env = build_scrubbed_env()

    worker_req = {
        "endpoint": endpoint,
        "model": model,
        "system_prompt": system_prompt,
        "user_prompt": user_prompt,
        "timeout_s": timeout_s,
    }

    # 6. Execute worker with at most 1 retry for malformed JSON / invalid schema
    max_attempts = 2
    last_err_code = "WORKER_ERROR"
    model_digest = ""

    for attempt in range(max_attempts):
        worker_res, proc_err = _invoke_worker_subprocess(worker_req, clean_env, timeout_s)
        if proc_err:
            return ([], "failed", proc_err, model, "", prompt_digest, "", "")

        if not worker_res:
            return ([], "failed", "WORKER_COMMUNICATION_FAILED", model, "", prompt_digest, "", "")

        model_digest = str(worker_res.get("model_digest") or "")

        if not worker_res.get("success"):
            err_code = str(worker_res.get("error_code") or "WORKER_ERROR")
            return ([], "failed", err_code, model, model_digest, prompt_digest, "", "")

        content = str(worker_res.get("content") or "")
        valid, parsed, val_err = validate_ai_response(content)

        if valid and parsed:
            purpose_class = str(parsed["purpose_class"])
            reason = str(parsed.get("reason", ""))
            findings = derive_ai_findings(purpose_class, capabilities)
            return (findings, "ok", "", model, model_digest, prompt_digest, purpose_class, reason)

        last_err_code = val_err
        # If schema or json was invalid, attempt retry once if attempt < max_attempts - 1
        if attempt < max_attempts - 1:
            continue

    return ([], "failed", last_err_code, model, model_digest, prompt_digest, "", "")
