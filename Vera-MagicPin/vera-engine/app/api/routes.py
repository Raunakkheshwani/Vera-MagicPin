import time

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from app.composer.evidence import build_evidence_bundle
from app.composer.llm_composer import compose_body
from app.composer.validators import validate_body
from app.engine.message_evolution import evolution_hint as build_evolution_hint
from app.engine.next_best_action import next_best_action
from app.engine.opportunity import score_opportunity
from app.models.api import (
    ContextPushRejected,
    ContextPushRequest,
    ContextsLoadedCount,
    HealthzResponse,
    MetadataResponse,
    ReplyRequest,
    ReplyResponse,
    TickAction,
    TickRequest,
    TickResponse,
    resolve_context_model,
)
from app.models.context import CategoryContext, CustomerContext, MerchantContext, TriggerContext
from app.state.context_store import ContextStore
from app.state.digital_twin import build_digital_twin
from app.state.engagement_store import EngagementStore
from config.settings import settings

router = APIRouter()

context_store = ContextStore()
engagement_store = EngagementStore()
_START_TIME = time.time()


@router.get("/v1/healthz", response_model=HealthzResponse)
async def healthz() -> HealthzResponse:
    counts = context_store.counts_loaded()
    return HealthzResponse(
        status="ok",
        uptime_seconds=int(time.time() - _START_TIME),
        contexts_loaded=ContextsLoadedCount(**counts),
    )


@router.get("/v1/metadata", response_model=MetadataResponse)
async def metadata() -> MetadataResponse:
    return MetadataResponse(
        team_name=settings.team_name,
        team_members=settings.team_members,
        model=settings.model_name,
        approach=settings.approach,
        contact_email=settings.contact_email,
        version=settings.version,
    )


@router.post("/v1/context")
async def push_context(request: Request):
    raw = await request.json()
    try:
        envelope = ContextPushRequest.model_validate(raw)
    except ValidationError as exc:
        return JSONResponse(status_code=400, content=ContextPushRejected(reason="invalid_scope", details=str(exc)).model_dump())

    model_cls = resolve_context_model(envelope.scope)
    try:
        model_cls.model_validate(envelope.payload)
    except ValidationError as exc:
        return JSONResponse(status_code=400, content=ContextPushRejected(reason="malformed_payload", details=str(exc)).model_dump())

    result = context_store.push(envelope.scope, envelope.context_id, envelope.version, envelope.payload)
    if not result.accepted:
        return JSONResponse(status_code=409, content=result.model_dump())
    return result.model_dump()


def _resolve_contexts(trigger_id: str):
    trigger_raw = context_store.get("trigger", trigger_id)
    if not trigger_raw:
        return None
    trigger = TriggerContext.model_validate(trigger_raw)

    merchant_raw = context_store.get("merchant", trigger.merchant_id)
    if not merchant_raw:
        return None
    merchant = MerchantContext.model_validate(merchant_raw)

    category_raw = context_store.get("category", merchant.category_slug)
    if not category_raw:
        return None
    category = CategoryContext.model_validate(category_raw)

    customer = None
    if trigger.customer_id:
        customer_raw = context_store.get("customer", trigger.customer_id)
        if customer_raw:
            customer = CustomerContext.model_validate(customer_raw)

    return trigger, merchant, category, customer


@router.post("/v1/tick", response_model=TickResponse)
async def tick(body: TickRequest) -> TickResponse:
    candidates = []
    for trigger_id in body.available_triggers:
        resolved = _resolve_contexts(trigger_id)
        if resolved is None:
            continue
        trigger, merchant, category, customer = resolved

        opp = score_opportunity(trigger, category, merchant, customer)
        if opp.suppress:
            continue
        if engagement_store.already_sent(opp.suppression_key):
            continue
        candidates.append((opp, merchant, category, customer))

    # Trigger arbitration: one action per merchant per tick, highest score wins
    best_by_merchant = {}
    for opp, merchant, category, customer in candidates:
        current = best_by_merchant.get(opp.merchant_id)
        if current is None or opp.score > current[0].score:
            best_by_merchant[opp.merchant_id] = (opp, merchant, category, customer)

    actions = []
    for opp, merchant, category, customer in best_by_merchant.values():
        fatigue = engagement_store.fatigue_for(opp.merchant_id)
        if not opp.bypass_fatigue and fatigue >= 0.8 and opp.urgency < 4:
            continue

        twin = build_digital_twin(merchant)
        action_name, cta_type, send_as = next_best_action(opp)
        evidence = build_evidence_bundle(opp, category, merchant, customer, twin=twin)
        customer_name = customer.identity.name if (customer and send_as == "merchant_on_behalf") else None

        attempt_number = engagement_store.bump_attempt(opp.merchant_id, opp.family)
        hint = build_evolution_hint(attempt_number, twin)

        body_text = compose_body(
            merchant_name=merchant.identity.name,
            category_tone=category.voice.tone,
            taboo_words=category.voice.vocab_taboo,
            action_name=action_name,
            why_now=opp.why_now,
            evidence=evidence,
            customer_name=customer_name,
            evolution_hint=hint,
        )
        ok, reason = validate_body(body_text, category.voice.vocab_taboo)
        if not ok:
            continue

        conversation_id = f"conv_{opp.merchant_id}_{opp.trigger_id}"
        first_outbound = not engagement_store.has_open_session(conversation_id)

        action = TickAction(
            conversation_id=conversation_id,
            merchant_id=opp.merchant_id,
            customer_id=opp.customer_id if send_as == "merchant_on_behalf" else None,
            send_as=send_as,
            trigger_id=opp.trigger_id,
            template_name=f"vera_{opp.family}_v1" if first_outbound else None,
            template_params=[merchant.identity.name] if first_outbound else [],
            body=body_text,
            cta=cta_type,
            suppression_key=opp.suppression_key,
            rationale="; ".join(opp.why_now) or f"{opp.family} opportunity, urgency={opp.urgency}",
        )
        actions.append(action)
        engagement_store.mark_sent(opp.suppression_key)
        engagement_store.record_send(opp.merchant_id)
        engagement_store.record_outbound(conversation_id, body_text)
        engagement_store.remember_opportunity(conversation_id, opp.family, opp.why_now, evidence)

    return TickResponse(actions=actions)


