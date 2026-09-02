import pytest
from fastmcp import Client
from fastmcp.exceptions import ToolError

from refund_demo.scenarios import POLICY_VERSION, scenario_for
from refund_demo.servers.remedies import mcp as remedies_mcp


def remedy_request_for(case_id: str, action: str, clause_id: str) -> dict[str, object]:
    scenario = scenario_for(case_id)
    return {
        "case_id": scenario.case_id,
        "customer_id": scenario.customer_id,
        "order_id": scenario.order_id,
        "action": action,
        "amount_minor": scenario.amount_minor if action == "store_credit" else 0,
        "currency": scenario.currency,
        "policy_version": POLICY_VERSION,
        "policy_clause_ids": [clause_id],
        "reason_code": "demo_test",
    }


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("case_id", "tool_name", "action", "clause_id"),
    [
        (
            "CASE-5226",
            "create_replacement",
            "replacement",
            "REPLACEMENT-DAMAGE-1",
        ),
        ("CASE-6814", "issue_store_credit", "store_credit", "STORE-CREDIT-30"),
        (
            "CASE-7352",
            "open_carrier_review",
            "carrier_review",
            "CARRIER-REVIEW-1",
        ),
    ],
)
async def test_remedy_action_is_idempotent(
    case_id: str, tool_name: str, action: str, clause_id: str
) -> None:
    request = remedy_request_for(case_id, action, clause_id)

    async with Client(remedies_mcp) as client:
        first = await client.call_tool(tool_name, {"request": request})
        second = await client.call_tool(tool_name, {"request": request})
        ledger = await client.call_tool("list_remedy_actions", {"case_id": case_id})

    assert first.structured_content["idempotent_replay"] is False
    assert second.structured_content["idempotent_replay"] is True
    assert (
        second.structured_content["action_id"]
        == first.structured_content["action_id"]
    )
    assert ledger.structured_content["receipt_count"] == 1
    assert ledger.structured_content["receipts"][0]["effect_count"] == 1


@pytest.mark.asyncio
async def test_replacement_rejects_refund_scenario() -> None:
    request = remedy_request_for(
        "CASE-1047", "replacement", "REPLACEMENT-DAMAGE-1"
    )

    async with Client(remedies_mcp) as client:
        with pytest.raises(ToolError, match="replacement_not_requested"):
            await client.call_tool("create_replacement", {"request": request})
