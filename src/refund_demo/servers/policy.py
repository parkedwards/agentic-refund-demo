from fastmcp import FastMCP

from refund_demo.models import PolicyClause, RefundPolicy
from refund_demo.scenarios import POLICY_VERSION

mcp = FastMCP(
    "Refund Policy",
    instructions=(
        "These read-only tools return the current refund policy. Cite clause IDs "
        "in every adjudication result."
    ),
)

_CLAUSES = {
    "STANDARD-30": PolicyClause(
        clause_id="STANDARD-30",
        title="Standard physical goods",
        rule=(
            "A non-final-sale physical item is eligible within 30 days when the "
            "payment is settled and has enough refundable balance."
        ),
        effect="allow",
    ),
    "AUTO-100": PolicyClause(
        clause_id="AUTO-100",
        title="Automatic approval limit",
        rule=(
            "An otherwise eligible request at or below USD 100.00 can receive "
            "automatic approval when risk is low and no material evidence conflicts."
        ),
        effect="allow",
    ),
    "REPLACEMENT-DAMAGE-1": PolicyClause(
        clause_id="REPLACEMENT-DAMAGE-1",
        title="Damaged-item replacement",
        rule=(
            "A verified damaged physical item can receive an automatic replacement "
            "when inventory is available, risk is low, and the customer requests it."
        ),
        effect="allow",
    ),
    "STORE-CREDIT-30": PolicyClause(
        clause_id="STORE-CREDIT-30",
        title="Store credit within return window",
        rule=(
            "A non-final-sale physical item can receive store credit within 30 days "
            "when the customer requests credit and risk is low."
        ),
        effect="allow",
    ),
    "CARRIER-REVIEW-1": PolicyClause(
        clause_id="CARRIER-REVIEW-1",
        title="Stalled shipment review",
        rule=(
            "Open a carrier review before a refund decision when tracking has stalled "
            "and authoritative delivery evidence is not yet available."
        ),
        effect="allow",
    ),
    "DELIVERY-EXCEPTION-2": PolicyClause(
        clause_id="DELIVERY-EXCEPTION-2",
        title="Conflicting delivery evidence",
        rule=(
            "A settled payment at or below USD 500.00 can receive a manager-approved "
            "exception when carrier evidence conflicts with the customer report."
        ),
        effect="require_approval",
    ),
    "FINAL-SALE-1": PolicyClause(
        clause_id="FINAL-SALE-1",
        title="Final-sale exclusion",
        rule="A final-sale item is not refundable after delivery.",
        effect="deny",
    ),
    "PAYMENT-BLOCK-1": PolicyClause(
        clause_id="PAYMENT-BLOCK-1",
        title="Payment state exclusion",
        rule=(
            "Deny a refund when the payment is not settled, has an active dispute, "
            "or has no refundable balance."
        ),
        effect="deny",
    ),
}


@mcp.tool
def get_active_refund_policy(
    region: str,
    currency: str,
    product_type: str,
    purchase_channel: str,
    as_of: str,
) -> RefundPolicy:
    """Get the policy that applies to the supplied market and purchase context."""
    if region.upper() != "US" or currency.upper() != "USD":
        raise ValueError("no_demo_policy_for_market")
    if purchase_channel != "web":
        raise ValueError("no_demo_policy_for_channel")
    if not product_type.startswith("physical_"):
        raise ValueError("no_demo_policy_for_product_type")
    if as_of < "2026-08-01" or as_of >= "2027-01-01":
        raise ValueError("no_active_demo_policy_for_date")

    return RefundPolicy(
        policy_version=POLICY_VERSION,
        effective_from="2026-08-01T00:00:00Z",
        effective_to=None,
        region="US",
        currency="USD",
        standard_window_days=30,
        digital_window_days=14,
        auto_approval_limit_minor=10_000,
        clauses=list(_CLAUSES.values()),
    )


@mcp.tool
def get_policy_clause(policy_version: str, clause_id: str) -> PolicyClause:
    """Read one complete policy clause by its stable ID."""
    if policy_version != POLICY_VERSION:
        raise ValueError("unknown_policy_version")
    try:
        return _CLAUSES[clause_id]
    except KeyError as exc:
        raise ValueError("unknown_policy_clause") from exc


if __name__ == "__main__":
    mcp.run()
