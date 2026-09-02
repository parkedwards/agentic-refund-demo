import re
from dataclasses import dataclass
from hashlib import sha256
from typing import Literal

from refund_demo.models import Evidence

DEMO_NOW = "2026-08-04T16:00:00Z"
POLICY_VERSION = "refund-policy-2026-08"
_CASE_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{2,63}$")

ScenarioKind = Literal[
    "auto",
    "review",
    "deny",
    "ambiguous",
    "replacement",
    "store_credit",
    "carrier_review",
]
ClaimType = Literal["item_issue", "delivery_issue", "preference_issue"]
PreferredRemedy = Literal["refund", "replacement", "store_credit"]


@dataclass(frozen=True)
class ScenarioTemplate:
    kind: ScenarioKind
    claim_type: ClaimType
    preferred_remedy: PreferredRemedy
    replacement_available: bool
    carrier_review_required: bool
    message: str
    requested_amount_minor: int
    purchase_date: str
    product_type: str
    final_sale: bool
    fulfillment_status: str
    delivered_at: str | None
    return_status: str
    item_condition: str
    payment_state: str
    prior_refunded_amount_minor: int
    refundable_amount_minor: int
    active_dispute: bool
    risk_level: Literal["low", "medium", "high"]
    risk_signals: tuple[str, ...]
    completed_orders_12m: int
    refund_requests_12m: int
    refunds_approved_12m: int
    chargebacks_12m: int


@dataclass(frozen=True)
class Scenario:
    case_id: str
    kind: ScenarioKind
    claim_type: ClaimType
    preferred_remedy: PreferredRemedy
    replacement_available: bool
    carrier_review_required: bool
    opened_at: str
    message: str
    claimed_email: str
    phone_last4: str
    order_hint: str
    requested_amount_minor: int
    currency: str
    region: str
    customer_id: str
    alternate_customer_id: str | None
    customer_name: str
    alternate_customer_name: str | None
    account_created_at: str
    order_id: str
    alternate_order_id: str | None
    payment_id: str
    alternate_payment_id: str | None
    purchase_date: str
    product_type: str
    final_sale: bool
    fulfillment_status: str
    delivered_at: str | None
    return_status: str
    item_condition: str
    payment_state: str
    prior_refunded_amount_minor: int
    refundable_amount_minor: int
    active_dispute: bool
    risk_level: Literal["low", "medium", "high"]
    risk_signals: tuple[str, ...]
    completed_orders_12m: int
    refund_requests_12m: int
    refunds_approved_12m: int
    chargebacks_12m: int

    @property
    def amount_minor(self) -> int:
        return self.requested_amount_minor

    @property
    def email(self) -> str:
        return f"customer-{self.customer_id[-8:]}@example.test"

    @property
    def alternate_email(self) -> str | None:
        if self.alternate_customer_id is None:
            return None
        return self.email


