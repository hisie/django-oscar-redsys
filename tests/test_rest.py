from __future__ import annotations

from decimal import Decimal
from unittest.mock import Mock, patch

import pytest

from oscar_redsys import rest
from oscar_redsys.conf import RedsysSettings
from oscar_redsys.params import decode_merchant_parameters
from oscar_redsys.signature import sign_merchant_parameters_v1
from oscar_redsys.transaction_types import CANCELLATION, CONFIRMATION, REFUND

SETTINGS = RedsysSettings(
    merchant_code="999008881",
    terminal="1",
    secret_key="sq7HjrUOBfKmC576",
    currency="978",
    sandbox=True,
    merchant_url="https://example.com/notify/",
    url_ok="https://example.com/ok/",
    url_ko="https://example.com/ko/",
)


def _sign_and_wrap(order_number: str, ds_response: str) -> dict[str, str]:
    from oscar_redsys.params import encode_merchant_parameters_v1

    raw = {"Ds_Order": order_number, "Ds_Response": ds_response}
    encoded = encode_merchant_parameters_v1(raw)
    signature = sign_merchant_parameters_v1(SETTINGS.secret_key, order_number, encoded)
    return {
        "Ds_SignatureVersion": "HMAC_SHA512_V1",
        "Ds_MerchantParameters": encoded,
        "Ds_Signature": signature,
    }


def test_build_refund_request_uses_test_url_and_correct_transaction_type() -> None:
    request = rest.build_refund_request("1234567890", Decimal("9.99"), settings=SETTINGS)
    assert request.url == "https://sis-t.redsys.es:25443/sis/rest/trataPeticionREST"
    decoded = decode_merchant_parameters(request.body["Ds_MerchantParameters"])
    assert decoded["DS_MERCHANT_TRANSACTIONTYPE"] == REFUND
    assert decoded["DS_MERCHANT_AMOUNT"] == "999"
    assert decoded["DS_MERCHANT_ORDER"] == "1234567890"
    assert request.body["Ds_SignatureVersion"] == "HMAC_SHA512_V1"


def test_build_cancellation_request_transaction_type() -> None:
    request = rest.build_cancellation_request("1234567890", Decimal("9.99"), settings=SETTINGS)
    decoded = decode_merchant_parameters(request.body["Ds_MerchantParameters"])
    assert decoded["DS_MERCHANT_TRANSACTIONTYPE"] == CANCELLATION


def test_build_confirmation_request_transaction_type() -> None:
    request = rest.build_confirmation_request("1234567890", Decimal("9.99"), settings=SETTINGS)
    decoded = decode_merchant_parameters(request.body["Ds_MerchantParameters"])
    assert decoded["DS_MERCHANT_TRANSACTIONTYPE"] == CONFIRMATION


def test_build_refund_request_production_url_when_not_sandbox() -> None:
    prod_settings = RedsysSettings(**{**SETTINGS.__dict__, "sandbox": False})
    request = rest.build_refund_request("1234567890", Decimal("1"), settings=prod_settings)
    assert request.url == "https://sis.redsys.es/sis/rest/trataPeticionREST"


def test_build_refund_request_validates_order_number() -> None:
    with pytest.raises(ValueError):
        rest.build_refund_request("bad", Decimal("1"), settings=SETTINGS)


def test_parse_operation_response_authorized() -> None:
    body = _sign_and_wrap("1234567890", "0900")
    result = rest.parse_operation_response(body, settings=SETTINGS)
    assert result.error_code is None
    assert result.order_number == "1234567890"
    assert result.signature_valid is True
    assert result.authorized is True


def test_parse_operation_response_declined() -> None:
    body = _sign_and_wrap("1234567890", "0180")
    result = rest.parse_operation_response(body, settings=SETTINGS)
    assert result.signature_valid is True
    assert result.authorized is False


def test_parse_operation_response_invalid_signature() -> None:
    body = _sign_and_wrap("1234567890", "0900")
    body["Ds_Signature"] = "tampered"
    result = rest.parse_operation_response(body, settings=SETTINGS)
    assert result.signature_valid is False
    assert result.authorized is False


def test_parse_operation_response_error_code() -> None:
    result = rest.parse_operation_response({"errorCode": "SIS0042"}, settings=SETTINGS)
    assert result.error_code == "SIS0042"
    assert result.authorized is False


def test_send_operation_request_posts_json_and_parses_response() -> None:
    request = rest.build_refund_request("1234567890", Decimal("9.99"), settings=SETTINGS)
    fake_response = Mock()
    fake_response.json.return_value = _sign_and_wrap("1234567890", "0900")
    fake_response.raise_for_status.return_value = None

    with patch("oscar_redsys.rest.requests.post", return_value=fake_response) as mock_post:
        result = rest.send_operation_request(request, settings=SETTINGS)

    mock_post.assert_called_once_with(request.url, json=request.body, timeout=45)
    assert result.authorized is True


def test_send_operation_request_raises_on_http_error() -> None:
    request = rest.build_refund_request("1234567890", Decimal("9.99"), settings=SETTINGS)
    fake_response = Mock()
    fake_response.raise_for_status.side_effect = rest.requests.HTTPError("boom")

    with patch("oscar_redsys.rest.requests.post", return_value=fake_response):
        with pytest.raises(rest.requests.HTTPError):
            rest.send_operation_request(request, settings=SETTINGS)
