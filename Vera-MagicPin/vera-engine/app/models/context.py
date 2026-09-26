"""
vera-engine/app/models/context.py

Official INPUT context models for the magicpin Vera AI Challenge.

These models represent exactly the four context objects defined by the
official challenge ZIP:
    - CategoryContext   (dataset/categories/*.json)
    - MerchantContext   (dataset/merchants_seed.json)
    - TriggerContext    (dataset/triggers_seed.json)
    - CustomerContext   (dataset/customers_seed.json)

RULES FOLLOWED WHILE WRITING THIS FILE:
    1. No field is renamed for "cleanliness." Official field names are kept
       verbatim (including the awkward-but-official `patient_content_library`
       key, which is reused as-is across ALL categories, not just clinics).
    2. No field is added because it "might be useful later." Anything Vera's
       own reasoning needs later (scores, ranks, decisions) belongs in
       SEPARATE internal models, not here.
    3. Where the official data itself is inconsistent (e.g. subscription
       shape differs between active/expired merchants), the model reflects
       that inconsistency with Optional fields rather than forcing a shape
       that would reject real records.
    4. Nested "knowledge blob" objects (voice, peer_stats, digest items,
       preferences, trigger payload) allow extra fields via
       `model_config = ConfigDict(extra="allow")`. This is deliberate: these
       sub-objects are documented as evolving/category-specific, and a
       strict schema here would reject valid official data the moment a
       category includes one extra field we didn't see in our 10-merchant,
       15-customer, 25-trigger sample.
    5. Fields we DID see be strictly required in every single official
       record we inspected stay required (no default). Everything else is
       Optional, matching what we actually observed.
"""

from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator


# ---------------------------------------------------------------------------
# CategoryContext
# ---------------------------------------------------------------------------
# Source: dataset/categories/{dentists,salons,restaurants,gyms,pharmacies}.json
# Confirmed identical top-level key set across all 5 category files.

class CategoryVoice(BaseModel):
    """Tone/vocabulary rules Vera must follow for this category."""
    model_config = ConfigDict(extra="allow")

    tone: str
    register: Optional[str] = None
    code_mix: Optional[str] = None
    vocab_allowed: List[str] = Field(default_factory=list)
    vocab_taboo: List[str] = Field(default_factory=list)
    salutation_examples: List[str] = Field(default_factory=list)
    tone_examples: List[str] = Field(default_factory=list)


class OfferCatalogItem(BaseModel):
    """One entry in a category's canonical offer catalog."""
    model_config = ConfigDict(extra="allow")

    id: str
    title: str
    value: str
    audience: str
    type: str


class PeerStats(BaseModel):
    """Category-wide benchmark numbers (avg views, avg CTR, etc.)."""
    model_config = ConfigDict(extra="allow")

    scope: Optional[str] = None
    avg_rating: Optional[float] = None
    avg_review_count: Optional[float] = None
    avg_views_30d: Optional[float] = None
    avg_calls_30d: Optional[float] = None
    avg_directions_30d: Optional[float] = None
    avg_ctr: Optional[float] = None
    avg_photos: Optional[float] = None
    avg_post_freq_days: Optional[float] = None
    retention_6mo_pct: Optional[float] = None


class DigestItem(BaseModel):
    """
    One knowledge-digest entry (research / compliance / cde / trend / tech).
    `kind` is intentionally a plain `str`, not a Literal: the 5 category
    files together show 5 different kind values, and nothing in the ZIP
    promises that set is closed — adaptive injection can push new digest
    kinds mid-test (see challenge-testing-brief.md, adaptive injection
    section, and api-call-examples.md Example 2.8).
    """
    model_config = ConfigDict(extra="allow")

    id: str
    kind: str
    title: str
    source: str
    summary: Optional[str] = None
    actionable: Optional[str] = None
    # kind-specific extras seen in the official data — kept optional
    # because they only apply to some kinds (e.g. trial_n only on
    # "research" kind, credits/date only on "cde" kind):
    trial_n: Optional[int] = None
    patient_segment: Optional[str] = None
    date: Optional[str] = None
    credits: Optional[int] = None
    deadline_iso: Optional[str] = None


class ContentLibraryItem(BaseModel):
    """
    A pre-written customer-education snippet. Official key name is
    `patient_content_library` even in non-clinical categories (salons,
    restaurants, gyms, pharmacies all use this exact key) — kept as-is.
    """
    model_config = ConfigDict(extra="allow")

    id: str
    title: str
    channel: str
    length_seconds: Optional[int] = None
    body: str


