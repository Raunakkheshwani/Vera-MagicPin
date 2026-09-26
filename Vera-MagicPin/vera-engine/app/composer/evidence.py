"""
Builds the compact evidence bundle handed to the LLM composer. Each item
is tagged FACT/DERIVED/SOURCE/CONFIDENCE. Enriched with merchant identity details
(owner_name, city, locality, performance numbers) to eliminate hallucinations.
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
    bundle.append({"type": "FACT", "fact": f"merchant_name: {merchant.identity.name}", "source": "MerchantContext.identity", "confidence": "high"})
    
    if merchant.identity.owner_first_name:
        bundle.append({"type": "FACT", "fact": f"owner_first_name: {merchant.identity.owner_first_name}", "source": "MerchantContext.identity", "confidence": "high"})
    if merchant.identity.city:
        bundle.append({"type": "FACT", "fact": f"city: {merchant.identity.city}", "source": "MerchantContext.identity", "confidence": "high"})
    if merchant.identity.locality:
        bundle.append({"type": "FACT", "fact": f"locality: {merchant.identity.locality}", "source": "MerchantContext.identity", "confidence": "high"})

    if merchant.performance:
        if merchant.performance.views is not None:
            bundle.append({"type": "FACT", "fact": f"30d_views: {merchant.performance.views}", "source": "MerchantContext.performance", "confidence": "high"})
        if merchant.performance.calls is not None:
            bundle.append({"type": "FACT", "fact": f"30d_calls: {merchant.performance.calls}", "source": "MerchantContext.performance", "confidence": "high"})
        if merchant.performance.ctr is not None:
            bundle.append({"type": "FACT", "fact": f"30d_ctr: {merchant.performance.ctr*100:.1f}%", "source": "MerchantContext.performance", "confidence": "high"})

    if customer is not None:
        bundle.append({"type": "FACT", "fact": f"customer_name: {customer.identity.name}", "source": "CustomerContext.identity", "confidence": "high"})
        if customer.preferences.preferred_slots:
            bundle.append({
                "type": "FACT", "fact": f"preferred_slots: {customer.preferences.preferred_slots}",
                "source": "CustomerContext.preferences", "confidence": "high",
            })

    if twin is not None:
        if twin.top_review_theme:
            bundle.append({"type": "DERIVED", "fact": f"top review theme: {twin.top_review_theme}",
                            "source": "MerchantContext.review_themes", "confidence": "medium"})
        bundle.append({"type": "DERIVED", "fact": f"7-day performance trend: {twin.performance_trend}",
                        "source": "MerchantContext.performance", "confidence": "medium"})

    return bundle