STOP_WORDS = ["stop", "unsubscribe", "not interested", "don't message", "no thanks", "remove me"]
HOSTILE_WORDS = ["scam", "fraud", "harassment", "angry", "sue you", "reported"]
COMMITMENT_WORDS = ["let's do it", "go ahead", "sounds good", "yes please", "sure, do it", "ok do it"]
AUTO_REPLY_SIGNS = ["currently unavailable", "will get back to you", "out of office", "auto-reply", "automatic reply"]


def _extract_merchant_and_family_from_conversation(conversation_id: str):
    # conversation_id format: conv_{merchant_id}_{trigger_id} — merchant_id itself
    # may contain underscores, so we recover it via the last stored opportunity instead.
    last_opp = engagement_store.get_last_opportunity(conversation_id)
    return last_opp["family"] if last_opp else None


@router.post("/v1/reply", response_model=ReplyResponse)
async def reply(body: ReplyRequest) -> ReplyResponse:
    msg = body.message.lower()

    if engagement_store.is_ended(body.conversation_id):
        return ReplyResponse(action="end", rationale="Conversation already ended/suppressed.")

    if any(w in msg for w in STOP_WORDS) or any(w in msg for w in HOSTILE_WORDS):
        engagement_store.end_conversation(body.conversation_id)
        family = _extract_merchant_and_family_from_conversation(body.conversation_id)
        if family:
            engagement_store.reset_attempts(body.merchant_id, family)
        return ReplyResponse(action="end", rationale="Explicit opt-out or hostile message detected. Ending gracefully.")

    if any(w in msg for w in AUTO_REPLY_SIGNS):
        count = engagement_store.bump_auto_reply(body.conversation_id)
        if count == 1:
            return ReplyResponse(action="wait", wait_seconds=14400, rationale="Detected auto-reply. Backing off 4 hours.")
        elif count == 2:
            return ReplyResponse(action="wait", wait_seconds=86400, rationale="Second auto-reply. Backing off 24 hours.")
        else:
            engagement_store.end_conversation(body.conversation_id)
            return ReplyResponse(action="end", rationale="Repeated auto-replies. Ending outreach.")

    if any(w in msg for w in COMMITMENT_WORDS):
        family = _extract_merchant_and_family_from_conversation(body.conversation_id)
        if family:
            engagement_store.reset_attempts(body.merchant_id, family)  # commitment resets evolution — no longer "ignored"
        reply_text = "Great — I'll get that moving right away and confirm once it's done."
        return ReplyResponse(action="send", body=reply_text, cta="binary_confirm_cancel",
                              rationale="Explicit commitment detected. Executing next step, not re-qualifying.")

    # Grounded default: pull the original opportunity's evidence rather than waiting blindly.
    last_opp = engagement_store.get_last_opportunity(body.conversation_id)
    if last_opp:
        follow_up = compose_body(
            merchant_name=body.merchant_id,
            category_tone="neutral, helpful",
            taboo_words=[],
            action_name=f"follow_up_on_{last_opp['family']}",
            why_now=last_opp["why_now"],
            evidence=last_opp["evidence"],
        )
        ok, _ = validate_body(follow_up, [])
        if ok:
            return ReplyResponse(action="send", body=follow_up, cta="open_ended",
                                  rationale=f"Grounded follow-up on the original {last_opp['family']} opportunity, no clear new intent yet.")

    return ReplyResponse(action="wait", wait_seconds=3600,
                          rationale="No clear intent signal and no prior opportunity context available; deferring rather than guessing.")