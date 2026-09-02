import pytest
from fastmcp import Client
from fastmcp.exceptions import ToolError

from refund_demo.scenarios import POLICY_VERSION, scenario_for
from refund_demo.servers.payment import mcp as payment_mcp


def refund_request_for(case_id: str, *, approval_mode: str) -> dict[str, object]:
    scenario = scenario_for(case_id)
    clauses = (
        ["STANDARD-30", "AUTO-100"]
        if approval_mode == "policy"
        else ["STANDARD-30", "DELIVERY-EXCEPTION-2"]
    )
    return {
        "case_id": scenario.case_id,
        "customer_id": scenario.customer_id,
        "order_id": scenario.order_id,
        "payment_id": scenario.payment_id,
        "amount_minor": scenario.requested_amount_minor,
        "currency": scenario.currency,
        "approval_mode": approval_mode,
        "policy_version": POLICY_VERSION,
        "policy_clause_ids": clauses,
        "reason_code": "demo_test",
    }


@pytest.mark.asyncio
async def test_issue_refund_is_idempotent() -> None:
    scenario = scenario_for("CASE-1047")
    arguments = {
        "refund_request": refund_request_for(
            scenario.case_id, approval_mode="policy"
        ),
        "idempotency_key": f"refund:{scenario.case_id}:{scenario.payment_id}",
    }

    async with Client(payment_mcp) as client:
        first = await client.call_tool("issue_refund", arguments)
        second = await client.call_tool("issue_refund", arguments)
        ledger = await client.call_tool(
            "list_refunds", {"case_id": scenario.case_id}
        )

    assert first.structured_content["idempotent_replay"] is False
    assert second.structured_content["idempotent_replay"] is True
    assert (
        second.structured_content["refund_id"]
        == first.structured_content["refund_id"]
    )
    assert ledger.structured_content["receipt_count"] == 1
    assert ledger.structured_content["receipts"][0]["effect_count"] == 1


@pytest.mark.asyncio
async def test_payment_boundary_rejects_denied_case() -> None:
    scenario = scenario_for("CASE-3149")
    arguments = {
        "refund_request": refund_request_for(
            scenario.case_id, approval_mode="manager"
        ),
        "idempotency_key": f"refund:{scenario.case_id}:{scenario.payment_id}",
    }

    async with Client(payment_mcp) as client:
        with pytest.raises(ToolError, match="final_sale_not_refundable"):
            await client.call_tool("issue_refund", arguments)
        ledger = await client.call_tool(
            "list_refunds", {"case_id": scenario.case_id}
        )

    assert ledger.structured_content["receipt_count"] == 0
