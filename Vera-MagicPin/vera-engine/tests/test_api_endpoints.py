import pytest
from fastapi.testclient import TestClient

from app.api.routes import context_store
from app.main import app

client = TestClient(app)


@pytest.fixture(autouse=True)
def _reset_store():
    """Every test starts and ends with a clean context store."""
    context_store.clear()
    yield
    context_store.clear()


# ---------------------------------------------------------------------------
# /v1/healthz + /v1/metadata
# ---------------------------------------------------------------------------

def test_healthz_before_any_push_reports_zero_counts():
    resp = client.get("/v1/healthz")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["contexts_loaded"] == {"category": 0, "merchant": 0, "customer": 0, "trigger": 0}


def test_metadata_returns_configured_team_info():
    resp = client.get("/v1/metadata")
    assert resp.status_code == 200
    body = resp.json()
    assert "team_name" in body
    assert "approach" in body


# ---------------------------------------------------------------------------
# /v1/context
# ---------------------------------------------------------------------------

MINIMAL_CATEGORY_PAYLOAD = {
    "slug": "dentists",
    "voice": {"tone": "peer_clinical"},
}


def test_context_push_v1_accepted():
    resp = client.post("/v1/context", json={
        "scope": "category",
        "context_id": "dentists",
        "version": 1,
        "payload": MINIMAL_CATEGORY_PAYLOAD,
    })
    assert resp.status_code == 200
    assert resp.json()["accepted"] is True


def test_context_push_same_version_returns_409_stale():
    client.post("/v1/context", json={
        "scope": "category", "context_id": "dentists", "version": 1,
        "payload": MINIMAL_CATEGORY_PAYLOAD,
    })
    resp = client.post("/v1/context", json={
        "scope": "category", "context_id": "dentists", "version": 1,
        "payload": MINIMAL_CATEGORY_PAYLOAD,
    })
    assert resp.status_code == 409
    assert resp.json()["reason"] == "stale_version"


def test_context_push_higher_version_replaces():
    client.post("/v1/context", json={
        "scope": "category", "context_id": "dentists", "version": 1,
        "payload": MINIMAL_CATEGORY_PAYLOAD,
    })
    resp = client.post("/v1/context", json={
        "scope": "category", "context_id": "dentists", "version": 2,
        "payload": {"slug": "dentists", "voice": {"tone": "peer_clinical"}, "digest": []},
    })
    assert resp.status_code == 200
    assert resp.json()["accepted"] is True


def test_context_push_invalid_scope_returns_400():
    resp = client.post("/v1/context", json={
        "scope": "not_a_real_scope",
        "context_id": "x",
        "version": 1,
        "payload": {},
    })
    assert resp.status_code == 400
    assert resp.json()["accepted"] is False


def test_context_push_malformed_payload_returns_400():
    """Category payload missing required `voice` field."""
    resp = client.post("/v1/context", json={
        "scope": "category",
        "context_id": "dentists",
        "version": 1,
        "payload": {"slug": "dentists"},  # voice missing
    })
    assert resp.status_code == 400
    assert resp.json()["reason"] == "malformed_payload"


def test_healthz_reflects_pushed_context_counts():
    client.post("/v1/context", json={
        "scope": "category", "context_id": "dentists", "version": 1,
        "payload": MINIMAL_CATEGORY_PAYLOAD,
    })
    resp = client.get("/v1/healthz")
    assert resp.json()["contexts_loaded"]["category"] == 1


# ---------------------------------------------------------------------------
# /v1/tick + /v1/reply
# ---------------------------------------------------------------------------

def test_tick_with_no_triggers_returns_empty_actions():
    resp = client.post("/v1/tick", json={"now": "2026-04-26T10:35:00Z", "available_triggers": []})
    assert resp.status_code == 200
    assert resp.json()["actions"] == []


def test_reply_with_no_keyword_match_and_no_prior_context_waits_3600():
    """
    /v1/reply's real logic: an ambiguous message with no stop/hostile/
    auto-reply/commitment keywords AND no prior opportunity stored for
    this conversation (nothing was ever sent via /v1/tick here) falls
    through to the honest default — wait, don't fabricate a reply.
    """
    resp = client.post("/v1/reply", json={
        "conversation_id": "conv_never_ticked",
        "merchant_id": "m_001",
        "from_role": "merchant",
        "message": "hello",
        "received_at": "2026-04-26T10:42:00Z",
        "turn_number": 1,
    })
    assert resp.status_code == 200
    body = resp.json()
    assert body["action"] == "wait"
    assert body["wait_seconds"] == 3600