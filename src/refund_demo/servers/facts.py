from fastmcp import FastMCP

from refund_demo.models import (
    LookupFailure,
    OrderFacts,
    PaymentFacts,
    RefundHistory,
    RiskSignals,
)
from refund_demo.scenarios import evidence, scenario_for

mcp = FastMCP(
    "Refund Facts",
    instructions=(
        "These tools return read-only facts from synthetic order, payment, and "
        "risk systems. They do not make refund decisions."
    ),
)


@mcp.tool
def get_order_facts(case_id: str, order_id: str) -> OrderFacts | LookupFailure:
    """Read fulfillment and product facts for one order."""
    scenario = scenario_for(case_id)
    if order_id != scenario.order_id:
        return LookupFailure(
            entity="order", requested_id=order_id, reason="order_not_found_for_case"
        )

    return OrderFacts(
        case_id=scenario.case_id,
        order_id=scenario.order_id,
        customer_id=scenario.customer_id,
        purchased_at=scenario.purchase_date,
        purchase_channel="web",
        product_type=scenario.product_type,
        final_sale=scenario.final_sale,
        fulfillment_status=scenario.fulfillment_status,
        delivered_at=scenario.delivered_at,
        return_status=scenario.return_status,
        item_condition=scenario.item_condition,
        evidence=[
            evidence(
                f"{scenario.case_id}:order:product_type",
                "order_system",
                "product_type",
                scenario.product_type,
            ),
            evidence(
                f"{scenario.case_id}:fulfillment:status",
                "fulfillment_system",
                "fulfillment_status",
                scenario.fulfillment_status,
            ),
            evidence(
                f"{scenario.case_id}:returns:status",
                "returns_system",
                "return_status",
                scenario.return_status,
            ),
        ],
    )


@mcp.tool
def get_payment_facts(
    case_id: str, payment_id: str
) -> PaymentFacts | LookupFailure:
    """Read settlement, dispute, and refundable-balance facts for one payment."""
    scenario = scenario_for(case_id)
    if payment_id != scenario.payment_id:
        return LookupFailure(
            entity="payment",
            requested_id=payment_id,
            reason="payment_not_found_for_case",
        )

    return PaymentFacts(
        case_id=scenario.case_id,
        payment_id=scenario.payment_id,
        order_id=scenario.order_id,
        state=scenario.payment_state,
        amount_minor=scenario.amount_minor,
        currency=scenario.currency,
        prior_refunded_amount_minor=scenario.prior_refunded_amount_minor,
        refundable_amount_minor=scenario.refundable_amount_minor,
        active_dispute=scenario.active_dispute,
        evidence=[
            evidence(
                f"{scenario.case_id}:payment:state",
                "payment_system",
                "payment_state",
                scenario.payment_state,
            ),
            evidence(
                f"{scenario.case_id}:payment:refundable",
                "payment_system",
                "refundable_amount_minor",
                scenario.refundable_amount_minor,
            ),
            evidence(
                f"{scenario.case_id}:payment:dispute",
                "payment_system",
                "active_dispute",
                scenario.active_dispute,
            ),
        ],
    )


@mcp.tool
def get_refund_history(case_id: str, customer_id: str) -> RefundHistory:
    """Read the customer's aggregate order and refund history."""
    scenario = scenario_for(case_id)
    if customer_id != scenario.customer_id:
        raise ValueError("customer_not_found_for_case")

    return RefundHistory(
        case_id=scenario.case_id,
        customer_id=scenario.customer_id,
        completed_orders_12m=scenario.completed_orders_12m,
        refund_requests_12m=scenario.refund_requests_12m,
        refunds_approved_12m=scenario.refunds_approved_12m,
        chargebacks_12m=scenario.chargebacks_12m,
        evidence=[
            evidence(
                f"{scenario.case_id}:history:refunds",
                "customer_analytics",
                "refunds_approved_12m",
                scenario.refunds_approved_12m,
            ),
            evidence(
                f"{scenario.case_id}:history:chargebacks",
                "customer_analytics",
                "chargebacks_12m",
                scenario.chargebacks_12m,
            ),
        ],
    )


@mcp.tool
def get_risk_signals(case_id: str, customer_id: str) -> RiskSignals:
    """Read explainable risk signals for this request."""
    scenario = scenario_for(case_id)
    if customer_id != scenario.customer_id:
        raise ValueError("customer_not_found_for_case")

    return RiskSignals(
        case_id=scenario.case_id,
        customer_id=scenario.customer_id,
        risk_level=scenario.risk_level,
        signals=list(scenario.risk_signals),
        evidence=[
            evidence(
                f"{scenario.case_id}:risk:level",
                "risk_system",
                "risk_level",
                scenario.risk_level,
            )
        ],
    )


if __name__ == "__main__":
    mcp.run()
