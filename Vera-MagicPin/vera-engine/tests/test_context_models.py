"""
vera-engine/tests/test_context_models.py

Validates app/models/context.py against the ACTUAL official dataset files
from the challenge ZIP — not hand-written fixtures. This is what proves the
models match the contract, rather than merely compiling.

OFFICIAL_DATASET_DIR below assumes the layout:
    Vera-MagicPin/
    ├── magicpin-ai-challenge/      <- official ZIP extracted here
    │   └── dataset/
    └── vera-engine/
        └── tests/test_context_models.py   <- this file
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.models.context import (
    CategoryContext,
    CustomerContext,
    MerchantContext,
    TriggerContext,
)

def _find_dataset_dir() -> Path:
    """
    Locate the official ZIP's dataset/ folder automatically, by searching
    for customers_seed.json anywhere under the repo root. This avoids
    hardcoding the extracted folder's name, which can vary depending on
    how the ZIP was unzipped (e.g. a nested folder inside it).
    """
    repo_root = Path(__file__).resolve().parents[2]  # .../Vera-MagicPin
    candidates = [
        p for p in repo_root.rglob("customers_seed.json")
        if ".venv" not in p.parts
    ]
    assert candidates, (
        f"Could not find customers_seed.json anywhere under {repo_root}.\n"
        f"Run this in your terminal to locate it manually:\n"
        f"  find '{repo_root}' -name customers_seed.json\n"
        f"Then hardcode OFFICIAL_DATASET_DIR to that file's parent folder."
    )
    return candidates[0].parent


OFFICIAL_DATASET_DIR = _find_dataset_dir()


def _load(name: str):
    path = OFFICIAL_DATASET_DIR / name
    assert path.exists(), (
        f"Could not find {path}. The dataset folder was located at "
        f"{OFFICIAL_DATASET_DIR}, but this specific file is missing from it."
    )
    return json.loads(path.read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# CategoryContext — all 5 official category files must validate
# ---------------------------------------------------------------------------

CATEGORY_FILES = ["dentists.json", "salons.json", "restaurants.json", "gyms.json", "pharmacies.json"]


@pytest.mark.parametrize("filename", CATEGORY_FILES)
def test_category_context_matches_official_file(filename):
    raw = _load(f"categories/{filename}")
    ctx = CategoryContext.model_validate(raw)

    assert ctx.slug == raw["slug"]
    assert ctx.voice.tone == raw["voice"]["tone"]

    assert len(ctx.offer_catalog) == len(raw["offer_catalog"])
    assert len(ctx.digest) == len(raw["digest"])

    assert ctx.voice.vocab_taboo == raw["voice"]["vocab_taboo"]


def test_category_context_tolerates_partial_payload_like_adaptive_injection():
    """
    api-call-examples.md Example 2.8 shows the judge can push a category
    context update containing only a subset of fields (e.g. just voice +
    digest) mid-test. Our model must accept this, not demand every field.
    """
    partial_payload = {
        "slug": "dentists",
        "voice": {"tone": "peer_clinical"},
        "digest": [
            {
                "id": "d_new_item",
                "kind": "compliance",
                "title": "New rule",
                "source": "DCI circular",
            }
        ],
    }
    ctx = CategoryContext.model_validate(partial_payload)
    assert ctx.offer_catalog == []
    assert ctx.digest[0].id == "d_new_item"


# ---------------------------------------------------------------------------
# MerchantContext — all 10 official seed merchants must validate,
# including the two "shape variance" cases we found
# ---------------------------------------------------------------------------

def _all_merchants():
    return _load("merchants_seed.json")["merchants"]


def test_all_seed_merchants_validate():
    for raw in _all_merchants():
        MerchantContext.model_validate(raw)


def test_merchant_subscription_shape_variance_is_handled():
    """
    m_004_glamour_salon_pune has status="expired" and uses
    `days_since_expiry` instead of `days_remaining`, and has no
    `renewed_at`. This is the exact edge case that would break a
    naive/guessed schema.
    """
    merchants = {m["merchant_id"]: m for m in _all_merchants()}
    raw = merchants["m_004_glamour_salon_pune"]
    m = MerchantContext.model_validate(raw)

    assert m.subscription.status == "expired"
    assert m.subscription.days_since_expiry == 38
    assert m.subscription.days_remaining is None
    assert m.subscription.renewed_at is None


def test_merchant_performance_ctr_pct_is_optional():
    """
    Only some merchants (dentists/salons in the seed) have ctr_pct inside
    delta_7d. Others only have views_pct/calls_pct. Must not require it.
    """
    merchants = {m["merchant_id"]: m for m in _all_merchants()}
    raw = merchants["m_005_pizzajunction_restaurant_delhi"]
    m = MerchantContext.model_validate(raw)
    assert m.performance.delta_7d.ctr_pct is None
    assert m.performance.delta_7d.views_pct is not None


# ---------------------------------------------------------------------------
# TriggerContext — all 25 official seed triggers, plus the validation rule
# ---------------------------------------------------------------------------

def _all_triggers():
    return _load("triggers_seed.json")["triggers"]


def test_all_seed_triggers_validate():
    for raw in _all_triggers():
        TriggerContext.model_validate(raw)


def test_trigger_urgency_range_enforced():
    raw = _all_triggers()[0].copy()
    raw["urgency"] = 9  # invalid: official range is 1-5
    with pytest.raises(ValidationError):
        TriggerContext.model_validate(raw)


def test_customer_scope_requires_customer_id():
    """
    This is our own encoded invariant (verified true across all 5
    customer-scoped seed triggers). Confirm it actually rejects the
    invalid case, not just passes valid ones by luck.
    """
    raw = next(t for t in _all_triggers() if t["scope"] == "customer").copy()
    raw["customer_id"] = None
    with pytest.raises(ValidationError):
        TriggerContext.model_validate(raw)


def test_merchant_scope_trigger_allows_null_customer_id():
    raw = next(t for t in _all_triggers() if t["scope"] == "merchant").copy()
    assert raw.get("customer_id") is None
    TriggerContext.model_validate(raw)  # must NOT raise


# ---------------------------------------------------------------------------
# CustomerContext — all 15 official seed customers, including the
# anonymous/walk-in edge case
# ---------------------------------------------------------------------------

def _all_customers():
    return _load("customers_seed.json")["customers"]


def test_all_seed_customers_validate():
    for raw in _all_customers():
        CustomerContext.model_validate(raw)


def test_anonymous_walkin_customer_edge_case():
    """
    c_015_anonymous_for_m010 has no preferred_slots, channel="none_recorded",
    and empty consent scope. This is the sparsest real record in the
    dataset — if our model handles this, it handles everything richer.
    """
    customers = {c["customer_id"]: c for c in _all_customers()}
    raw = customers["c_015_anonymous_for_m010"]
    c = CustomerContext.model_validate(raw)

    assert c.preferences.preferred_slots is None
    assert c.preferences.channel == "none_recorded"
    assert c.consent.scope == []
    assert c.state == "new"


def test_customer_state_rejects_invalid_value():
    raw = _all_customers()[0].copy()
    raw["state"] = "definitely_not_a_real_state"
    with pytest.raises(ValidationError):
        CustomerContext.model_validate(raw)


def test_customer_preferences_pass_through_category_specific_extras():
    """
    c_005_kavya_for_m003 has a salon-specific `wedding_date` preference key
    that isn't a fixed field on CustomerPreferences. Confirm it's preserved
    (not silently dropped) via extra="allow", accessible for later modules
    (e.g. a salon bridal-timeline opportunity) via model_extra.
    """
    customers = {c["customer_id"]: c for c in _all_customers()}
    raw = customers["c_005_kavya_for_m003"]
    c = CustomerContext.model_validate(raw)
    assert c.preferences.model_extra.get("wedding_date") == "2026-11-08"