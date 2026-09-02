import pytest
from fastmcp import Client

from refund_demo.scenarios import scenario_for
from refund_demo.servers.facts import mcp as facts_mcp
from refund_demo.servers.identity import mcp as identity_mcp
from refund_demo.servers.payment import mcp as payment_mcp
from refund_demo.servers.policy import mcp as policy_mcp


@pytest.mark.parametrize(
    ("case_id", "kind"),
    [
        ("CASE-1047", "auto"),
        ("CASE-2083", "review"),
        ("CASE-3149", "deny"),
        ("CASE-4772", "ambiguous"),
    ],
)
def test_scripted_case_path_is_stable(case_id: str, kind: str) -> None:
    first = scenario_for(case_id)
    second = scenario_for(case_id.lower())

    assert first == second
    assert first.kind == kind


def test_arbitrary_case_is_stable() -> None:
    first = scenario_for("CASE-9281")
    second = scenario_for("CASE-9281")

    assert first == second
    assert first.customer_id.startswith("cus_")
    assert first.order_id.startswith("ord_")
    assert first.payment_id.startswith("pay_")


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("server", "expected_tools"),
    [
        (
            identity_mcp,
            {
                "get_support_case",
                "search_customers",
                "find_candidate_purchases",
            },
        ),
        (
            facts_mcp,
            {
                "get_order_facts",
                "get_payment_facts",
                "get_refund_history",
                "get_risk_signals",
            },
        ),
        (
            policy_mcp,
            {"get_active_refund_policy", "get_policy_clause"},
        ),
        (
            payment_mcp,
            {
                "get_authoritative_payment",
                "issue_refund",
                "get_refund_receipt",
                "list_refunds",
            },
        ),
    ],
)
async def test_server_exposes_only_its_capabilities(server, expected_tools) -> None:
    async with Client(server) as client:
        tools = await client.list_tools()

    assert {tool.name for tool in tools} == expected_tools


@pytest.mark.asyncio
async def test_ambiguous_case_returns_two_customer_candidates() -> None:
    scenario = scenario_for("CASE-4772")
    async with Client(identity_mcp) as client:
        result = await client.call_tool(
            "search_customers",
            {
                "case_id": scenario.case_id,
                "email": scenario.claimed_email,
                "phone_last4": scenario.phone_last4,
            },
        )

    assert result.structured_content["candidate_count"] == 2
