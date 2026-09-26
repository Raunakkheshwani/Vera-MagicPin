"""
Merchant Digital Twin — a compact derived profile built ONLY from official
context, never invented. Guides the composer's word choice (e.g. lead
with a review theme instead of repeating the same performance stat on a
second attempt) — never fabricates facts.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

from app.models.context import MerchantContext


@dataclass
class MerchantDigitalTwin:
    merchant_id: str
    name: str
    category_slug: str
    subscription_status: str
    active_offer_titles: List[str]
    top_review_theme: Optional[str]
    performance_trend: str
    response_style: str


def build_digital_twin(merchant: MerchantContext) -> MerchantDigitalTwin:
    d = merchant.performance.delta_7d
    if d and d.views_pct is not None:
        trend = "up" if d.views_pct > 0.05 else "down" if d.views_pct < -0.05 else "flat"
    else:
        trend = "unknown"

    top_theme = None
    if merchant.review_themes:
        top_theme = max(merchant.review_themes, key=lambda t: t.occurrences_30d or 0).theme

    engaged_replies = [m for m in merchant.conversation_history if m.from_ == "merchant"]
    response_style = "responsive" if engaged_replies else "unknown"

    return MerchantDigitalTwin(
        merchant_id=merchant.merchant_id,
        name=merchant.identity.name,
        category_slug=merchant.category_slug,
        subscription_status=merchant.subscription.status,
        active_offer_titles=[o.title for o in merchant.offers if o.status == "active"],
        top_review_theme=top_theme,
        performance_trend=trend,
        response_style=response_style,
    )