# SPDX-License-Identifier: MIT
"""Unit and integration tests for the Release Desk FastAPI web application."""

import pytest
from fastapi.testclient import TestClient

from release_desk.app import app, demo


@pytest.fixture(autouse=True)
def reset_state():
    """Reset the demo state before each test."""
    demo.reset()
    yield
    demo.reset()


@pytest.fixture
def client():
    return TestClient(app)


def test_index_page(client):
    response = client.get("/")
    assert response.status_code == 200
    assert "SEGEL" in response.text
    assert "Release Desk" in response.text


def test_new_release_form(client):
    response = client.get("/release/new")
    assert response.status_code == 200
    assert "Create New Release" in response.text
    assert "release_id" in response.text


def test_trust_page(client):
    response = client.get("/trust")
    assert response.status_code == 200
    assert "Trust Root" in response.text
    assert "author" in response.text
    assert "approver" in response.text


def test_ledger_page(client):
    response = client.get("/ledger")
    assert response.status_code == 200
    assert "Transparency Ledger" in response.text


def test_create_release_and_view_detail(client):
    # Create a release
    form_data = {
        "release_id": "WEB-TEST-1",
        "sequence": "1",
        "purpose": "Web UI test release",
        "canary_targets": "canary-1,canary-2",
        "general_scope": "canary-1,canary-2,unit-3",
    }
    response = client.post("/release/create", data=form_data)
    assert response.status_code == 200
    assert "WEB-TEST-1" in response.text
    assert "CANDIDATE_RECORDED" in response.text

    # View release detail
    detail_res = client.get("/release/0")
    assert detail_res.status_code == 200
    assert "WEB-TEST-1" in detail_res.text

    # Check invalid release id
    bad_res = client.get("/release/999")
    assert bad_res.status_code == 404


def test_full_web_lifecycle_canary_and_promote(client):
    # Step 1: Create release
    form_data = {
        "release_id": "WEB-LIFECYCLE-1",
        "sequence": "1",
        "purpose": "Full lifecycle web test",
        "canary_targets": "canary-1,canary-2",
        "general_scope": "canary-1,canary-2,unit-3",
    }
    create_res = client.post("/release/create", data=form_data)
    assert create_res.status_code == 200

    # Step 2: Deploy to canary
    canary_res = client.post("/release/0/deploy-canary")
    assert canary_res.status_code == 200
    assert "CANARY_DEPLOYED" in canary_res.text

    # Step 3: Promote release
    promote_res = client.post("/release/0/promote")
    assert promote_res.status_code == 200
    assert "PROMOTED" in promote_res.text


def test_reset_endpoint(client):
    # Create release
    form_data = {
        "release_id": "RESET-TEST-1",
        "sequence": "1",
        "purpose": "Reset test",
        "canary_targets": "canary-1",
        "general_scope": "canary-1",
    }
    client.post("/release/create", data=form_data)
    assert len(demo.releases) == 1

    # Reset
    res = client.post("/reset")
    assert res.status_code == 200
    assert res.json() == {"status": "reset"}
    assert len(demo.releases) == 0


def test_healthz_endpoint(client):
    res = client.get("/healthz")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "healthy"
    assert data["service"] == "segel-release-desk"


def test_segel_endpoint(client):
    res = client.get("/segel")
    assert res.status_code == 200
    assert "SEGEL" in res.text or "Segel" in res.text
    assert "Keren nix" in res.text
    assert "Task Statistics" in res.text
    assert "Total Revenue" in res.text

    # Verify backward-compatible alias
    compat_res = client.get("/zassk")
    assert compat_res.status_code == 200


def test_favicon_endpoint(client):
    res = client.get("/favicon.ico")
    assert res.status_code == 200
    assert "image" in res.headers.get("content-type", "")


