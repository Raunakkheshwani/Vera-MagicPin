"""
vera-engine/app/models/api.py

Official API ENVELOPE models — the wire contract for the 5 endpoints:
    POST /v1/context
    POST /v1/tick
    POST /v1/reply
    GET  /v1/healthz
    GET  /v1/metadata

This is deliberately a SEPARATE file from app/models/context.py.
context.py = what a CategoryContext/MerchantContext/TriggerContext/
CustomerContext looks like (the domain objects).
api.py = the request/response shapes the judge actually sends and expects
(the transport envelope). A context object travels INSIDE a
ContextPushRequest.payload — it is not the same thing as the envelope
around it.

Source of truth for every shape below: challenge-testing-brief.md
(§2, the contract + reference skeleton) and examples/api-call-examples.md
(the worked request/response pairs), cross-checked against each other.
"""

from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional, Type

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.context import (
    CategoryContext,
    CustomerContext,
    MerchantContext,
    TriggerContext,
)

ContextScope = Literal["category", "merchant", "customer", "trigger"]


# ---------------------------------------------------------------------------
# POST /v1/context
# ---------------------------------------------------------------------------

class ContextPushRequest(BaseModel):
    """
    The envelope the judge POSTs for every context push, regardless of
    scope. `payload` is intentionally `Dict[str, Any]` here, NOT one of
    the four typed context models — the envelope doesn't know in advance
    which shape it's carrying; that's resolved by `scope` at the handler
    level via `resolve_context_model()` below. Keeping the envelope and
    the payload's domain type decoupled means a malformed envelope
    (missing `version`, bad `scope` string) fails independently of
    whether the payload itself is well-formed.
    """
    model_config = ConfigDict(extra="allow")

    scope: ContextScope
    context_id: str
    version: int = Field(ge=1)
    payload: Dict[str, Any]
    delivered_at: Optional[str] = None


# Maps an envelope's `scope` to the domain model that should validate
# its `payload`. Used by the /v1/context route handler, e.g.:
#   model_cls = resolve_context_model(body.scope)
#   validated = model_cls.model_validate(body.payload)
CONTEXT_SCOPE_TO_MODEL: Dict[ContextScope, Type[BaseModel]] = {
    "category": CategoryContext,
    "merchant": MerchantContext,
    "customer": CustomerContext,
    "trigger": TriggerContext,
}


def resolve_context_model(scope: ContextScope) -> Type[BaseModel]:
    """Look up which domain model validates a given scope's payload."""
    return CONTEXT_SCOPE_TO_MODEL[scope]


class ContextPushAccepted(BaseModel):
    """200 response — version accepted and stored/replaced."""
    accepted: Literal[True] = True
    ack_id: str
    stored_at: str


class ContextPushRejected(BaseModel):
    """
    409 (stale_version) or 400 (invalid_scope / malformed) response.
    `current_version` only applies to the stale_version case;
    `details` only applies to malformed-payload cases.
    """
    accepted: Literal[False] = False
    reason: str
    current_version: Optional[int] = None
    details: Optional[str] = None


# ---------------------------------------------------------------------------
# POST /v1/tick
# ---------------------------------------------------------------------------

class TickRequest(BaseModel):
    model_config = ConfigDict(extra="allow")

    now: str
    available_triggers: List[str] = Field(default_factory=list)


class TickAction(BaseModel):
    """
    One action our bot returns from /v1/tick.

    Fields marked required below are exactly the ones the testing brief
    calls out by name: "Missing required action fields such as
    conversation_id, send_as, trigger_id, cta, suppression_key or
    rationale causes the action to score zero and incurs a
    malformed-response penalty." `body` is also enforced non-empty here
    because "Empty body on send" is separately listed as a penalty case.
    """
    model_config = ConfigDict(extra="allow")

    conversation_id: str
    merchant_id: str
    customer_id: Optional[str] = None
    send_as: Literal["vera", "merchant_on_behalf"]
    trigger_id: str
    template_name: Optional[str] = None
    template_params: List[str] = Field(default_factory=list)
    body: str = Field(min_length=1)
    cta: str
    suppression_key: str
    rationale: str

    @model_validator(mode="after")
    def _merchant_on_behalf_requires_customer(self) -> "TickAction":
        """
        A message sent "merchant_on_behalf" is by definition addressed to
        a customer (see engagement-design.md / the Creative Differentiators
        doc's merchant-facing vs customer-facing split). Catches a real
        bug class early: composing a customer-facing message without
        actually attaching which customer it's for.
        """
        if self.send_as == "merchant_on_behalf" and not self.customer_id:
            raise ValueError(
                "send_as == 'merchant_on_behalf' requires a non-null customer_id"
            )
        return self


class TickResponse(BaseModel):
    """
    Empty `actions` is explicitly valid and desired when restraint is the
    right call ("Empty actions is valid. Restraint is rewarded; spam is
    penalized." — api-call-examples.md Example 2.3).
    """
    actions: List[TickAction] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# POST /v1/reply
# ---------------------------------------------------------------------------

class ReplyRequest(BaseModel):
    model_config = ConfigDict(extra="allow")

    conversation_id: str
    merchant_id: str
    customer_id: Optional[str] = None
    from_role: Literal["merchant", "customer"]
    message: str
    received_at: str
    turn_number: int


class ReplyResponse(BaseModel):
    """
    Shape varies by `action` — enforced below rather than left to the
    composer to remember:
      - "send": body + cta required, wait_seconds must be absent
      - "wait": wait_seconds required, body/cta must be absent
      - "end":  body/cta/wait_seconds must all be absent
    `rationale` is required in every example regardless of action.
    """
    model_config = ConfigDict(extra="allow")

    action: Literal["send", "wait", "end"]
    body: Optional[str] = None
    cta: Optional[str] = None
    wait_seconds: Optional[int] = None
    rationale: str

    @model_validator(mode="after")
    def _shape_matches_action(self) -> "ReplyResponse":
        if self.action == "send":
            if not self.body or not self.cta:
                raise ValueError("action == 'send' requires both body and cta")
            if self.wait_seconds is not None:
                raise ValueError("action == 'send' must not set wait_seconds")
        elif self.action == "wait":
            if self.wait_seconds is None:
                raise ValueError("action == 'wait' requires wait_seconds")
            if self.body is not None or self.cta is not None:
                raise ValueError("action == 'wait' must not set body/cta")
        elif self.action == "end":
            if self.body is not None or self.cta is not None or self.wait_seconds is not None:
                raise ValueError("action == 'end' must not set body/cta/wait_seconds")
        return self


# ---------------------------------------------------------------------------
# GET /v1/healthz
# ---------------------------------------------------------------------------

class ContextsLoadedCount(BaseModel):
    category: int = 0
    merchant: int = 0
    customer: int = 0
    trigger: int = 0


class HealthzResponse(BaseModel):
    status: Literal["ok"]
    uptime_seconds: int
    contexts_loaded: ContextsLoadedCount


# ---------------------------------------------------------------------------
# GET /v1/metadata
# ---------------------------------------------------------------------------

class MetadataResponse(BaseModel):
    model_config = ConfigDict(extra="allow")

    team_name: str
    team_members: List[str] = Field(default_factory=list)
    model: str
    approach: str
    contact_email: str
    version: str
    submitted_at: Optional[str] = None