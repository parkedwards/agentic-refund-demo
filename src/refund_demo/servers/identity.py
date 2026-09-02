from fastmcp import FastMCP

from refund_demo.models import (
    CustomerCandidate,
    CustomerSearchResult,
    PurchaseCandidate,
    PurchaseSearchResult,
    SupportCase,
)
from refund_demo.scenarios import evidence, scenario_for

mcp = FastMCP(
    "Refund Identity",
    instructions=(
        "Use these read-only tools to resolve one support case to a customer, "
        "order, and payment. Treat multiple candidates as ambiguous."
    ),
)


@mcp.tool
def get_support_case(case_id: str) -> SupportCase:
    """Read the original customer request and its claimed identifiers."""
    scenario = scenario_for(case_id)
    return SupportCase(
        case_id=scenario.case_id,
        opened_at=scenario.opened_at,
        channel="email",
        message=scenario.message,
        claimed_email=scenario.claimed_email,
        phone_last4=scenario.phone_last4,
        order_hint=scenario.order_hint,
        requested_amount_minor=scenario.requested_amount_minor,
        currency=scenario.currency,
        region=scenario.region,
        evidence=[
            evidence(
                f"{scenario.case_id}:case:email",
                "support_case",
                "claimed_email",
                scenario.claimed_email,
            ),
            evidence(
                f"{scenario.case_id}:case:order_hint",
                "support_case",
                "order_hint",
                scenario.order_hint,
            ),
        ],
    )


@mcp.tool
def search_customers(
    case_id: str,
    email: str | None = None,
    phone_last4: str | None = None,
) -> CustomerSearchResult:
    """Search synthetic CRM records with identifiers from a support case."""
    scenario = scenario_for(case_id)
    if email is None and phone_last4 is None:
        raise ValueError("provide_email_or_phone_last4")
    query_matches = (
        (email is None or email.casefold() == scenario.email.casefold())
        and (phone_last4 is None or phone_last4 == scenario.phone_last4)
    )
    match_reasons = []
    if email is not None:
        match_reasons.append("email_exact")
    if phone_last4 is not None:
        match_reasons.append("phone_last4_exact")

    candidates: list[CustomerCandidate] = []
    if query_matches:
        candidates.append(
            CustomerCandidate(
                customer_id=scenario.customer_id,
                display_name=scenario.customer_name,
                email=scenario.email,
                phone_last4=scenario.phone_last4,
                account_created_at=scenario.account_created_at,
                match_reasons=match_reasons,
            )
        )
        if scenario.alternate_customer_id is not None:
            candidates.append(
                CustomerCandidate(
                    customer_id=scenario.alternate_customer_id,
                    display_name=scenario.alternate_customer_name or "Taylor Lee",
                    email=scenario.alternate_email or scenario.email,
                    phone_last4=scenario.phone_last4,
                    account_created_at="2025-11-08T12:00:00Z",
                    match_reasons=["shared_email", *match_reasons],
                )
            )

    return CustomerSearchResult(
        case_id=scenario.case_id,
        candidate_count=len(candidates),
        candidates=candidates,
        evidence=[
            evidence(
                f"{scenario.case_id}:crm:candidate_count",
                "crm",
                "candidate_count",
                len(candidates),
            )
        ],
    )


@mcp.tool
def find_candidate_purchases(
    case_id: str,
    customer_id: str,
    order_hint: str | None = None,
) -> PurchaseSearchResult:
    """Find purchases that can connect a customer record to the support case."""
    scenario = scenario_for(case_id)
    candidates: list[PurchaseCandidate] = []

    if customer_id == scenario.customer_id and (
        order_hint is None or scenario.order_id.endswith(order_hint)
    ):
        candidates.append(
            PurchaseCandidate(
                customer_id=scenario.customer_id,
                order_id=scenario.order_id,
                payment_id=scenario.payment_id,
                purchased_at=scenario.purchase_date,
                amount_minor=scenario.amount_minor,
                currency=scenario.currency,
                product_type=scenario.product_type,
                status=scenario.fulfillment_status,
                match_reasons=["customer_owner", "order_hint_match"],
            )
        )

    if (
        scenario.alternate_customer_id is not None
        and customer_id == scenario.alternate_customer_id
        and scenario.alternate_order_id is not None
        and scenario.alternate_payment_id is not None
    ):
        candidates.append(
            PurchaseCandidate(
                customer_id=scenario.alternate_customer_id,
                order_id=scenario.alternate_order_id,
                payment_id=scenario.alternate_payment_id,
                purchased_at="2026-07-30T15:45:00Z",
                amount_minor=scenario.amount_minor,
                currency=scenario.currency,
                product_type="physical_standard",
                status="delivered",
                match_reasons=["customer_owner", "partial_order_hint_match"],
            )
        )

    return PurchaseSearchResult(
        case_id=scenario.case_id,
        candidate_count=len(candidates),
        candidates=candidates,
        evidence=[
            evidence(
                f"{scenario.case_id}:orders:candidate_count:{customer_id}",
                "order_system",
                "candidate_count",
                len(candidates),
            )
        ],
    )


if __name__ == "__main__":
    mcp.run()
