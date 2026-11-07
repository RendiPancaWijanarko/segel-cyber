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

