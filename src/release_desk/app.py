# SPDX-License-Identifier: MIT
"""Release Desk — FastAPI web application for release management.

This is the Release Desk (Zone Z3) — the untrusted web application that
orchestrates the release lifecycle. It NEVER holds private signing keys.
All signing happens in separate processes/devices.

Per PRD v2.0 §7.2:
- Provides a web UI for release creation and status tracking.
- Generates QR codes for air-gapped approval transfer.
- Orchestrates the pipeline: build → inspect → approve → record → deploy.
- Never performs cryptographic signing directly.
"""

from __future__ import annotations

import json
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Form, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from approver.approver import (
    approver_sign,
    collect_approvals,
    create_approval_payload,
)
from builder.builder import build_release_package, sign_manifest, sign_origin
from inspector.inspector import create_inspect_attestation, inspect_release, sign_inspect
from ledger.ledger import TransparencyLedger
from passport.assembler import build_candidate_passport, build_general_passport
from promotion.controller import CanaryReceipt, evaluate_promotion
from segel_core.config import load_config
from segel_core.crypto.ed25519 import KeyPair, export_public_key, generate_keypair
from segel_core.schemas.attestation import PromotionCriteria
from segel_core.schemas.passport import LedgerProof
from segel_core.schemas.trust import (
    KeyRecord,
    RoleThreshold,
    TrustRoot,
    TrustSnapshot,
    VerificationPolicy,
)
from segel_core.verification.trust import TrustContext
from witness.witness import Witness

# ── Application Setup ────────────────────────────────────────────────

config = load_config(auto_load_dotenv=True)

