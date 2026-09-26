"""
Category Policy Layer. Applies category-specific rules from official CategoryContext
and MerchantContext to guide opportunity scoring, action selection, and suppression.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from app.models.context import CategoryContext, CustomerContext, MerchantContext, TriggerContext


@dataclass
class CategoryPolicyResult:
    allowed: bool
    policy_fit: float  # 0.0 to 1.0
    recommended_action: Optional[str] = None
    recommended_cta: Optional[str] = None
    reason: str = ""


def evaluate_category_policy(
    category: CategoryContext,
    merchant: MerchantContext,
    trigger: TriggerContext,
    customer: Optional[CustomerContext],
    family: str,
) -> CategoryPolicyResult:
    slug = category.slug.lower()
    t_kind = trigger.kind.lower()

    # PHARMACY: Be conservative. Prioritize refill/compliance/operational/GBP workflows.
    # Suppress generic marketing pitches and generic dips/spikes without concrete action.
    if "pharmacy" in slug or "pharmacies" in slug:
        if family in ("compliance", "customer_recall"):
            return CategoryPolicyResult(
                allowed=True,
                policy_fit=1.0,
                recommended_action="send_compliance_alert" if family == "compliance" else "propose_refill_reminder",
                recommended_cta="binary_confirm_cancel" if family == "compliance" else "binary_yes_no",
                reason="Pharmacy operational/refill/compliance item highly relevant",
            )
        if "gbp" in t_kind or "unverified" in t_kind or "operational" in t_kind:
            return CategoryPolicyResult(
                allowed=True,
                policy_fit=0.9,
                recommended_action="prompt_gbp_verification",
                recommended_cta="binary_confirm_cancel",
                reason="Pharmacy GBP verification alert appropriate",
            )
        if family == "knowledge_digest":
            return CategoryPolicyResult(
                allowed=True,
                policy_fit=0.8,
                recommended_action="send_digest_insight",
                recommended_cta="open_ended",
                reason="Pharmacy regulatory/digest item",
            )
        # Generic promo or un-grounded dip/spike for pharmacy: lower fit / suppress if weak
        return CategoryPolicyResult(
            allowed=False,
            policy_fit=0.2,
            reason="Pharmacy policy suppresses generic marketing pitches without operational/refill context",
        )

    # SALON: Focus on appointments, service demand, bridal/event timing, service+price offers, curious asks.
    if "salon" in slug or "salons" in slug:
        if family == "customer_recall":
            return CategoryPolicyResult(
                allowed=True,
                policy_fit=1.0,
                recommended_action="propose_salon_booking_slot",
                recommended_cta="binary_yes_no",
                reason="Salon appointment recall relevant",
            )
        if family == "external_event" or "festival" in t_kind:
            return CategoryPolicyResult(
                allowed=True,
                policy_fit=0.9,
                recommended_action="propose_salon_service_offer",
                recommended_cta="binary_yes_no",
                reason="Salon festival/event service offer relevant",
            )
        if "curious" in t_kind or family == "knowledge_digest":
            return CategoryPolicyResult(
                allowed=True,
                policy_fit=0.95,
                recommended_action="ask_salon_trending_service",
                recommended_cta="open_ended",
                reason="Salon curious ask / trending service inquiry",
            )
        if family == "performance_dip":
            return CategoryPolicyResult(
                allowed=True,
                policy_fit=0.8,
                recommended_action="propose_salon_service_offer",
                recommended_cta="binary_yes_no",
                reason="Salon performance dip counteracted with service+price offer",
            )
        return CategoryPolicyResult(allowed=True, policy_fit=0.7, reason="Standard salon opportunity")

    # DENTIST: Peer-clinical tone, evidence-grounded, recall, study citations.
    if "dentist" in slug or "dentists" in slug:
        if family == "knowledge_digest":
            return CategoryPolicyResult(
                allowed=True,
                policy_fit=1.0,
                recommended_action="send_clinical_digest_citation",
                recommended_cta="open_ended",
                reason="Dentist clinical study citation relevant",
            )
        if family == "customer_recall":
            return CategoryPolicyResult(
                allowed=True,
                policy_fit=1.0,
                recommended_action="propose_dental_recall_slot",
                recommended_cta="binary_yes_no",
                reason="Dental patient recall due",
            )
        if family == "compliance":
            return CategoryPolicyResult(
                allowed=True,
                policy_fit=1.0,
                recommended_action="send_compliance_alert",
                recommended_cta="binary_confirm_cancel",
                reason="Dental compliance circular",
            )
        return CategoryPolicyResult(allowed=True, policy_fit=0.8, reason="Standard dentist opportunity")

    # RESTAURANT: Covers, footfall, AOV/RPC, match/occasion timing (BOGO pizza for IPL).
    if "restaurant" in slug or "restaurants" in slug:
        if "ipl" in t_kind or "match" in t_kind:
            return CategoryPolicyResult(
                allowed=True,
                policy_fit=1.0,
                recommended_action="propose_ipl_delivery_offer",
                recommended_cta="binary_yes_no",
                reason="Restaurant IPL match delivery offer alignment",
            )
        if "corporate" in t_kind or "thali" in t_kind:
            return CategoryPolicyResult(
                allowed=True,
                policy_fit=0.95,
                recommended_action="propose_corporate_catering_plan",
                recommended_cta="open_ended",
                reason="Restaurant corporate catering planning",
            )
        return CategoryPolicyResult(allowed=True, policy_fit=0.8, reason="Standard restaurant opportunity")

    # GYM: Memberships, lapse/churn, PT, attendance.
    if "gym" in slug or "gyms" in slug:
        if family in ("win_back", "customer_recall"):
            return CategoryPolicyResult(
                allowed=True,
                policy_fit=0.9,
                recommended_action="propose_gym_class_pass",
                recommended_cta="binary_yes_no",
                reason="Gym member win-back / recall pass",
            )
        return CategoryPolicyResult(allowed=True, policy_fit=0.8, reason="Standard gym opportunity")

    # Default fallback
    return CategoryPolicyResult(allowed=True, policy_fit=0.7, reason="Default category fit")
