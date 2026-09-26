"""
Internal Decision Trace Logger.
Keeps a clean internal log of candidate opportunities, counterfactual scores,
decision policy evaluation, and evidence bundles. Never exposed to merchants/customers.
"""

from __future__ import annotations

import logging
from dataclasses import asdict, dataclass
from typing import Any, Dict, List, Optional

logger = logging.getLogger("vera.decision_trace")


@dataclass
class DecisionTrace:
    trigger_id: str
    merchant_id: str
    category_slug: str
    family: str
    relevance: float
    business_impact: float
    evidence_strength: float
    counterfactual_loss: float
    decision: str  # SEND / WAIT / SUPPRESS
    action_name: Optional[str]
    cta_type: Optional[str]
    suppress_reason: Optional[str]
    why_now: List[str]

    def log(self) -> None:
        logger.info(f"[DecisionTrace] {self.merchant_id} | {self.family} | Decision={self.decision} | Action={self.action_name} | Loss={self.counterfactual_loss:.2f} | Reason={self.suppress_reason or '; '.join(self.why_now[:2])}")
