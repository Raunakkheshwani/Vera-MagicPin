"""
Next Best Action policy — decides the BUSINESS action before any LLM
touches it.
"""

from __future__ import annotations

from typing import Tuple

from app.engine.opportunity import Opportunity

FAMILY_ACTION = {
    "performance_dip": ("send_performance_insight", "open_ended", "vera"),
    "performance_spike": ("send_performance_insight", "open_ended", "vera"),
    "customer_recall": ("propose_booking_slot", "binary_yes_no", "merchant_on_behalf"),
    "win_back": ("propose_offer", "binary_yes_no", "merchant_on_behalf"),
    "competitive_threat": ("send_competitive_insight", "open_ended", "vera"),
    "external_event": ("propose_existing_offer", "binary_yes_no", "vera"),
    "compliance": ("send_compliance_alert", "binary_confirm_cancel", "vera"),
    "knowledge_digest": ("send_digest_insight", "open_ended", "vera"),
    "renewal": ("prompt_renewal", "binary_yes_no", "vera"),
    "generic": ("send_generic_check_in", "open_ended", "vera"),
}


def next_best_action(opp: Opportunity) -> Tuple[str, str, str]:
    return FAMILY_ACTION.get(opp.family, FAMILY_ACTION["generic"])