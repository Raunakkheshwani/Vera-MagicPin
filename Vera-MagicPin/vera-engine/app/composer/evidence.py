"""
Builds the compact evidence bundle handed to the LLM composer. Each item
is tagged FACT/DERIVED/SOURCE/CONFIDENCE. Now optionally enriched with
Digital Twin facts (review theme, performance trend) so Message Evolution
has real alternate facts to pull from on a second attempt.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from app.engine.opportunity import Opportunity
from app.models.context import CategoryContext, CustomerContext, MerchantContext
from app.state.digital_twin import MerchantDigitalTwin


def build_evidence_bundle(
    opp: Opportunity,
    category: CategoryContext,
    merchant: MerchantContext,
    customer: Optional[CustomerContext],
    twin: Optional[MerchantDigitalTwin] = None,
) -> List[Dict[str, Any]]:
    bundle = list(opp.evidence)
    bundle.append({"type": "FACT", "fact": merchant.identity.name, "source": "MerchantContext.identity", "confidence": "high"})

    if customer is not None:
        bundle.append({"type": "FACT", "fact": customer.identity.name, "source": "CustomerContext.identity", "confidence": "high"})
        if customer.preferences.preferred_slots:
            bundle.append({
                "type": "FACT", "fact": customer.preferences.preferred_slots,
                "source": "CustomerContext.preferences", "confidence": "high",
            })

    if twin is not None:
        if twin.top_review_theme:
            bundle.append({"type": "DERIVED", "fact": f"top review theme: {twin.top_review_theme}",
                            "source": "MerchantContext.review_themes", "confidence": "medium"})
        bundle.append({"type": "DERIVED", "fact": f"7-day performance trend: {twin.performance_trend}",
                        "source": "MerchantContext.performance", "confidence": "medium"})

    return bundle