class SeasonalBeat(BaseModel):
    model_config = ConfigDict(extra="allow")

    month_range: str
    note: str


class TrendSignal(BaseModel):
    model_config = ConfigDict(extra="allow")

    query: str
    delta_yoy: Optional[float] = None
    segment_age: Optional[str] = None
    skew: Optional[str] = None


class CategoryContext(BaseModel):
    """
    Slow-changing, shared-across-merchants knowledge for one category
    (dentists / salons / restaurants / gyms / pharmacies).

    Pushed via POST /v1/context with scope="category".
    """
    model_config = ConfigDict(extra="allow")

    slug: str
    display_name: Optional[str] = None
    voice: CategoryVoice
    offer_catalog: List[OfferCatalogItem] = Field(default_factory=list)
    peer_stats: PeerStats = Field(default_factory=PeerStats)
    digest: List[DigestItem] = Field(default_factory=list)
    patient_content_library: List[ContentLibraryItem] = Field(default_factory=list)
    seasonal_beats: List[SeasonalBeat] = Field(default_factory=list)
    trend_signals: List[TrendSignal] = Field(default_factory=list)
    regulatory_authorities: List[str] = Field(default_factory=list)
    professional_journals: List[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# MerchantContext
# ---------------------------------------------------------------------------
# Source: dataset/merchants_seed.json ("merchants" list, 10 records)

class MerchantIdentity(BaseModel):
    model_config = ConfigDict(extra="allow")

    name: str
    city: str
    locality: Optional[str] = None
    place_id: Optional[str] = None
    verified: Optional[bool] = None
    languages: List[str] = Field(default_factory=list)
    owner_first_name: Optional[str] = None
    established_year: Optional[int] = None


class Subscription(BaseModel):
    """
    NOTE: real seed data proves this is NOT one fixed shape.
    m_004 (status="expired") has `days_since_expiry` instead of
    `days_remaining`, and lacks `renewed_at` entirely. `status` is left
    as `str` rather than a closed Literal — we only observed
    active/trial/expired in 10 records, which isn't proof the set is closed.
    """
    model_config = ConfigDict(extra="allow")

    status: str  # observed: "active" | "trial" | "expired"
    plan: Optional[str] = None
    days_remaining: Optional[int] = None
    days_since_expiry: Optional[int] = None
    renewed_at: Optional[str] = None


class PerformanceDelta7d(BaseModel):
    model_config = ConfigDict(extra="allow")

    views_pct: Optional[float] = None
    calls_pct: Optional[float] = None
    ctr_pct: Optional[float] = None  # only present for some merchants


class Performance(BaseModel):
    model_config = ConfigDict(extra="allow")

    window_days: Optional[int] = None
    views: Optional[int] = None
    calls: Optional[int] = None
    directions: Optional[int] = None
    ctr: Optional[float] = None
    leads: Optional[int] = None
    delta_7d: Optional[PerformanceDelta7d] = None


class MerchantOffer(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: str
    title: str
    status: str  # observed: "active" | "expired"
    started: Optional[str] = None
    ended: Optional[str] = None


class ConversationMessage(BaseModel):
    """
    One turn of prior WhatsApp history. `from` is a reserved word in
    Python, so we map it to `from_` internally but keep the wire name
    via alias — the official field name is untouched on the JSON side.
    """
    model_config = ConfigDict(extra="allow", populate_by_name=True)

    ts: str
    from_: str = Field(alias="from")
    body: str
    engagement: Optional[str] = None


class CustomerAggregate(BaseModel):
    model_config = ConfigDict(extra="allow")

    total_unique_ytd: Optional[int] = None
    lapsed_180d_plus: Optional[int] = None
    retention_6mo_pct: Optional[float] = None
    high_risk_adult_count: Optional[int] = None


class ReviewTheme(BaseModel):
    model_config = ConfigDict(extra="allow")

    theme: str
    sentiment: str
    occurrences_30d: Optional[int] = None
    common_quote: Optional[str] = None


class MerchantContext(BaseModel):
    """
    Everything known about one specific merchant.
    Pushed via POST /v1/context with scope="merchant".
    """
    model_config = ConfigDict(extra="allow")

    merchant_id: str
    category_slug: str
    identity: MerchantIdentity
    subscription: Subscription
    performance: Performance
    offers: List[MerchantOffer] = Field(default_factory=list)
    conversation_history: List[ConversationMessage] = Field(default_factory=list)
    customer_aggregate: Optional[CustomerAggregate] = None
    signals: List[str] = Field(default_factory=list)
    review_themes: List[ReviewTheme] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# TriggerContext
# ---------------------------------------------------------------------------
# Source: dataset/triggers_seed.json ("triggers" list, 25 records)

class AvailableSlot(BaseModel):
    """Seen inside recall/appointment trigger payloads (not a fixed schema
    field of TriggerContext itself — payload is intentionally generic,
    see TriggerContext.payload docstring below)."""
    model_config = ConfigDict(extra="allow")

    iso: str
    label: str


class TriggerContext(BaseModel):
    """
    A single reason Vera might act right now.

    `payload` is deliberately typed as `Dict[str, Any]`, NOT a fixed model.
    We inspected all 25 seed triggers across 24 distinct `kind` values
    (research_digest, recall_due, perf_dip, ipl_match_today, competitor_opened,
    chronic_refill_due, ...) and every one of them has a DIFFERENT payload
    shape. Forcing one schema onto `payload` would mean either rejecting
    valid triggers or inventing a superset schema not backed by the ZIP —
    both violate the "don't guess, don't invent" rule. The Opportunity
    Engine (a later module) is responsible for interpreting `payload`
    per-`kind`, not this contract layer.
    """
    model_config = ConfigDict(extra="allow")

    id: str
    scope: Literal["merchant", "customer"]
    kind: str
    source: Literal["internal", "external"]
    merchant_id: str
    customer_id: Optional[str] = None
    payload: Dict[str, Any] = Field(default_factory=dict)
    urgency: int = Field(ge=1, le=5)
    suppression_key: str
    expires_at: Optional[str] = None

    @model_validator(mode="after")
    def _customer_scope_requires_customer_id(self) -> "TriggerContext":
        """
        Verified invariant: all 5 customer-scoped triggers in the seed data
        carry a non-null customer_id. This isn't a guess — it's a real
        constraint the data enforces, so we encode it as validation rather
        than hoping downstream code remembers to check.
        """
        if self.scope == "customer" and not self.customer_id:
            raise ValueError(
                "TriggerContext.scope == 'customer' requires a non-null customer_id"
            )
        return self


# ---------------------------------------------------------------------------
# CustomerContext
# ---------------------------------------------------------------------------
# Source: dataset/customers_seed.json ("customers" list, 15 records)

class CustomerIdentity(BaseModel):
    model_config = ConfigDict(extra="allow")

    name: str
    phone_redacted: Optional[str] = None
    language_pref: Optional[str] = None
    age_band: Optional[str] = None


class CustomerRelationship(BaseModel):
    model_config = ConfigDict(extra="allow")

    first_visit: Optional[str] = None
    last_visit: Optional[str] = None
    visits_total: Optional[int] = None
    services_received: List[str] = Field(default_factory=list)
    lifetime_value: Optional[float] = None


class CustomerPreferences(BaseModel):
    """
    `channel` and `reminder_opt_in` are the only two fields present in
    EVERY one of the 15 seed records. `preferred_slots` is missing for the
    walk-in/anonymous customer (c_015). Every other key we saw
    (preferred_stylist, wedding_date, training_focus, health_focus,
    office_nearby, family_size, household_size, delivery_address) is
    category-specific and appears on only a subset of records — these are
    NOT hardcoded as fields; `extra="allow"` lets them pass through
    untouched instead of us inventing a fixed list that would go stale
    the moment a new category-specific preference shows up mid-test.
    """
    model_config = ConfigDict(extra="allow")

    channel: str
    reminder_opt_in: bool
    preferred_slots: Optional[str] = None


class CustomerConsent(BaseModel):
    model_config = ConfigDict(extra="allow")

    opted_in_at: Optional[str] = None
    scope: List[str] = Field(default_factory=list)


class CustomerContext(BaseModel):
    """
    Everything known about one specific customer of one specific merchant.
    Pushed via POST /v1/context with scope="customer".

    `state` IS modeled as a closed Literal (unlike subscription.status)
    because this 5-value set — including "churned", which never actually
    appears in our 15-record seed sample — is explicitly written out as a
    Literal type in the ZIP's own design docs (engagement-design.md and
    challenge-brief.md), not just inferred from data we happened to see.
    """
    model_config = ConfigDict(extra="allow")

    customer_id: str
    merchant_id: str
    identity: CustomerIdentity
    relationship: CustomerRelationship
    state: Literal["new", "active", "lapsed_soft", "lapsed_hard", "churned"]
    preferences: CustomerPreferences
    consent: CustomerConsent