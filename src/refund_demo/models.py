from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class DemoModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Evidence(DemoModel):
    fact_id: str
    source: str
    fact: str
    value: str
    observed_at: str


class SupportCase(DemoModel):
    case_id: str
    opened_at: str
    channel: Literal["email", "chat", "phone"]
    message: str
    claimed_email: str
    phone_last4: str | None
    order_hint: str | None
    requested_amount_minor: int = Field(gt=0)
    currency: str
    region: str
    evidence: list[Evidence]


class CustomerCandidate(DemoModel):
    customer_id: str
    display_name: str
    email: str
    phone_last4: str
    account_created_at: str
    match_reasons: list[str]


class CustomerSearchResult(DemoModel):
    case_id: str
    candidate_count: int = Field(ge=0)
    candidates: list[CustomerCandidate]
    evidence: list[Evidence]


class PurchaseCandidate(DemoModel):
    customer_id: str
    order_id: str
    payment_id: str
    purchased_at: str
    amount_minor: int = Field(gt=0)
    currency: str
    product_type: str
    status: str
    match_reasons: list[str]


class PurchaseSearchResult(DemoModel):
    case_id: str
    candidate_count: int = Field(ge=0)
    candidates: list[PurchaseCandidate]
    evidence: list[Evidence]


class LookupFailure(DemoModel):
    found: Literal[False] = False
    entity: str
    requested_id: str
    reason: str


class OrderFacts(DemoModel):
    found: Literal[True] = True
    case_id: str
    order_id: str
    customer_id: str
    purchased_at: str
    purchase_channel: str
    product_type: str
    final_sale: bool
    fulfillment_status: str
    delivered_at: str | None
    return_status: str
    item_condition: str
    evidence: list[Evidence]


class PaymentFacts(DemoModel):
    found: Literal[True] = True
    case_id: str
    payment_id: str
    order_id: str
    state: str
    amount_minor: int = Field(gt=0)
    currency: str
    prior_refunded_amount_minor: int = Field(ge=0)
    refundable_amount_minor: int = Field(ge=0)
    active_dispute: bool
    evidence: list[Evidence]


class RefundHistory(DemoModel):
    case_id: str
    customer_id: str
    completed_orders_12m: int = Field(ge=0)
    refund_requests_12m: int = Field(ge=0)
    refunds_approved_12m: int = Field(ge=0)
    chargebacks_12m: int = Field(ge=0)
    evidence: list[Evidence]


class RiskSignals(DemoModel):
    case_id: str
    customer_id: str
    risk_level: Literal["low", "medium", "high"]
    signals: list[str]
    evidence: list[Evidence]


class PolicyClause(DemoModel):
    clause_id: str
    title: str
    rule: str
    effect: Literal["allow", "deny", "require_approval"]


class RefundPolicy(DemoModel):
    policy_version: str
    effective_from: str
    effective_to: str | None
    region: str
    currency: str
    standard_window_days: int = Field(gt=0)
    digital_window_days: int = Field(gt=0)
    auto_approval_limit_minor: int = Field(gt=0)
    clauses: list[PolicyClause]


class RefundRequest(DemoModel):
    case_id: str
    customer_id: str
    order_id: str
    payment_id: str
    amount_minor: int = Field(gt=0)
    currency: str
    approval_mode: Literal["policy", "manager"]
    policy_version: str
    policy_clause_ids: list[str] = Field(min_length=1)
    reason_code: str


class RefundReceipt(DemoModel):
    refund_id: str
    idempotency_key: str
    case_id: str
    payment_id: str
    amount_minor: int
    currency: str
    status: Literal["succeeded"]
    effect_count: Literal[1] = 1
    idempotent_replay: bool
    created_at: str


class RefundLedger(DemoModel):
    receipt_count: int = Field(ge=0)
    receipts: list[RefundReceipt]