logger = logging.getLogger("segel.release_desk")
logging.basicConfig(
    level=getattr(logging, config.log_level.upper(), logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Application lifespan context manager for startup and graceful shutdown."""
    logger.info(
        "Starting SEGEL Release Desk in mode '%s' on %s:%d",
        config.mode,
        config.host,
        config.port,
    )
    logger.info(
        "Storage configuration: data_dir=%s, state_dir=%s, keys_dir=%s",
        config.data_dir,
        config.state_dir,
        config.keys_dir,
    )
    yield
    logger.info("Shutting down SEGEL Release Desk")
    if hasattr(demo, "ledger"):
        demo.ledger.close()


app = FastAPI(
    title="SEGEL Release Desk",
    description="Secure Configuration & Release Distribution Platform",
    version="0.1.0-mvp",
    lifespan=lifespan,
)


@app.get("/healthz")
async def healthz() -> dict[str, Any]:
    """Health and diagnostic endpoint for container and operational monitoring."""
    return {
        "status": "healthy",
        "service": "segel-release-desk",
        "mode": config.mode,
        "ledger_size": demo.ledger.size,
        "epoch": demo.snapshot.epoch,
    }

# Template directory
TEMPLATE_DIR = Path(__file__).parent / "templates"
TEMPLATE_DIR.mkdir(exist_ok=True)

templates = Jinja2Templates(directory=str(TEMPLATE_DIR))


# ── Synthetic Demo State (MVP) ───────────────────────────────────────
# In production, keys would be loaded from secure storage.
# For the MVP demo, we generate synthetic keys at startup.

class DemoState:
    """In-memory state for the MVP demo."""

    def __init__(self) -> None:
        self.reset()

    def reset(self) -> None:
        # Generate synthetic keys
        self.author_key = generate_keypair()
        self.builder_key = generate_keypair()
        self.inspector_key = generate_keypair()
        self.approver_keys = [generate_keypair() for _ in range(3)]
        self.ledger_key = generate_keypair()
        self.witness_key = generate_keypair()
        self.canary_keys = [generate_keypair() for _ in range(2)]
        self.general_receiver_key = generate_keypair()

        # Build trust root
        def kr(kp: KeyPair, role: str, group: str = "default") -> KeyRecord:
            return KeyRecord(
                key_id=kp.key_id,
                public_key_b64=export_public_key(kp.public_key_bytes),
                role=role, group=group,
            )

        self.trust_root = TrustRoot(
            root_version=1,
            keys=[
                kr(self.author_key, "author"),
                kr(self.builder_key, "builder"),
                kr(self.inspector_key, "inspector_signer"),
                kr(self.approver_keys[0], "approver", "group-0"),
                kr(self.approver_keys[1], "approver", "group-1"),
                kr(self.approver_keys[2], "approver", "group-0"),
                kr(self.ledger_key, "ledger"),
                kr(self.witness_key, "witness"),
                kr(self.canary_keys[0], "receiver"),
                kr(self.canary_keys[1], "receiver"),
                kr(self.general_receiver_key, "receiver"),
            ],
            roles=[
                RoleThreshold(role="author", threshold=1),
                RoleThreshold(role="builder", threshold=1),
                RoleThreshold(role="inspector_signer", threshold=1),
                RoleThreshold(role="approver", threshold=2,
                              group_minimums={"group-0": 1, "group-1": 1}),
                RoleThreshold(role="ledger", threshold=1),
                RoleThreshold(role="witness", threshold=1),
                RoleThreshold(role="receiver", threshold=1),
            ],
        )

        self.policy = VerificationPolicy(
            policy_version=1, approval_threshold=2,
            approval_groups={"group-0": 1, "group-1": 1},
            canary_required_count=2, witness_cosignature_count=1,
        )
        self.snapshot = TrustSnapshot(epoch=1)
        self.trust_ctx = TrustContext(
            root=self.trust_root, policy=self.policy, snapshot=self.snapshot,
        )

        # Infrastructure
        self.ledger = TransparencyLedger()
        self.witness = Witness(self.witness_key)

        # Release tracking
        self.releases: list[dict[str, Any]] = []
        self.current_release: dict[str, Any] | None = None


demo = DemoState()


# ── Routes ───────────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def index(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "releases": demo.releases,
            "ledger_size": demo.ledger.size,
        },
    )


@app.get("/release/new", response_class=HTMLResponse)
async def new_release_form(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(
        request=request,
        name="new_release.html",
        context={},
    )


@app.post("/release/create", response_class=HTMLResponse)
async def create_release(
    request: Request,
    release_id: str = Form(...),
    sequence: int = Form(...),
    purpose: str = Form(...),
    canary_targets: str = Form("canary-1,canary-2"),
    general_scope: str = Form("canary-1,canary-2,unit-3"),
) -> HTMLResponse:
    """Run the complete release pipeline: build → inspect → approve → record."""

    try:
        canary_list = [t.strip() for t in canary_targets.split(",") if t.strip()]
        scope_list = [t.strip() for t in general_scope.split(",") if t.strip()]

        # Demo configuration files
        app_cfg = (
            f"# Release {release_id}@{sequence}\n"
            f"server:\n  port: 8080\n  host: 0.0.0.0\n"
            f"purpose: {purpose}\n"
        ).encode()
        files = {
            "config/app.yaml": app_cfg,
            "config/logging.yaml": b"log_level: info\nlog_file: /var/log/app.log\n",
        }

        # Step 1-2: Build
        build_result = build_release_package(
            files=files, release_id=release_id, sequence=sequence,
            purpose=purpose, canary_targets=canary_list,
            general_scope=scope_list,
        )

        # Step 3: Author signs manifest
        manifest_env = sign_manifest(build_result, demo.author_key)

        # Step 4: Builder signs origin
        origin_env = sign_origin(build_result, demo.builder_key)

        # Step 5-7: Inspect
        inspection = inspect_release(
            files=files, manifest=build_result.manifest,
            manifest_digest=build_result.manifest_digest, ai_enabled=False,
        )
        inspect_stmt = create_inspect_attestation(
            inspection, build_result.manifest, build_result.manifest_digest,
        )
        inspect_env = sign_inspect(inspect_stmt, demo.inspector_key)

        # Step 8-9: Approve (2-of-3)
        approve_stmt, approve_req = create_approval_payload(
            build_result.manifest, build_result.manifest_digest,
            origin_env, inspect_env, inspection.verdict,
            canary_targets=canary_list,
            promotion_criteria=PromotionCriteria(
                required_healthy_canary_units=2,
                required_probes=["file_exists", "config_valid"],
            ),
        )

        responses = [
            approver_sign(approve_req, demo.approver_keys[0]),
            approver_sign(approve_req, demo.approver_keys[1]),
        ]
        approve_env = collect_approvals(approve_stmt, approve_req, responses)

        # Step 10: Record in ledger
        candidate_event = {
            "event_type": "candidate_recorded",
            "release_id": release_id,
            "sequence": sequence,
            "manifest_sha256": build_result.manifest_digest,
        }
        entry = demo.ledger.append("candidate_recorded", candidate_event)
        signed_cp = demo.ledger.sign_checkpoint(demo.ledger_key)

        # Witness cosign
        consistency_proof = None
        if demo.witness.state.last_checkpoint_size > 0:
            proof_hex = demo.ledger.consistency_proof(
                demo.witness.state.last_checkpoint_size,
                signed_cp.checkpoint.size,
            )
            consistency_proof = [bytes.fromhex(h) for h in proof_hex]
        cosig = demo.witness.cosign_checkpoint(
            signed_cp.checkpoint, consistency_proof=consistency_proof,
        )
        demo.ledger.add_witness_cosignature(
            signed_cp.checkpoint.size, demo.witness_key.key_id, cosig,
        )

        # Build candidate passport
        proof = demo.ledger.inclusion_proof(entry.index)
        ledger_proof = LedgerProof(
            event_type="candidate_recorded",
            entry_index=proof.entry_index,
            leaf_hash=proof.leaf_hash,
            inclusion_proof=proof.proof,
            checkpoint_size=proof.checkpoint_size,
            checkpoint_root_hash=proof.checkpoint_root_hash,
            checkpoint_signature=signed_cp.ledger_signature,
            witness_cosignatures=[cosig],
        )

        passport = build_candidate_passport(
            manifest_env, origin_env, inspect_env, approve_env,
            ledger_proof, signed_cp, min_epoch=1,
        )

        # Track release
        release_info = {
            "release_id": release_id,
            "sequence": sequence,
            "purpose": purpose,
            "status": "CANDIDATE_RECORDED",
            "verdict": inspection.verdict,
            "capabilities": len(inspection.capabilities),
            "findings": len(inspection.deterministic_findings),
            "approvals": 2,
            "ledger_index": entry.index,
            "passport_type": "candidate",
            "manifest_digest": build_result.manifest_digest[:16] + "...",
            "package_digest": build_result.package_digest[:16] + "...",
            "files": files,
            "build_result": build_result,
            "manifest_env": manifest_env,
            "origin_env": origin_env,
            "inspect_env": inspect_env,
            "approve_env": approve_env,
            "inspection": inspection,
            "passport": passport,
            "ledger_proof": ledger_proof,
            "signed_cp": signed_cp,
            "timestamp": datetime.now(UTC).isoformat(),
        }
        demo.releases.append(release_info)
        demo.current_release = release_info

        return templates.TemplateResponse(
            request=request,
            name="release_detail.html",
            context={
                "release": release_info,
                "success": True,
            },
        )

    except Exception as e:
        return templates.TemplateResponse(
            request=request,
            name="error.html",
            context={
                "error": str(e),
                "error_type": type(e).__name__,
            },
        )


@app.get("/release/{idx}", response_class=HTMLResponse)
async def release_detail(request: Request, idx: int) -> HTMLResponse:
    if idx < 0 or idx >= len(demo.releases):
        raise HTTPException(404, "Release not found")
    return templates.TemplateResponse(
        request=request,
        name="release_detail.html",
        context={
            "release": demo.releases[idx],
            "idx": idx,
        },
    )


@app.get("/ledger", response_class=HTMLResponse)
async def ledger_view(request: Request) -> HTMLResponse:
    entries = []
    for i in range(demo.ledger.size):
        e = demo.ledger.get_entry(i)
        if e:
            entries.append({
                "index": e.index,
                "event_type": e.event_type,
                "data_hex": e.data_hex[:16] + "...",
                "leaf_hash": e.leaf_hash[:16] + "...",
            })
    cp = demo.ledger.get_latest_checkpoint()
    return templates.TemplateResponse(
        request=request,
        name="ledger.html",
        context={
            "entries": entries,
            "checkpoint": cp,
            "root_hash": (
                demo.ledger.root_hash_hex()[:16] + "..."
                if demo.ledger.size > 0
                else "empty"
            ),
        },
    )


@app.get("/trust", response_class=HTMLResponse)
async def trust_view(request: Request) -> HTMLResponse:
    keys = []
    for kr in demo.trust_root.keys:
        keys.append({
            "key_id": kr.key_id[:16] + "...",
            "role": kr.role,
            "group": kr.group,
            "status": kr.status,
        })
    return templates.TemplateResponse(
        request=request,
        name="trust.html",
        context={
            "keys": keys,
            "root_version": demo.trust_root.root_version,
            "policy_version": demo.policy.policy_version,
            "epoch": demo.snapshot.epoch,
        },
    )


@app.post("/release/{idx}/deploy-canary", response_class=HTMLResponse)
async def deploy_canary(request: Request, idx: int) -> HTMLResponse:
    """Deploy a candidate release to canary units and collect health receipts."""
    if idx < 0 or idx >= len(demo.releases):
        raise HTTPException(404, "Release not found")

    release = demo.releases[idx]

    try:
        from receiver.receiver import Receiver, ReceiverState

        passport = release["passport"]
        files = release["files"]
        release["build_result"]
        canary_receipts = []
        canary_receipt_envelopes = []

        for i, (canary_key, unit_id) in enumerate(
            zip(demo.canary_keys, ["canary-1", "canary-2"], strict=False)
        ):
            import tempfile
            deploy_dir = Path(tempfile.mkdtemp(prefix=f"segel-canary-{i+1}-"))

            canary_state = ReceiverState(unit_id=unit_id, unit_role="canary")
            canary_receiver = Receiver(
                state=canary_state,
                trust_ctx=demo.trust_ctx,
                receiver_key=canary_key,
                deploy_root=deploy_dir / "config",
            )

            verification, receipt_env = canary_receiver.verify_and_deploy(
                passport=passport, files=files,
            )

            if receipt_env is None:
                raise ValueError(
                    f"Canary deployment failed for unit {unit_id}: "
                    f"eligibility={verification.eligibility.value}, "
                    f"reasons={verification.eligibility_reasons}"
                )

            receipt_payload = json.loads(receipt_env.get_payload_bytes())
            predicate = receipt_payload.get("predicate", {})

            canary_receipts.append(CanaryReceipt(
                unit_id=unit_id,
                overall_result=predicate["overall_result"],
                health_results=predicate.get("health_results", []),
                envelope=receipt_env,
            ))
            canary_receipt_envelopes.append(receipt_env)

        # Update release info
        release["canary_receipts"] = canary_receipts
        release["canary_receipt_envelopes"] = canary_receipt_envelopes
        release["status"] = "CANARY_DEPLOYED"

        return templates.TemplateResponse(
            request=request,
            name="release_detail.html",
            context={
                "release": release,
                "idx": idx,
                "canary_success": True,
            },
        )
    except Exception as e:
        return templates.TemplateResponse(
            request=request,
            name="error.html",
            context={
                "error": str(e),
                "error_type": type(e).__name__,
            },
        )


@app.post("/release/{idx}/promote", response_class=HTMLResponse)
async def promote_release(request: Request, idx: int) -> HTMLResponse:
    """Evaluate promotion criteria and promote release if criteria met."""
    if idx < 0 or idx >= len(demo.releases):
        raise HTTPException(404, "Release not found")

    release = demo.releases[idx]

    if "canary_receipts" not in release:
        return templates.TemplateResponse(
            request=request,
            name="error.html",
            context={
                "error": "Must deploy to canaries first",
                "error_type": "PipelineError",
            },
        )

    try:
        canary_receipts = release["canary_receipts"]
        canary_receipt_envelopes = release["canary_receipt_envelopes"]
        build_result = release["build_result"]

        # Evaluate promotion
        promotion_criteria = PromotionCriteria(
            required_healthy_canary_units=2,
            required_probes=["file_exists", "config_valid"],
        )
        promotion_result = evaluate_promotion(
            criteria=promotion_criteria, receipts=canary_receipts,
        )

        if not promotion_result.promoted:
            release["status"] = "PROMOTION_FAILED"
            release["promotion_reason"] = promotion_result.reason
            return templates.TemplateResponse(
                request=request,
                name="release_detail.html",
                context={
                    "release": release,
                    "idx": idx,
                    "promotion_failed": True,
                },
            )

        # Record promotion in ledger
        promotion_event = {
            "event_type": "release_promoted",
            "release_id": release["release_id"],
            "sequence": release["sequence"],
            "manifest_sha256": build_result.manifest_digest,
            "healthy_canary_units": promotion_result.healthy_units,
        }
        promotion_entry = demo.ledger.append("release_promoted", promotion_event)
        signed_cp2 = demo.ledger.sign_checkpoint(demo.ledger_key)

        # Witness cosign
        proof_hex2 = demo.ledger.consistency_proof(
            demo.witness.state.last_checkpoint_size,
            signed_cp2.checkpoint.size,
        )
        consistency_proof = [bytes.fromhex(h) for h in proof_hex2]
        cosig2 = demo.witness.cosign_checkpoint(
            signed_cp2.checkpoint, consistency_proof=consistency_proof,
        )
        demo.ledger.add_witness_cosignature(
            signed_cp2.checkpoint.size, demo.witness_key.key_id, cosig2,
        )

        # Build promotion proof
        promotion_proof_raw = demo.ledger.inclusion_proof(promotion_entry.index)
        promotion_proof = LedgerProof(
            event_type="release_promoted",
            entry_index=promotion_proof_raw.entry_index,
            leaf_hash=promotion_proof_raw.leaf_hash,
            inclusion_proof=promotion_proof_raw.proof,
            checkpoint_size=promotion_proof_raw.checkpoint_size,
            checkpoint_root_hash=promotion_proof_raw.checkpoint_root_hash,
            checkpoint_signature=signed_cp2.ledger_signature,
            witness_cosignatures=[cosig2],
        )

        # Build general passport
        general_passport = build_general_passport(
            release["manifest_env"], release["origin_env"],
            release["inspect_env"], release["approve_env"],
            release["ledger_proof"], canary_receipt_envelopes,
            promotion_proof, signed_cp2, min_epoch=1,
        )

        # Update release info
        release["status"] = "PROMOTED"
        release["passport_type"] = "general"
        release["passport"] = general_passport
        release["promotion_result"] = promotion_result
        release["promotion_proof"] = promotion_proof

        return templates.TemplateResponse(
            request=request,
            name="release_detail.html",
            context={
                "release": release,
                "idx": idx,
                "promotion_success": True,
            },
        )
    except Exception as e:
        return templates.TemplateResponse(
            request=request,
            name="error.html",
            context={
                "error": str(e),
                "error_type": type(e).__name__,
            },
        )


@app.post("/reset")
async def reset_demo() -> dict[str, str]:
    demo.reset()
    return {"status": "reset"}

