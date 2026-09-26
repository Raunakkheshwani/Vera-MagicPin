"""
Opportunity Decay: a trigger's value erodes as it approaches expiry, and
drops to zero past it. "Avoid stale promotions and late follow-ups. Keep
decay deterministic and explainable." — Creative Differentiators doc.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional


def decay_factor(expires_at: Optional[str], now: Optional[datetime] = None,
                  full_value_window_hours: float = 24.0) -> float:
    if not expires_at:
        return 1.0
    try:
        expiry_dt = datetime.fromisoformat(expires_at.replace("Z", "+00:00"))
    except ValueError:
        return 1.0

    now = now or datetime.now(timezone.utc)
    remaining_hours = (expiry_dt - now).total_seconds() / 3600.0

    if remaining_hours <= 0:
        return 0.0
    if remaining_hours >= full_value_window_hours:
        return 1.0
    return round(remaining_hours / full_value_window_hours, 3)