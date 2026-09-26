"""
Message Evolution: "If outreach is ignored, change strategy rather than
blindly repeating." Attempt 1 = concise value. Attempt 2+ = different
angle (pull an alternate fact from the Digital Twin) and lower-friction
phrasing. Attempt count is tracked per (merchant_id, family) in
EngagementStore, and reset once the merchant replies with commitment or
the conversation ends.
"""

from __future__ import annotations

from typing import Optional

from app.state.digital_twin import MerchantDigitalTwin


def evolution_hint(attempt_number: int, twin: Optional[MerchantDigitalTwin]) -> Optional[str]:
    """
    Returns an instruction string to inject into the composer prompt, or
    None if this is a fresh (attempt 1) message needing no adjustment.
    """
    if attempt_number <= 1:
        return None

    if attempt_number == 2:
        if twin and twin.top_review_theme:
            return (
                f"This is a FOLLOW-UP — the first message was ignored. "
                f"Use a DIFFERENT angle this time: mention '{twin.top_review_theme}' "
                f"(a real recent review theme) instead of repeating the original stat. "
                f"Make the ask lower-friction — a single-tap yes/no."
            )
        return (
            "This is a FOLLOW-UP — the first message was ignored. "
            "Make the ask lower-friction (single-tap yes/no) and keep it shorter than before."
        )

    return (
        "Multiple attempts already made with no response. Keep this extremely "
        "short — treat it as a final, low-pressure nudge, not a repeat pitch."
    )