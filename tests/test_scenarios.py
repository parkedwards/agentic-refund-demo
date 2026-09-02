import pytest
from fastmcp import Client

from refund_demo.scenarios import scenario_for
from refund_demo.servers.facts import mcp as facts_mcp
from refund_demo.servers.identity import mcp as identity_mcp
from refund_demo.servers.payment import mcp as payment_mcp
from refund_demo.servers.policy import mcp as policy_mcp
from refund_demo.servers.remedies import mcp as remedies_mcp


@pytest.mark.parametrize(
    ("case_id", "kind"),
    [
        ("CASE-1047", "auto"),
        ("CASE-2083", "review"),
        ("CASE-3149", "deny"),
        ("CASE-4772", "ambiguous"),
        ("CASE-5226", "replacement"),
        ("CASE-6814", "store_credit"),
        ("CASE-7352", "carrier_review"),
    ],
)
def test_scripted_case_path_is_stable(case_id: str, kind: str) -> None:
    first = scenario_for(case_id)
    second = scenario_for(case_id.lower())

    assert first == second
    assert first.kind == kind


@pytest.mark.parametrize(
    ("case_id", "claim_type", "preferred_remedy"),
    [
        ("CASE-1047", "item_issue", "refund"),
        ("CASE-2083", "delivery_issue", "refund"),
        ("CASE-3149", "preference_issue", "refund"),
        ("CASE-5226", "item_issue", "replacement"),
        ("CASE-6814", "preference_issue", "store_credit"),
        ("CASE-7352", "delivery_issue", "refund"),
    ],
)
def test_scripted_case_has_stable_remedy_facts(
    case_id: str, claim_type: str, preferred_remedy: str
) -> None:
    scenario = scenario_for(case_id)

    assert scenario.claim_type == claim_type
    assert scenario.preferred_remedy == preferred_remedy


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
                "get_remedy_options",
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
        (
            remedies_mcp,
            {
                "create_replacement",
                "issue_store_credit",
                "open_carrier_review",
                "get_remedy_receipt",
                "list_remedy_actions",
            },
        ),
    ],
)
async def test_server_exposes_only_its_capabilities(server, expected_tools) -> None:
    async with Client(server) as client:
        tools = await client.list_tools()

    assert {tool.name for tool in tools} == expected_tools


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("case_id", "claim_type", "preferred_remedy"),
    [
        ("CASE-5226", "item_issue", "replacement"),
        ("CASE-6814", "preference_issue", "store_credit"),
        ("CASE-7352", "delivery_issue", "refund"),
    ],
)
async def test_remedy_options_match_scenario(
    case_id: str, claim_type: str, preferred_remedy: str
) -> None:
    scenario = scenario_for(case_id)
    async with Client(facts_mcp) as client:
        result = await client.call_tool(
            "get_remedy_options",
            {"case_id": scenario.case_id, "order_id": scenario.order_id},
        )

    content = result.structured_content["result"]
    assert content["claim_type"] == claim_type
    assert content["preferred_remedy"] == preferred_remedy


@pytest.mark.asyncio
async def test_policy_exposes_remedy_clauses() -> None:
    async with Client(policy_mcp) as client:
        result = await client.call_tool(
            "get_active_refund_policy",
            {
                "region": "US",
                "currency": "USD",
                "product_type": "physical_standard",
                "purchase_channel": "web",
                "as_of": "2026-08-04T16:00:00Z",
            },
        )

    clauses = result.structured_content["clauses"]
    clause_ids = {clause["clause_id"] for clause in clauses}
    assert {
        "REPLACEMENT-DAMAGE-1",
        "STORE-CREDIT-30",
        "CARRIER-REVIEW-1",
    } <= clause_ids


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
