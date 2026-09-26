from __future__ import annotations

"""
bot.py — Vera Engine Submission Module

Exposes the canonical `compose(...)` function as required by challenge-brief.md §7.1.
"""
import os

from typing import Any, Dict, Optional

from app.composer.evidence import build_evidence_bundle
from app.composer.llm_composer import compose_body
from app.composer.validators import validate_body
from app.engine.next_best_action import next_best_action
from app.engine.opportunity import score_opportunity
from app.models.context import (
    CategoryContext,
    CustomerContext,
    MerchantContext,
    TriggerContext,
)
from app.state.digital_twin import build_digital_twin


def compose(
    category: Dict[str, Any],
    merchant: Dict[str, Any],
    trigger: Dict[str, Any],
    customer: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Inputs are raw dicts loaded from context JSONs.
    Returns dict with keys: body, cta, send_as, suppression_key, rationale.
    """
    category_ctx = CategoryContext.model_validate(category)
    merchant_ctx = MerchantContext.model_validate(merchant)
    trigger_ctx = TriggerContext.model_validate(trigger)
    customer_ctx = CustomerContext.model_validate(customer) if customer else None

    opp = score_opportunity(trigger_ctx, category_ctx, merchant_ctx, customer_ctx)

    if opp.suppress:
        return {
            "body": "",
            "cta": "none",
            "send_as": "vera",
            "suppression_key": opp.suppression_key,
            "rationale": opp.suppress_reason or "Opportunity suppressed",
        }

    action_name, cta_type, send_as = next_best_action(opp)
    twin = build_digital_twin(merchant_ctx)
    evidence = build_evidence_bundle(opp, category_ctx, merchant_ctx, customer_ctx, twin=twin)
    customer_name = customer_ctx.identity.name if (customer_ctx and send_as == "merchant_on_behalf") else None

    body_text = compose_body(
        merchant_name=merchant_ctx.identity.name,
        category_tone=category_ctx.voice.tone,
        taboo_words=category_ctx.voice.vocab_taboo,
        action_name=action_name,
        why_now=opp.why_now,
        evidence=evidence,
        customer_name=customer_name,
    )

    ok, reason = validate_body(body_text, category_ctx.voice.vocab_taboo)
    if not ok:
        return {
            "body": "",
            "cta": "none",
            "send_as": send_as,
            "suppression_key": opp.suppression_key,
            "rationale": f"Validation failed: {reason}",
        }

    return {
        "body": body_text,
        "cta": cta_type,
        "send_as": send_as,
        "suppression_key": opp.suppression_key,
        "rationale": "; ".join(opp.why_now) or f"{opp.family} opportunity, urgency={opp.urgency}",
    }