def test_webmanifest_endpoint(client):
    res = client.get("/site.webmanifest")
    assert res.status_code == 200
    assert "manifest" in res.headers.get("content-type", "") or "json" in res.headers.get("content-type", "")
    data = res.json()
    assert data["short_name"] == "SEGEL"


def test_dynamic_telemetry_metrics_empty(client):
    """Verify that an empty demo state renders genuine dynamic zero/empty metrics, not mock SaaS data."""
    res = client.get("/")
    assert res.status_code == 200
    # Obsolete mock placeholder strings must not be present
    assert "63k+" not in res.text
    assert "4,653 Paket" not in res.text
    assert "379 Paspor" not in res.text
    assert "653 Titik" not in res.text


def test_dynamic_telemetry_with_releases(client):
    """Verify dynamic metrics update after releases are created, canary deployed, and promoted."""
    form_data = {
        "release_id": "DYNAMIC-TEST-1",
        "sequence": "1",
        "purpose": "Telemetry test release",
        "canary_targets": "canary-1,canary-2",
        "general_scope": "canary-1,canary-2,unit-3",
    }
    client.post("/release/create", data=form_data)
    client.post("/release/0/deploy-canary")
    client.post("/release/0/promote")

    res = client.get("/")
    assert res.status_code == 200
    assert "DYNAMIC-TEST-1" in res.text


def test_create_release_uses_config_ai_enabled(monkeypatch, client):
    """Verify create_release passes config.ai_enabled to inspect_release."""
    from dataclasses import replace
    from release_desk import app as app_module

    called_with_ai = None
    original_inspect = app_module.inspect_release

    def spy_inspect(*args, **kwargs):
        nonlocal called_with_ai
        called_with_ai = kwargs.get("ai_enabled")
        # Ensure we don't actually hit network during test
        kwargs["ai_enabled"] = False
        return original_inspect(*args, **kwargs)

    monkeypatch.setattr(app_module, "inspect_release", spy_inspect)
    new_cfg = replace(app_module.config, ai_enabled=True)
    monkeypatch.setattr(app_module, "config", new_cfg)

    form_data = {
        "release_id": "AI-TEST-1",
        "sequence": "1",
        "purpose": "AI inspection test",
        "canary_targets": "canary-1",
        "general_scope": "canary-1",
    }
    client.post("/release/create", data=form_data)
    assert called_with_ai is True


def test_autopilot_page(client):
    """Verify automated demonstration autopilot route returns 200 with required elements."""
    res = client.get("/autopilot")
    assert res.status_code == 200
    assert "SEGEL" in res.text
    assert "Autopilot" in res.text or "Demonstrasi Otomatis" in res.text


def test_create_release_renders_valid_canary_and_promote_action(client):
    """Verify created release page renders valid non-empty indices for canary and promote forms."""
    form_data = {
        "release_id": "FORM-TEST-1",
        "sequence": "1",
        "purpose": "Form action test",
        "canary_targets": "canary-1,canary-2",
        "general_scope": "canary-1,canary-2,unit-3",
    }
    create_res = client.post("/release/create", data=form_data)
    assert create_res.status_code == 200
    assert "/release//deploy-canary" not in create_res.text
    assert "/release/0/deploy-canary" in create_res.text


def test_fallback_double_slash_canary_and_promote(client):
    """Verify fallback routes handle empty or double-slash index gracefully."""
    form_data = {
        "release_id": "FALLBACK-TEST-1",
        "sequence": "1",
        "purpose": "Fallback route test",
        "canary_targets": "canary-1,canary-2",
        "general_scope": "canary-1,canary-2,unit-3",
    }
    client.post("/release/create", data=form_data)

    # Fallback deploy-canary
    canary_res = client.post("/release//deploy-canary")
    assert canary_res.status_code == 200
    assert "CANARY_DEPLOYED" in canary_res.text

    # Fallback promote
    promote_res = client.post("/release//promote")
    assert promote_res.status_code == 200
    assert "PROMOTED" in promote_res.text