_TEMPLATES: dict[ScenarioKind, ScenarioTemplate] = {
    "auto": ScenarioTemplate(
        kind="auto",
        claim_type="item_issue",
        preferred_remedy="refund",
        replacement_available=True,
        carrier_review_required=False,
        message=(
            "My order arrived with a cracked lid. Please refund the item to the "
            "original payment method."
        ),
        requested_amount_minor=7495,
        purchase_date="2026-07-18T14:30:00Z",
        product_type="physical_standard",
        final_sale=False,
        fulfillment_status="delivered",
        delivered_at="2026-07-22T18:12:00Z",
        return_status="carrier_scan_received",
        item_condition="damaged_on_arrival",
        payment_state="settled",
        prior_refunded_amount_minor=0,
        refundable_amount_minor=7495,
        active_dispute=False,
        risk_level="low",
        risk_signals=("verified_contact", "established_account"),
        completed_orders_12m=8,
        refund_requests_12m=1,
        refunds_approved_12m=0,
        chargebacks_12m=0,
    ),
    "review": ScenarioTemplate(
        kind="review",
        claim_type="delivery_issue",
        preferred_remedy="refund",
        replacement_available=False,
        carrier_review_required=False,
        message=(
            "The carrier marked my package delivered, but the delivery photo is not "
            "my building. I need a refund."
        ),
        requested_amount_minor=18900,
        purchase_date="2026-07-23T09:20:00Z",
        product_type="physical_standard",
        final_sale=False,
        fulfillment_status="delivered_with_conflicting_evidence",
        delivered_at="2026-07-28T21:05:00Z",
        return_status="not_received",
        item_condition="unknown",
        payment_state="settled",
        prior_refunded_amount_minor=0,
        refundable_amount_minor=18900,
        active_dispute=False,
        risk_level="low",
        risk_signals=("verified_contact", "delivery_evidence_conflict"),
        completed_orders_12m=14,
        refund_requests_12m=1,
        refunds_approved_12m=1,
        chargebacks_12m=0,
    ),
    "deny": ScenarioTemplate(
        kind="deny",
        claim_type="preference_issue",
        preferred_remedy="refund",
        replacement_available=False,
        carrier_review_required=False,
        message="I changed my mind about the final-sale item. Please refund it.",
        requested_amount_minor=12900,
        purchase_date="2026-07-10T11:15:00Z",
        product_type="physical_final_sale",
        final_sale=True,
        fulfillment_status="delivered",
        delivered_at="2026-07-14T16:40:00Z",
        return_status="not_started",
        item_condition="opened",
        payment_state="settled",
        prior_refunded_amount_minor=0,
        refundable_amount_minor=12900,
        active_dispute=False,
        risk_level="low",
        risk_signals=("verified_contact",),
        completed_orders_12m=3,
        refund_requests_12m=0,
        refunds_approved_12m=0,
        chargebacks_12m=0,
    ),
    "ambiguous": ScenarioTemplate(
        kind="ambiguous",
        claim_type="preference_issue",
        preferred_remedy="refund",
        replacement_available=False,
        carrier_review_required=False,
        message=(
            "One of the two family orders on our shared email was wrong. I do not "
            "have the full order number."
        ),
        requested_amount_minor=5500,
        purchase_date="2026-07-29T13:05:00Z",
        product_type="physical_standard",
        final_sale=False,
        fulfillment_status="delivered",
        delivered_at="2026-08-02T17:25:00Z",
        return_status="not_started",
        item_condition="unknown",
        payment_state="settled",
        prior_refunded_amount_minor=0,
        refundable_amount_minor=5500,
        active_dispute=False,
        risk_level="medium",
        risk_signals=("shared_email", "incomplete_order_identifier"),
        completed_orders_12m=2,
        refund_requests_12m=0,
        refunds_approved_12m=0,
        chargebacks_12m=0,
    ),
    "replacement": ScenarioTemplate(
        kind="replacement",
        claim_type="item_issue",
        preferred_remedy="replacement",
        replacement_available=True,
        carrier_review_required=False,
        message=(
            "The blender jar arrived cracked. Please send a replacement instead of "
            "a refund."
        ),
        requested_amount_minor=8995,
        purchase_date="2026-07-20T10:10:00Z",
        product_type="physical_standard",
        final_sale=False,
        fulfillment_status="delivered",
        delivered_at="2026-07-25T15:30:00Z",
        return_status="photo_verified_damage",
        item_condition="damaged_on_arrival",
        payment_state="settled",
        prior_refunded_amount_minor=0,
        refundable_amount_minor=8995,
        active_dispute=False,
        risk_level="low",
        risk_signals=("verified_contact", "damage_photo_verified"),
        completed_orders_12m=6,
        refund_requests_12m=0,
        refunds_approved_12m=0,
        chargebacks_12m=0,
    ),
    "store_credit": ScenarioTemplate(
        kind="store_credit",
        claim_type="preference_issue",
        preferred_remedy="store_credit",
        replacement_available=False,
        carrier_review_required=False,
        message=(
            "The color does not work for me. I will accept store credit for a future "
            "purchase."
        ),
        requested_amount_minor=6400,
        purchase_date="2026-07-19T12:45:00Z",
        product_type="physical_standard",
        final_sale=False,
        fulfillment_status="delivered",
        delivered_at="2026-07-24T17:10:00Z",
        return_status="return_requested",
        item_condition="opened_like_new",
        payment_state="settled",
        prior_refunded_amount_minor=0,
        refundable_amount_minor=6400,
        active_dispute=False,
        risk_level="low",
        risk_signals=("verified_contact", "established_account"),
        completed_orders_12m=11,
        refund_requests_12m=1,
        refunds_approved_12m=1,
        chargebacks_12m=0,
    ),
    "carrier_review": ScenarioTemplate(
        kind="carrier_review",
        claim_type="delivery_issue",
        preferred_remedy="refund",
        replacement_available=False,
        carrier_review_required=True,
        message=(
            "Tracking has not moved for nine days and the package has not arrived. "
            "Please investigate before deciding the refund."
        ),
        requested_amount_minor=14200,
        purchase_date="2026-07-16T08:40:00Z",
        product_type="physical_standard",
        final_sale=False,
        fulfillment_status="in_transit_stalled",
        delivered_at=None,
        return_status="not_received",
        item_condition="unknown",
        payment_state="settled",
        prior_refunded_amount_minor=0,
        refundable_amount_minor=14200,
        active_dispute=False,
        risk_level="low",
        risk_signals=("verified_contact", "carrier_scan_stalled"),
        completed_orders_12m=5,
        refund_requests_12m=0,
        refunds_approved_12m=0,
        chargebacks_12m=0,
    ),
}

