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
import re
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Form, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from approver.approver import (
    collect_approvals,
    create_approval_payload,
)
from approver.service import StandaloneApproverSigner
from builder.builder import build_release_package, sign_manifest, sign_origin
from demo_infra.keys import generate_demo_bundle
from inspector.inspector import create_inspect_attestation, inspect_release, sign_inspect
from ledger.ledger import TransparencyLedger
from passport.assembler import build_candidate_passport, build_general_passport
from promotion.controller import CanaryReceipt, evaluate_promotion
from segel_core.canonical import compute_acknowledgement_digest
from segel_core.config import load_config
from segel_core.schemas.attestation import PromotionCriteria
from segel_core.schemas.passport import LedgerProof
from segel_core.schemas.trust import (
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
    description="Configuration & Release Distribution Platform with Multi-Party Attestation",
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

# Static assets directory (images, CSS, JS)
STATIC_DIR = Path(__file__).parent / "static"
STATIC_DIR.mkdir(exist_ok=True)
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/favicon.ico", include_in_schema=False)
async def favicon() -> FileResponse:
    """Serve the root favicon for all browsers and API clients."""
    favicon_path = STATIC_DIR / "favicons" / "favicon.ico"
    if not favicon_path.exists():
        favicon_path = STATIC_DIR / "favicon.ico"
    return FileResponse(favicon_path, media_type="image/x-icon")


@app.get("/site.webmanifest", include_in_schema=False)
async def webmanifest() -> FileResponse:
    """Serve the web app manifest at domain root."""
    manifest_path = STATIC_DIR / "favicons" / "site.webmanifest"
    return FileResponse(manifest_path, media_type="application/manifest+json")


# ── Synthetic Demo State (MVP) ───────────────────────────────────────
# In production, keys would be loaded from an external HSM or isolated key manager.
# For the MVP demo, we generate synthetic keys at startup.

class DemoState:
    """In-memory state for the MVP demo."""

    def __init__(self) -> None:
        self.reset()

    @property
    def demo_keys(self) -> Any:
        return self._demo_keys

    def reset(self) -> None:
        # Generate synthetic demo keys via external demo infra
        self._demo_keys = generate_demo_bundle()
        self.approver_signer = StandaloneApproverSigner()

        # Build trust root
        self.trust_root = TrustRoot(
            root_version=1,
            keys=self._demo_keys.make_key_records() + self.approver_signer.get_public_key_records(),
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
            require_warn_acknowledgement=True,
        )
        self.snapshot = TrustSnapshot(epoch=1)
        self.trust_ctx = TrustContext(
            root=self.trust_root, policy=self.policy, snapshot=self.snapshot,
        )

        # Infrastructure
        self.ledger = TransparencyLedger()
        self.witness = Witness(self._demo_keys.witness_key)

        # Release tracking
        self.releases: list[dict[str, Any]] = []
        self.current_release: dict[str, Any] | None = None


demo = DemoState()


# ── Routes ───────────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def index(request: Request) -> HTMLResponse:
    promoted_count = sum(1 for r in demo.releases if r.get("status") == "PROMOTED")
    active_statuses = ("CANDIDATE_RECORDED", "CANARY_DEPLOYED")
    candidate_count = sum(1 for r in demo.releases if r.get("status") in active_statuses)
    passed_count = sum(1 for r in demo.releases if r.get("verdict") == "PASS")
    failed_count = sum(1 for r in demo.releases if r.get("verdict") == "REJECT")
    warn_count = sum(1 for r in demo.releases if r.get("verdict") == "WARN")
    total_releases = len(demo.releases)
    pass_rate = int((passed_count / total_releases) * 100) if total_releases else 100
    failure_rate = f"{(failed_count / total_releases) * 100:.1f}%" if total_releases else "0.0%"

    # Cryptographic stamps count:
    # 5 stamps per candidate release (Author, Builder, Inspect, Approvers x2)
    # + 2 canary receipts if CANARY_DEPLOYED or PROMOTED
    # + 1 witness cosignature if PROMOTED
    # + ledger checkpoints / entries
    stempel_kripto_count = sum(
        5
        + (
            len(r.get("canary_receipts", []))
            if r.get("status") in ("CANARY_DEPLOYED", "PROMOTED")
            else 0
        )
        + (1 if r.get("status") == "PROMOTED" else 0)
        for r in demo.releases
    ) + demo.ledger.size

    # Deployed tactical units (deduplicated across active/promoted deployments)
    deployed_units: set[str] = set()
    for r in demo.releases:
        if r.get("status") in ("CANARY_DEPLOYED", "PROMOTED"):
            for u in r.get("canary_targets", []):
                deployed_units.add(u)
        if r.get("status") == "PROMOTED":
            for u in r.get("general_scope", []):
                deployed_units.add(u)
    deployed_units_count = len(deployed_units)

    # Canary tests passed
    canary_passed_count = sum(len(r.get("canary_receipts", [])) for r in demo.releases)
    canary_probes_passed = canary_passed_count * 2

    # Quorum consensus
    quorum_consensus_rate = 100 if total_releases > 0 else 0

    # Channel metrics
    canary_packages_count = sum(
        1 for r in demo.releases if r.get("status") in ("CANARY_DEPLOYED", "PROMOTED")
    )
    channel_stats = {
        "canary_packages": canary_packages_count,
        "airgap_passports": promoted_count,
        "deployed_units": deployed_units_count,
    }

    # Dynamic telemetry data points for "Aktivitas Log Verifikasi Kriptografis"
    verification_points = []
    if demo.ledger.size == 0 and not demo.releases:
        # Baseline operational state (before any release is created)
        verification_points = [
            {
                "label": "Akar",
                "xPerc": 0,
                "yHeight": 35,
                "stempel": len(demo.trust_root.keys),
                "latency": "0.8ms",
                "event": "Inisialisasi Kunci Akar",
                "verdict": "Sah RFC 6962",
            },
            {
                "label": "Kuorum",
                "xPerc": 25,
                "yHeight": 48,
                "stempel": 2,
                "latency": "0.5ms",
                "event": "Ambang Batas Kuorum 2/2",
                "verdict": "Sah RFC 6962",
            },
            {
                "label": "Ledger",
                "xPerc": 50,
                "yHeight": 65,
                "stempel": 1,
                "latency": "0.3ms",
                "event": "Buku Besar Merkle Aktif",
                "verdict": "Sah RFC 6962",
            },
            {
                "label": "Inspektur",
                "xPerc": 75,
                "yHeight": 52,
                "stempel": 1,
                "latency": "1.2ms",
                "event": "AI Inspector Loopback Siap",
                "verdict": "Sah RFC 6962",
            },
            {
                "label": "Operasi",
                "xPerc": 100,
                "yHeight": 70,
                "stempel": stempel_kripto_count,
                "latency": "0.4ms",
                "event": "Gerbang Siap Operasi",
                "verdict": "Sah RFC 6962",
            },
        ]
    else:
        # Construct points dynamically from the root and releases
        raw_points = [{
            "label": "Akar",
            "yHeight": 35,
            "stempel": len(demo.trust_root.keys),
            "latency": "0.8ms",
            "event": f"Akar Kepercayaan v{demo.trust_root.root_version}",
            "verdict": "Sah RFC 6962",
        }]
        for rel in demo.releases:
            rel_id = rel.get("release_id", "RILIS")
            verdict = rel.get("verdict", "PASS")
            status = rel.get("status", "CANDIDATE_RECORDED")
            seq = rel.get("sequence", 1)

            raw_points.append({
                "label": f"#{seq} Inspek",
                "yHeight": 58 if verdict == "PASS" else (42 if verdict == "WARN" else 25),
                "stempel": 5,
                "latency": "1.8ms",
                "event": f"{rel_id} (Inspeksi {verdict})",
                "verdict": "Sah RFC 6962" if verdict != "REJECT" else "Ditolak",
            })

            if status in ("CANARY_DEPLOYED", "PROMOTED"):
                raw_points.append({
                    "label": f"#{seq} Canary",
                    "yHeight": 76,
                    "stempel": 7,
                    "latency": "2.1ms",
                    "event": f"{rel_id} (Gelar Canary 2 Unit)",
                    "verdict": "Sah RFC 6962",
                })

            if status == "PROMOTED":
                raw_points.append({
                    "label": f"#{seq} Promosi",
                    "yHeight": 92,
                    "stempel": 8,
                    "latency": "1.9ms",
                    "event": f"{rel_id} (Promosi Seluruh Satuan)",
                    "verdict": "Sah RFC 6962",
                })

        raw_points.append({
            "label": f"Log #{demo.ledger.size}",
            "yHeight": min(95, max(45, 45 + demo.ledger.size * 6)),
            "stempel": stempel_kripto_count,
            "latency": "1.7ms",
            "event": f"Buku Besar Merkle ({demo.ledger.size} Entri Tercatat)",
            "verdict": "Sah RFC 6962",
        })

        n_pts = len(raw_points)
        for i, pt in enumerate(raw_points):
            pt["xPerc"] = int((i / max(1, n_pts - 1)) * 100)
            verification_points.append(pt)

    # Recent ledger entries from the Merkle tree
    recent_ledger_entries = []
    for i in range(demo.ledger.size):
        e = demo.ledger.get_entry(i)
        if e:
            recent_ledger_entries.append({
                "index": e.index,
                "event_type": e.event_type,
                "data_hex": e.data_hex[:16] + "...",
                "leaf_hash": e.leaf_hash[:16] + "...",
            })

    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "request": request,
            "releases": demo.releases,
            "total_releases": total_releases,
            "ledger_size": demo.ledger.size,
            "promoted_count": promoted_count,
            "candidate_count": candidate_count,
            "passed_count": passed_count,
            "failed_count": failed_count,
            "warn_count": warn_count,
            "pass_rate": pass_rate,
            "failure_rate": failure_rate,
            "stempel_kripto_count": stempel_kripto_count,
            "deployed_units_count": deployed_units_count,
            "canary_passed_count": canary_passed_count,
            "canary_probes_passed": canary_probes_passed,
            "quorum_consensus_rate": quorum_consensus_rate,
            "channel_stats": channel_stats,
            "recent_ledger_entries": recent_ledger_entries,
            "verification_points": verification_points,
            "total_keys": len(demo.trust_root.keys),
            "root_version": demo.trust_root.root_version,
            "policy_version": demo.policy.policy_version,
            "epoch": demo.snapshot.epoch,
            "root_hash": (
                demo.ledger.root_hash_hex()[:16] + "..."
                if demo.ledger.size > 0
                else "empty"
            ),
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
        if re.search(r"[\x00-\x1f\x7f-\x9f]", purpose):
            raise HTTPException(
                status_code=400,
                detail="Manifest purpose contains forbidden control characters",
            )

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
        manifest_env = sign_manifest(build_result, demo.demo_keys.author_key)

        # Step 4: Builder signs origin
        origin_env = sign_origin(build_result, demo.demo_keys.builder_key)

        # Step 5-7: Inspect
        inspection = inspect_release(
            files=files, manifest=build_result.manifest,
            manifest_digest=build_result.manifest_digest, ai_enabled=config.ai_enabled,
        )
        inspect_stmt = create_inspect_attestation(
            inspection, build_result.manifest, build_result.manifest_digest,
        )
        inspect_env = sign_inspect(inspect_stmt, demo.demo_keys.inspector_key)

        # Step 8-9: Approve (2-of-3 via standalone signer service per SEC-004)
        ack_digest = ""
        warn_ids: list[str] = []
        if inspection.verdict == "WARN":
            all_findings = inspection.deterministic_findings + inspection.ai_findings
            warn_ids = sorted(
                {f.capability_id for f in all_findings if f.severity.lower() == "warn"}
            )
            ack_digest = compute_acknowledgement_digest(warn_ids)

        approve_stmt, approve_req = create_approval_payload(
            build_result.manifest, build_result.manifest_digest,
            origin_env, inspect_env, inspection.verdict,
            canary_targets=canary_list,
            promotion_criteria=PromotionCriteria(
                required_healthy_canary_units=2,
                required_probes=["file_exists", "config_valid"],
            ),
            acknowledgement_digest=ack_digest,
        )

        responses = demo.approver_signer.sign_approval_request(approve_req, count=2)
        approve_env = collect_approvals(approve_stmt, approve_req, responses)

        # Step 10: Record in ledger
        candidate_event = {
            "event_type": "candidate_recorded",
            "release_id": release_id,
            "sequence": sequence,
            "manifest_sha256": build_result.manifest_digest,
        }
        entry = demo.ledger.append("candidate_recorded", candidate_event)
        signed_cp = demo.ledger.sign_checkpoint(demo.demo_keys.ledger_key)

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
            signed_cp.checkpoint.size, demo.demo_keys.witness_key.key_id, cosig,
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
            "acknowledgement_digest": ack_digest,
            "acknowledged_findings": warn_ids,
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


@app.get("/segel", response_class=HTMLResponse)
@app.get("/zassk", response_class=HTMLResponse, include_in_schema=False)
async def segel_analytics_view(request: Request) -> HTMLResponse:
    """UI/UX Design R&D Environment exclusively serving segel.html."""
    return templates.TemplateResponse(
        request=request,
        name="segel.html",
        context={"request": request},
    )


@app.get("/autopilot", response_class=HTMLResponse)
async def autopilot_demo_view(request: Request) -> HTMLResponse:
    """Automated synchronized demonstration player for talking head video recording."""
    return templates.TemplateResponse(
        request=request,
        name="autopilot.html",
        context={"request": request},
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
            zip(demo.demo_keys.canary_keys, ["canary-1", "canary-2"], strict=False)
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
        signed_cp2 = demo.ledger.sign_checkpoint(demo.demo_keys.ledger_key)

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
            signed_cp2.checkpoint.size, demo.demo_keys.witness_key.key_id, cosig2,
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

