import os
from typing import Any

from fastmcp import Client
from prefect import flow
from prefect.artifacts import acreate_markdown_artifact
from prefect.logging import get_run_logger

from refund_demo.models import RefundRequest


@flow(name="issue-refund-sandbox", log_prints=True)
async def issue_refund(
    refund_request: RefundRequest,
    decision_evidence: dict[str, Any],
) -> dict[str, Any]:
    """Validate and issue one refund through the isolated payment sandbox."""
    logger = get_run_logger()
    payment_mcp_url = os.environ["PAYMENT_SANDBOX_MCP_URL"]
    horizon_api_key = os.environ["HORIZON_API_KEY"]
    idempotency_key = (
        f"refund:{refund_request.case_id.upper()}:{refund_request.payment_id}"
    )

    async with Client(payment_mcp_url, auth=horizon_api_key) as client:
        payment_result = await client.call_tool(
            "get_authoritative_payment",
            {
                "case_id": refund_request.case_id,
                "payment_id": refund_request.payment_id,
            },
        )
        payment = payment_result.structured_content
        if not isinstance(payment, dict) or payment.get("found") is not True:
            raise ValueError("The authoritative payment does not exist.")
        _validate_payment_boundary(refund_request, payment)

        refund_result = await client.call_tool(
            "issue_refund",
            {
                "refund_request": refund_request.model_dump(),
                "idempotency_key": idempotency_key,
            },
        )

    receipt = refund_result.structured_content
    if not isinstance(receipt, dict) or receipt.get("status") != "succeeded":
        raise ValueError("The payment sandbox did not return a refund receipt.")

    logger.info(
        "Payment sandbox issued refund %s for case %s.",
        receipt["refund_id"],
        refund_request.case_id,
    )
    await acreate_markdown_artifact(
        key=f"refund-receipt-{refund_request.case_id.lower()}",
        description="The payment sandbox receipt for an agentic refund run.",
        markdown=_receipt_markdown(receipt, refund_request, decision_evidence),
    )
    return receipt


def _validate_payment_boundary(
    refund_request: RefundRequest, payment: dict[str, Any]
) -> None:
    if payment["payment_id"] != refund_request.payment_id:
        raise ValueError("The payment ID changed before execution.")
    if payment["currency"] != refund_request.currency:
        raise ValueError("The payment currency changed before execution.")
    if payment["state"] != "settled":
        raise ValueError("The payment is not settled.")
    if payment["active_dispute"]:
        raise ValueError("The payment has an active dispute.")
    if payment["refundable_amount_minor"] < refund_request.amount_minor:
        raise ValueError("The refund exceeds the current refundable balance.")


def _receipt_markdown(
    receipt: dict[str, Any],
    refund_request: RefundRequest,
    decision_evidence: dict[str, Any],
) -> str:
    clauses = ", ".join(refund_request.policy_clause_ids)
    facts = ", ".join(str(item) for item in decision_evidence.get("fact_ids", []))
    return f"""# Simulated refund receipt

| Field | Value |
| --- | --- |
| Refund ID | `{receipt["refund_id"]}` |
| Case ID | `{refund_request.case_id}` |
| Payment ID | `{refund_request.payment_id}` |
| Amount | `{refund_request.amount_minor}` minor units |
| Currency | `{refund_request.currency}` |
| Approval mode | `{refund_request.approval_mode}` |
| Policy | `{refund_request.policy_version}` |
| Policy clauses | `{clauses}` |
| Evidence facts | `{facts}` |
| Idempotent replay | `{receipt["idempotent_replay"]}` |

The deterministic child flow created this artifact after the payment boundary
accepted the command.
"""


if __name__ == "__main__":
    issue_refund.serve(name="issue-refund-sandbox")