_FIXED_CASES: dict[str, ScenarioKind] = {
    "CASE-1047": "auto",
    "CASE-2083": "review",
    "CASE-3149": "deny",
    "CASE-4772": "ambiguous",
    "CASE-5226": "replacement",
    "CASE-6814": "store_credit",
    "CASE-7352": "carrier_review",
}


def normalize_case_id(case_id: str) -> str:
    normalized = case_id.strip().upper()
    if not _CASE_ID_PATTERN.fullmatch(normalized):
        raise ValueError(
            "case_id must have 3 to 64 letters, numbers, underscores, or hyphens"
        )
    return normalized


def scenario_for(case_id: str) -> Scenario:
    normalized = normalize_case_id(case_id)
    digest = sha256(normalized.encode()).hexdigest()
    kinds: tuple[ScenarioKind, ...] = tuple(_TEMPLATES)
    kind = _FIXED_CASES.get(normalized, kinds[int(digest[:2], 16) % len(kinds)])
    template = _TEMPLATES[kind]
    suffix = digest[:8]
    alternate = kind == "ambiguous"

    customer_id = f"cus_{suffix}"
    order_id = f"ord_{digest[8:16]}"
    return Scenario(
        case_id=normalized,
        kind=kind,
        claim_type=template.claim_type,
        preferred_remedy=template.preferred_remedy,
        replacement_available=template.replacement_available,
        carrier_review_required=template.carrier_review_required,
        opened_at=DEMO_NOW,
        message=template.message,
        claimed_email=f"customer-{customer_id[-8:]}@example.test",
        phone_last4=str(int(digest[16:20], 16) % 10_000).zfill(4),
        order_hint=order_id[-4:] if not alternate else order_id[-2:],
        requested_amount_minor=template.requested_amount_minor,
        currency="USD",
        region="US",
        customer_id=customer_id,
        alternate_customer_id=f"cus_{digest[20:28]}" if alternate else None,
        customer_name="Jordan Lee",
        alternate_customer_name="Morgan Lee" if alternate else None,
        account_created_at="2023-04-12T10:00:00Z",
        order_id=order_id,
        alternate_order_id=f"ord_{digest[28:36]}" if alternate else None,
        payment_id=f"pay_{digest[36:44]}",
        alternate_payment_id=f"pay_{digest[44:52]}" if alternate else None,
        purchase_date=template.purchase_date,
        product_type=template.product_type,
        final_sale=template.final_sale,
        fulfillment_status=template.fulfillment_status,
        delivered_at=template.delivered_at,
        return_status=template.return_status,
        item_condition=template.item_condition,
        payment_state=template.payment_state,
        prior_refunded_amount_minor=template.prior_refunded_amount_minor,
        refundable_amount_minor=template.refundable_amount_minor,
        active_dispute=template.active_dispute,
        risk_level=template.risk_level,
        risk_signals=template.risk_signals,
        completed_orders_12m=template.completed_orders_12m,
        refund_requests_12m=template.refund_requests_12m,
        refunds_approved_12m=template.refunds_approved_12m,
        chargebacks_12m=template.chargebacks_12m,
    )


def evidence(fact_id: str, source: str, fact: str, value: object) -> Evidence:
    return Evidence(
        fact_id=fact_id,
        source=source,
        fact=fact,
        value=str(value),
        observed_at=DEMO_NOW,
    )
