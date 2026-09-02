from datetime import UTC, datetime
from hashlib import sha256
from threading import Lock

from fastmcp import FastMCP

from refund_demo.models import (
    LookupFailure,
    PaymentFacts,
    RefundLedger,
    RefundReceipt,
    RefundRequest,
)
from refund_demo.scenarios import POLICY_VERSION, evidence, scenario_for

mcp = FastMCP(
    "Payment Sandbox",
    instructions=(
        "This server simulates an irreversible payment system. Attach it only to "
        "the terminal payment action node after policy or manager authorization."
    ),
)

_ledger_lock = Lock()
_receipts: dict[str, RefundReceipt] = {}
_request_hashes: dict[str, str] = {}


@mcp.tool
def get_authoritative_payment(
    case_id: str, payment_id: str
) -> PaymentFacts | LookupFailure:
    """Read the payment state that the write boundary uses for final validation."""
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
                f"{scenario.case_id}:authoritative-payment:state",
                "payment_write_system",
                "payment_state",
                scenario.payment_state,
            ),
            evidence(
                f"{scenario.case_id}:authoritative-payment:refundable",
                "payment_write_system",
                "refundable_amount_minor",
                scenario.refundable_amount_minor,
            ),
        ],
    )


@mcp.tool
def issue_refund(
    refund_request: RefundRequest,
    idempotency_key: str | None = None,
) -> RefundReceipt:
    """Issue one simulated refund after strict source and policy validation."""
    scenario = scenario_for(refund_request.case_id)
    expected_key = f"refund:{scenario.case_id}:{scenario.payment_id}"
    if idempotency_key is not None and idempotency_key != expected_key:
        raise ValueError("invalid_idempotency_key")
    idempotency_key = expected_key

    _validate_refund_request(refund_request)
    request_hash = sha256(refund_request.model_dump_json().encode()).hexdigest()

    with _ledger_lock:
        prior_hash = _request_hashes.get(idempotency_key)
        if prior_hash is not None and prior_hash != request_hash:
            raise ValueError("idempotency_key_reused_with_different_request")
        existing = _receipts.get(idempotency_key)
        if existing is not None:
            return existing.model_copy(update={"idempotent_replay": True})

        receipt = RefundReceipt(
            refund_id=f"re_{sha256(idempotency_key.encode()).hexdigest()[:16]}",
            idempotency_key=idempotency_key,
            case_id=scenario.case_id,
            payment_id=scenario.payment_id,
            amount_minor=refund_request.amount_minor,
            currency=refund_request.currency,
            status="succeeded",
            effect_count=1,
            idempotent_replay=False,
            created_at=datetime.now(UTC).isoformat(),
        )
        _request_hashes[idempotency_key] = request_hash
        _receipts[idempotency_key] = receipt
        return receipt


@mcp.tool
def get_refund_receipt(idempotency_key: str) -> RefundReceipt | LookupFailure:
    """Read a simulated refund receipt without creating a refund."""
    with _ledger_lock:
        receipt = _receipts.get(idempotency_key)
    if receipt is None:
        return LookupFailure(
            entity="refund",
            requested_id=idempotency_key,
            reason="refund_not_found",
        )
    return receipt


@mcp.tool
def list_refunds(case_id: str | None = None) -> RefundLedger:
    """List refund effects so a presenter can verify called and skipped paths."""
    normalized_case_id = scenario_for(case_id).case_id if case_id is not None else None
    with _ledger_lock:
        receipts = list(_receipts.values())
    if normalized_case_id is not None:
        receipts = [item for item in receipts if item.case_id == normalized_case_id]
    receipts.sort(key=lambda item: item.created_at)
    return RefundLedger(receipt_count=len(receipts), receipts=receipts)


def _validate_refund_request(refund_request: RefundRequest) -> None:
    expected = scenario_for(refund_request.case_id)
    if refund_request.customer_id != expected.customer_id:
        raise ValueError("customer_mismatch")
    if refund_request.order_id != expected.order_id:
        raise ValueError("order_mismatch")
    if refund_request.payment_id != expected.payment_id:
        raise ValueError("payment_mismatch")
    if refund_request.currency != expected.currency:
        raise ValueError("currency_mismatch")
    if refund_request.policy_version != POLICY_VERSION:
        raise ValueError("stale_policy_version")
    if refund_request.amount_minor > expected.refundable_amount_minor:
        raise ValueError("amount_exceeds_refundable_balance")
    if expected.payment_state != "settled":
        raise ValueError("payment_not_settled")
    if expected.active_dispute:
        raise ValueError("payment_has_active_dispute")
    if expected.final_sale:
        raise ValueError("final_sale_not_refundable")

    clauses = set(refund_request.policy_clause_ids)
    if refund_request.approval_mode == "policy":
        if refund_request.amount_minor > 10_000:
            raise ValueError("amount_exceeds_automatic_limit")
        if expected.risk_level != "low":
            raise ValueError("risk_requires_review")
        if not {"STANDARD-30", "AUTO-100"}.issubset(clauses):
            raise ValueError("automatic_policy_clauses_missing")
    elif "DELIVERY-EXCEPTION-2" not in clauses:
        raise ValueError("manager_exception_clause_missing")


if __name__ == "__main__":
    mcp.run()
