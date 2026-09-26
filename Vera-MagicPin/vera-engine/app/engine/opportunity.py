"""
Opportunity Engine. Converts (trigger, category, merchant, customer) into a scored
Opportunity — integrating Category Policy, Evidence Strength, Decay, and
Counterfactual Loss (avoiding low-value outreach).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from app.engine.category_policy import evaluate_category_policy
from app.engine.opportunity_decay import decay_factor
from app.models.context import CategoryContext, CustomerContext, MerchantContext, TriggerContext


@dataclass
class Opportunity:
    trigger_id: str
    merchant_id: str
    customer_id: Optional[str]
    family: str
    value: float
    urgency: int
    why_now: List[str]
    evidence: List[Dict[str, Any]]
    suppress: bool = False
    suppress_reason: Optional[str] = None
    bypass_fatigue: bool = False
    suppression_key: str = ""
    recommended_action: Optional[str] = None
    recommended_cta: Optional[str] = None

    @property
    def score(self) -> float:
        return self.value * self.urgency


def _active_offer(merchant: MerchantContext):
    for o in merchant.offers:
        if o.status == "active":
            return o
    return None


def classify_family(kind: str) -> str:
    k = kind.lower()
    if "perf_dip" in k or "performance_dip" in k:
        return "performance_dip"
    if "perf_spike" in k or "performance_spike" in k or "milestone" in k:
        return "performance_spike"
    if "recall" in k or "refill" in k or "appointment" in k:
        return "customer_recall"
    if "lapsed" in k or "dormant" in k or "churn" in k:
        return "win_back"
    if "competitor" in k:
        return "competitive_threat"
    if "ipl" in k or "festival" in k or "match" in k:
        return "external_event"
    if "compliance" in k or "regulation" in k or "gbp_unverified" in k:
        return "compliance"
    if "research" in k or "digest" in k or "trend" in k or "curious" in k or "planning" in k:
        return "knowledge_digest"
    if "renewal" in k or "trial_followup" in k or "subscription" in k:
        return "renewal"
    return "generic"


def score_opportunity(
    trigger: TriggerContext,
    category: CategoryContext,
    merchant: MerchantContext,
    customer: Optional[CustomerContext],
) -> Opportunity:
    family = classify_family(trigger.kind)
    why_now: List[str] = []
    evidence: List[Dict[str, Any]] = []
    value = trigger.urgency / 5.0
    suppress = False
    suppress_reason = None
    bypass_fatigue = False

    # Evaluate Category-Specific Policy
    cat_policy = evaluate_category_policy(category, merchant, trigger, customer, family)
    if not cat_policy.allowed and family != "compliance":
        suppress = True
        suppress_reason = cat_policy.reason
    value *= cat_policy.policy_fit

    if family == "performance_dip":
        d = merchant.performance.delta_7d
        pct = d.views_pct if d and d.views_pct is not None else None
        if pct is not None:
            why_now.append(f"7-day views changed {pct*100:.0f}%")
            evidence.append({"type": "FACT", "fact": f"views_pct_7d={pct}", "source": "MerchantContext", "confidence": "high"})
            value = min(1.0, abs(pct) / 0.3) if pct < 0 else value * 0.3
        offer = _active_offer(merchant)
        if offer:
            why_now.append(f"active offer available: {offer.title}")
            evidence.append({"type": "FACT", "fact": offer.title, "source": "MerchantContext.offers", "confidence": "high"})

    elif family == "performance_spike":
        d = merchant.performance.delta_7d
        pct = d.views_pct if d and d.views_pct is not None else None
        if pct is not None and pct > 0:
            why_now.append(f"7-day views up {pct*100:.0f}% — good moment to capitalize")
            evidence.append({"type": "FACT", "fact": f"views_pct_7d={pct}", "source": "MerchantContext", "confidence": "high"})
            value = min(1.0, pct / 0.3)

    elif family == "customer_recall":
        if customer is None:
            suppress, suppress_reason = True, "customer-scoped family with no resolved CustomerContext"
        elif customer.consent.scope and "promotional_offers" not in customer.consent.scope and "recall_reminders" not in customer.consent.scope:
            suppress, suppress_reason = True, "customer consent scope does not cover recall messaging"
        else:
            why_now.append(f"customer state={customer.state}, last_visit={customer.relationship.last_visit}")
            evidence.append({"type": "FACT", "fact": f"state={customer.state}", "source": "CustomerContext", "confidence": "high"})
            value = 0.7 if customer.state in ("active", "lapsed_soft") else 0.5

    elif family == "win_back":
        if customer is None:
            suppress, suppress_reason = True, "customer-scoped family with no resolved CustomerContext"
        else:
            why_now.append(f"customer state={customer.state} (win-back candidate)")
            evidence.append({"type": "FACT", "fact": f"state={customer.state}", "source": "CustomerContext", "confidence": "high"})
            value = 0.6 if customer.state == "lapsed_soft" else 0.4

    elif family == "competitive_threat":
        offer = _active_offer(merchant)
        why_now.append("a competitor opened nearby")
        if offer:
            why_now.append(f"can counter with existing offer: {offer.title}")
            value = 0.6
        else:
            value = 0.3

    elif family == "external_event":
        offer = _active_offer(merchant)
        if offer is None and category.offer_catalog:
            offer = category.offer_catalog[0]
        if offer is None:
            suppress, suppress_reason = True, "external event with no relevant offer to anchor a message to"
        else:
            title = getattr(offer, "title", None)
            why_now.append(f"upcoming festival/event seasonal surge, featured promotion: {title}")
            evidence.append({"type": "FACT", "fact": title, "source": "MerchantContext/CategoryContext offer", "confidence": "medium"})
            value = 0.55

    elif family == "compliance":
        why_now.append(f"regulatory/listing update required: {trigger.kind}")
        value = 1.0
        bypass_fatigue = True
        payload_summary = str(trigger.payload)[:120]
        evidence.append({"type": "FACT", "fact": payload_summary, "source": "TriggerContext.payload", "confidence": "medium"})

    elif family == "knowledge_digest":
        matching = None
        for item in category.digest:
            if item.kind and item.kind in trigger.kind:
                matching = item
                break
        if matching is None and category.digest:
            matching = category.digest[0]
        if matching is None:
            suppress, suppress_reason = True, "no grounded digest item found to cite for this knowledge trigger"
        else:
            why_now.append(f"category digest item available: {matching.title}")
            evidence.append({"type": "FACT", "fact": matching.title, "source": matching.source, "confidence": "high"})
            if matching.source:
                evidence.append({"type": "FACT", "fact": f"citation_source: {matching.source}", "source": "CategoryContext.digest", "confidence": "high"})
            if matching.trial_n:
                evidence.append({"type": "FACT", "fact": f"trial_n: {matching.trial_n} patients", "source": matching.source, "confidence": "high"})
            if matching.summary:
                evidence.append({"type": "FACT", "fact": f"digest_summary: {matching.summary}", "source": matching.source, "confidence": "high"})
            value = 0.5

    elif family == "renewal":
        why_now.append(f"subscription status={merchant.subscription.status}")
        evidence.append({"type": "FACT", "fact": merchant.subscription.status, "source": "MerchantContext.subscription", "confidence": "high"})
        value = 0.6 if merchant.subscription.status in ("expired", "trial") else 0.3

    else:
        why_now.append(f"ungrouped trigger kind '{trigger.kind}', scored on urgency alone")
        value = value * 0.5

    if merchant.subscription.status == "expired" and family != "compliance":
        value *= 0.5
        why_now.append("merchant subscription expired — deprioritized")

    # Opportunity Decay & Counterfactual Loss
    decay = decay_factor(trigger.expires_at)
    if decay == 0.0 and not bypass_fatigue:
        suppress, suppress_reason = True, suppress_reason or "trigger has expired (decay reached zero)"
    value = value * decay

    counterfactual_loss = value * decay
    if counterfactual_loss < 0.1 and family != "compliance" and trigger.urgency < 4:
        suppress, suppress_reason = True, suppress_reason or "Low counterfactual loss (benefit does not justify interruption cost)"

    if decay < 1.0 and decay > 0.0:
        why_now.append(f"opportunity decaying — {decay*100:.0f}% of value remaining before expiry")

    return Opportunity(
        trigger_id=trigger.id,
        merchant_id=trigger.merchant_id,
        customer_id=trigger.customer_id,
        family=family,
        value=round(max(0.0, min(1.0, value)), 3),
        urgency=trigger.urgency,
        why_now=why_now,
        evidence=evidence,
        suppress=suppress,
        suppress_reason=suppress_reason,
        bypass_fatigue=bypass_fatigue,
        suppression_key=trigger.suppression_key,
        recommended_action=cat_policy.recommended_action,
        recommended_cta=cat_policy.recommended_cta,
    )