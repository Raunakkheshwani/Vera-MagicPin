"""
vera-engine/tests/test_api_models.py

Validates app/models/api.py against the exact worked examples in
examples/api-call-examples.md (Section "API Call Examples"). Unlike
test_context_models.py, these aren't loaded from a dataset JSON file —
they're transport examples documented inline in that markdown file — so
they're transcribed here directly, matching the doc verbatim.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.models.api import (
    CONTEXT_SCOPE_TO_MODEL,
    ContextPushAccepted,
    ContextPushRejected,
    ContextPushRequest,
    HealthzResponse,
    MetadataResponse,
    ReplyRequest,
    ReplyResponse,
    TickAction,
    TickRequest,
    TickResponse,
    resolve_context_model,
)
from app.models.context import CategoryContext, TriggerContext


# ---------------------------------------------------------------------------
# /v1/context — Examples 1.3, 1.5, 1.6
# ---------------------------------------------------------------------------

def test_context_push_request_category_scope():
    raw = {
        "scope": "category",
        "context_id": "dentists",
        "version": 1,
        "delivered_at": "2026-04-26T09:45:00Z",
        "payload": {
            "slug": "dentists",
            "voice": {"tone": "peer_clinical", "vocab_taboo": ["guaranteed", "100% safe"]},
            "offer_catalog": [],
            "peer_stats": {},
            "digest": [],
            "patient_content_library": [],
            "seasonal_beats": [],
            "trend_signals": [],
        },
    }
    req = ContextPushRequest.model_validate(raw)
    assert req.scope == "category"
    assert req.version == 1

    # Handler-level resolution: envelope tells us which domain model to use
    model_cls = resolve_context_model(req.scope)
    assert model_cls is CategoryContext
    domain_obj = model_cls.model_validate(req.payload)
    assert domain_obj.slug == "dentists"


def test_context_push_accepted_response_shape():
    resp = ContextPushAccepted(ack_id="ack_dentists_v1", stored_at="2026-04-26T09:45:00.123Z")
    assert resp.accepted is True


def test_context_push_stale_version_rejected_response_shape():
    """Example 1.5 — re-posting the same version."""
    resp = ContextPushRejected(reason="stale_version", current_version=1)
    assert resp.accepted is False
    assert resp.reason == "stale_version"


def test_context_push_version_must_be_at_least_1():
    raw = {"scope": "trigger", "context_id": "trg_001", "version": 0, "payload": {}}
    with pytest.raises(ValidationError):
        ContextPushRequest.model_validate(raw)


def test_resolve_context_model_covers_all_four_scopes():
    for scope in ("category", "merchant", "customer", "trigger"):
        assert scope in CONTEXT_SCOPE_TO_MODEL


# ---------------------------------------------------------------------------
# /v1/tick — Examples 2.1, 2.2, 2.3
# ---------------------------------------------------------------------------

def test_tick_request_shape():
    req = TickRequest.model_validate({
        "now": "2026-04-26T10:35:00Z",
        "available_triggers": ["trg_001_research_digest_dentists"],
    })
    assert req.available_triggers == ["trg_001_research_digest_dentists"]


def test_tick_action_matches_worked_example_2_2():
    """Transcribed from api-call-examples.md Example 2.2."""
    action = TickAction.model_validate({
        "conversation_id": "conv_m_001_drmeera_research_W17",
        "merchant_id": "m_001_drmeera_dentist_delhi",
        "customer_id": None,
        "send_as": "vera",
        "trigger_id": "trg_001_research_digest_dentists",
        "template_name": "vera_research_digest_v1",
        "template_params": ["Dr. Meera", "...", "..."],
        "body": "Dr. Meera, JIDA's Oct issue landed...",
        "cta": "open_ended",
        "suppression_key": "research:dentists:2026-W17",
        "rationale": "External research digest with merchant-relevant clinical anchor.",
    })
    assert action.send_as == "vera"
    assert action.customer_id is None


def test_tick_response_empty_actions_is_valid():
    """Example 2.3 — restraint (sending nothing) must be a valid response."""
    resp = TickResponse.model_validate({"actions": []})
    assert resp.actions == []


def test_tick_action_missing_required_field_rejected():
    """Testing brief: missing cta/suppression_key/rationale/etc. must fail validation."""
    raw = {
        "conversation_id": "conv_1",
        "merchant_id": "m_001",
        "send_as": "vera",
        "trigger_id": "trg_1",
        "body": "hello",
        "suppression_key": "key_1",
        "rationale": "because",
        # cta missing
    }
    with pytest.raises(ValidationError):
        TickAction.model_validate(raw)


def test_tick_action_empty_body_rejected():
    raw = {
        "conversation_id": "conv_1",
        "merchant_id": "m_001",
        "send_as": "vera",
        "trigger_id": "trg_1",
        "body": "",
        "cta": "open_ended",
        "suppression_key": "key_1",
        "rationale": "because",
    }
    with pytest.raises(ValidationError):
        TickAction.model_validate(raw)


def test_tick_action_merchant_on_behalf_requires_customer_id():
    raw = {
        "conversation_id": "conv_1",
        "merchant_id": "m_001",
        "customer_id": None,
        "send_as": "merchant_on_behalf",
        "trigger_id": "trg_1",
        "body": "hello",
        "cta": "open_ended",
        "suppression_key": "key_1",
        "rationale": "because",
    }
    with pytest.raises(ValidationError):
        TickAction.model_validate(raw)


# ---------------------------------------------------------------------------
# /v1/reply — Examples 2.4, 2.5, 2.6, 2.7
# ---------------------------------------------------------------------------

def test_reply_request_shape_matches_example_2_4():
    req = ReplyRequest.model_validate({
        "conversation_id": "conv_m_001_drmeera_research_W17",
        "merchant_id": "m_001_drmeera_dentist_delhi",
        "customer_id": None,
        "from_role": "merchant",
        "message": "Yes please send the abstract. Also draft the patient WhatsApp.",
        "received_at": "2026-04-26T10:42:00Z",
        "turn_number": 2,
    })
    assert req.from_role == "merchant"


def test_reply_response_send_shape_example_2_4():
    resp = ReplyResponse.model_validate({
        "action": "send",
        "body": "Sending the abstract now...",
        "cta": "binary_yes_no",
        "rationale": "Honoring both asks in one turn.",
    })
    assert resp.action == "send"


def test_reply_response_wait_shape_example_2_5():
    """Auto-reply detected — bot backs off 4 hours."""
    resp = ReplyResponse.model_validate({
        "action": "wait",
        "wait_seconds": 14400,
        "rationale": "Detected merchant auto-reply. Backing off 4 hours.",
    })
    assert resp.wait_seconds == 14400


def test_reply_response_end_shape_example_2_6():
    """Hard 'no' — bot ends gracefully."""
    resp = ReplyResponse.model_validate({
        "action": "end",
        "rationale": "Merchant explicitly opted out. Closing conversation.",
    })
    assert resp.body is None
    assert resp.wait_seconds is None


def test_reply_response_send_without_cta_rejected():
    with pytest.raises(ValidationError):
        ReplyResponse.model_validate({
            "action": "send",
            "body": "hello",
            "rationale": "because",
            # cta missing — invalid for action="send"
        })


def test_reply_response_wait_without_wait_seconds_rejected():
    with pytest.raises(ValidationError):
        ReplyResponse.model_validate({
            "action": "wait",
            "rationale": "because",
            # wait_seconds missing — invalid for action="wait"
        })


def test_reply_response_end_with_body_rejected():
    with pytest.raises(ValidationError):
        ReplyResponse.model_validate({
            "action": "end",
            "body": "this should not be here",
            "rationale": "because",
        })


# ---------------------------------------------------------------------------
# /v1/healthz — Examples 1.1, 1.7
# ---------------------------------------------------------------------------

def test_healthz_warmup_shape_example_1_1():
    resp = HealthzResponse.model_validate({
        "status": "ok",
        "uptime_seconds": 124,
        "contexts_loaded": {"category": 0, "merchant": 0, "customer": 0, "trigger": 0},
    })
    assert resp.contexts_loaded.category == 0


def test_healthz_post_warmup_shape_example_1_7():
    resp = HealthzResponse.model_validate({
        "status": "ok",
        "uptime_seconds": 1024,
        "contexts_loaded": {"category": 5, "merchant": 50, "customer": 200, "trigger": 0},
    })
    assert resp.contexts_loaded.merchant == 50


# ---------------------------------------------------------------------------
# /v1/metadata — Example 1.2
# ---------------------------------------------------------------------------

def test_metadata_shape_example_1_2():
    resp = MetadataResponse.model_validate({
        "team_name": "Team Alpha",
        "team_members": ["Alice", "Bob"],
        "model": "claude-opus-4-7",
        "approach": "single-prompt composer with retrieval over digest items",
        "contact_email": "team@example.com",
        "version": "1.2.0",
        "submitted_at": "2026-04-26T08:00:00Z",
    })
    assert resp.team_name == "Team Alpha"