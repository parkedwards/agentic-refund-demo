from datetime import UTC, datetime
from hashlib import sha256
from threading import Lock
from typing import Literal

from fastmcp import FastMCP

from refund_demo.models import (
    LookupFailure,
    RemedyLedger,
    RemedyReceipt,
    RemedyRequest,
)
from refund_demo.scenarios import POLICY_VERSION, scenario_for

mcp = FastMCP(
    "Remedy Sandbox",
    instructions=(
        "These tools create synthetic commerce effects. Call one write tool only from "
        "its terminal remedy action node."
    ),
)

RemedyAction = Literal["replacement", "store_credit", "carrier_review"]

_ledger_lock = Lock()
_receipts: dict[str, RemedyReceipt] = {}
_request_hashes: dict[str, str] = {}


@mcp.tool
def create_replacement(request: RemedyRequest) -> RemedyReceipt:
    """Create one synthetic replacement order after strict remedy validation."""
    return _create_remedy(request, expected_action="replacement")


@mcp.tool
def issue_store_credit(request: RemedyRequest) -> RemedyReceipt:
    """Issue one synthetic store credit after strict remedy validation."""
    return _create_remedy(request, expected_action="store_credit")


@mcp.tool
def open_carrier_review(request: RemedyRequest) -> RemedyReceipt:
    """Open one synthetic carrier review after strict remedy validation."""
    return _create_remedy(request, expected_action="carrier_review")


@mcp.tool
def get_remedy_receipt(
    case_id: str, action: RemedyAction
) -> RemedyReceipt | LookupFailure:
    """Read one remedy receipt without creating an effect."""
    scenario = scenario_for(case_id)
    idempotency_key = _idempotency_key(action, scenario.case_id, scenario.order_id)
    with _ledger_lock:
        receipt = _receipts.get(idempotency_key)
    if receipt is None:
        return LookupFailure(
            entity="remedy",
            requested_id=idempotency_key,
            reason="remedy_not_found",
        )
    return receipt


@mcp.tool
def list_remedy_actions(case_id: str | None = None) -> RemedyLedger:
    """List synthetic remedy effects for audit and skipped-path checks."""
    normalized_case_id = scenario_for(case_id).case_id if case_id is not None else None
    with _ledger_lock:
        receipts = list(_receipts.values())
    if normalized_case_id is not None:
        receipts = [item for item in receipts if item.case_id == normalized_case_id]
    receipts.sort(key=lambda item: item.created_at)
    return RemedyLedger(receipt_count=len(receipts), receipts=receipts)


def _create_remedy(
    request: RemedyRequest, *, expected_action: RemedyAction
) -> RemedyReceipt:
    if request.action != expected_action:
        raise ValueError("action_does_not_match_tool")
    scenario = scenario_for(request.case_id)
    _validate_request(request, expected_action=expected_action)
    idempotency_key = _idempotency_key(
        expected_action, scenario.case_id, scenario.order_id
    )
    request_hash = sha256(request.model_dump_json().encode()).hexdigest()

    with _ledger_lock:
        prior_hash = _request_hashes.get(idempotency_key)
        if prior_hash is not None and prior_hash != request_hash:
            raise ValueError("idempotency_key_reused_with_different_request")
        existing = _receipts.get(idempotency_key)
        if existing is not None:
            return existing.model_copy(update={"idempotent_replay": True})

        prefix = {
            "replacement": "rep",
            "store_credit": "cr",
            "carrier_review": "car",
        }[expected_action]
        receipt = RemedyReceipt(
            action_id=f"{prefix}_{sha256(idempotency_key.encode()).hexdigest()[:16]}",
            idempotency_key=idempotency_key,
            case_id=scenario.case_id,
            order_id=scenario.order_id,
            action=expected_action,
            amount_minor=request.amount_minor,
            currency=request.currency,
            status="succeeded",
            effect_count=1,
            idempotent_replay=False,
            created_at=datetime.now(UTC).isoformat(),
        )
        _request_hashes[idempotency_key] = request_hash
        _receipts[idempotency_key] = receipt
        return receipt


def _validate_request(request: RemedyRequest, *, expected_action: RemedyAction) -> None:
    scenario = scenario_for(request.case_id)
    if request.customer_id != scenario.customer_id:
        raise ValueError("customer_mismatch")
    if request.order_id != scenario.order_id:
        raise ValueError("order_mismatch")
    if request.currency != scenario.currency:
        raise ValueError("currency_mismatch")
    if request.policy_version != POLICY_VERSION:
        raise ValueError("stale_policy_version")
    if scenario.risk_level != "low":
        raise ValueError("risk_requires_review")

    clauses = set(request.policy_clause_ids)
    if expected_action == "replacement":
        if scenario.claim_type != "item_issue":
            raise ValueError("replacement_requires_item_issue")
        if scenario.preferred_remedy != "replacement":
            raise ValueError("replacement_not_requested")
        if not scenario.replacement_available:
            raise ValueError("replacement_unavailable")
        if request.amount_minor != 0:
            raise ValueError("replacement_amount_must_be_zero")
        if "REPLACEMENT-DAMAGE-1" not in clauses:
            raise ValueError("replacement_policy_clause_missing")
        return

    if expected_action == "store_credit":
        if scenario.claim_type != "preference_issue":
            raise ValueError("store_credit_requires_preference_issue")
        if scenario.preferred_remedy != "store_credit":
            raise ValueError("store_credit_not_requested")
        if scenario.final_sale:
            raise ValueError("final_sale_not_creditable")
        if request.amount_minor != scenario.amount_minor:
            raise ValueError("store_credit_amount_mismatch")
        if "STORE-CREDIT-30" not in clauses:
            raise ValueError("store_credit_policy_clause_missing")
        return

    if scenario.claim_type != "delivery_issue":
        raise ValueError("carrier_review_requires_delivery_issue")
    if not scenario.carrier_review_required:
        raise ValueError("carrier_review_not_required")
    if request.amount_minor != 0:
        raise ValueError("carrier_review_amount_must_be_zero")
    if "CARRIER-REVIEW-1" not in clauses:
        raise ValueError("carrier_review_policy_clause_missing")


def _idempotency_key(action: RemedyAction, case_id: str, order_id: str) -> str:
    return f"{action}:{case_id}:{order_id}"


if __name__ == "__main__":
    mcp.run()
