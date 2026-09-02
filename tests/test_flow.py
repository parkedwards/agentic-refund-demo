import pytest

from flows.issue_refund import _tool_payload


def test_tool_payload_unwraps_fastmcp_union_result() -> None:
    payment = {"found": True, "payment_id": "pay_123"}

    assert _tool_payload({"result": payment}) == payment


def test_tool_payload_keeps_direct_object_result() -> None:
    receipt = {"status": "succeeded", "refund_id": "re_123"}

    assert _tool_payload(receipt) == receipt


@pytest.mark.parametrize("content", [None, {"result": "not-an-object"}])
def test_tool_payload_rejects_non_object_result(content: object) -> None:
    with pytest.raises(ValueError, match="did not return"):
        _tool_payload(content)
