"""Confirm/refund/cancel an already-authorized operation — server-to-server.

Per Redsys's "TPV-Virtual Manual Integración-REST" (v4.0.1.1, 17/10/2025,
ref. RS.TE.CEL.MAN.0037): unlike a payment, there is no browser redirect
for these — the merchant's own backend POSTs directly to Redsys's REST
endpoint, referencing the original ``Ds_Merchant_Order``, with no card
data involved at all. This is the *only* way to issue a refund or
cancellation through the redirection integration method; nothing about
it goes through :mod:`oscar_redsys.facade` or the customer's browser.

Deliberately kept out of anything a shopper's session could reach — see
``oscar_redsys/admin.py`` for the one place this is wired up, gated by a
custom Django permission. A refund/cancellation is a merchant/seller
decision, never a self-service storefront action.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any

import requests

from .conf import RedsysSettings, get_redsys_settings
from .facade import amount_to_minor_units
from .order_number import validate_order_number
from .params import decode_merchant_parameters, encode_merchant_parameters_v1
from .response_codes import is_authorized
from .signature import sign_merchant_parameters_v1, signatures_match_v1
from .transaction_types import CANCELLATION, CONFIRMATION, REFUND

SIGNATURE_VERSION_V1 = "HMAC_SHA512_V1"

_TEST_URL = "https://sis-t.redsys.es:25443/sis/rest/trataPeticionREST"
_PRODUCTION_URL = "https://sis.redsys.es/sis/rest/trataPeticionREST"


@dataclass(frozen=True)
class RestOperationRequest:
    url: str
    body: dict[str, str]


@dataclass(frozen=True)
class RestOperationResult:
    """The outcome of a REST operation call.

    ``error_code`` is set for Redsys's "not processed" response shape
    (``{"errorCode": "SIS0042"}``, section "Respuesta de una operación No
    procesada correctamente") — in that case none of the other fields are
    meaningful. Otherwise ``signature_valid``/``authorized`` describe a
    normal signed response, exactly like a redirection-flow notification.
    """

    error_code: str | None
    order_number: str | None = None
    ds_response: str | None = None
    signature_valid: bool = False
    authorized: bool = False
    raw_parameters: dict[str, Any] | None = None


def _gateway_url(settings: RedsysSettings) -> str:
    return _TEST_URL if settings.sandbox else _PRODUCTION_URL


def _build_operation_request(
    settings: RedsysSettings,
    *,
    order_number: str,
    amount: Decimal,
    transaction_type: str,
) -> RestOperationRequest:
    validate_order_number(order_number)
    parameters = {
        "DS_MERCHANT_ORDER": order_number,
        "DS_MERCHANT_MERCHANTCODE": settings.merchant_code,
        "DS_MERCHANT_TERMINAL": settings.terminal,
        "DS_MERCHANT_CURRENCY": settings.currency,
        "DS_MERCHANT_TRANSACTIONTYPE": transaction_type,
        "DS_MERCHANT_AMOUNT": amount_to_minor_units(amount, settings.currency),
    }
    encoded_parameters = encode_merchant_parameters_v1(parameters)
    signature = sign_merchant_parameters_v1(settings.secret_key, order_number, encoded_parameters)
    body = {
        "Ds_SignatureVersion": SIGNATURE_VERSION_V1,
        "Ds_MerchantParameters": encoded_parameters,
        "Ds_Signature": signature,
    }
    return RestOperationRequest(url=_gateway_url(settings), body=body)


def build_confirmation_request(
    order_number: str, amount: Decimal, *, settings: RedsysSettings | None = None
) -> RestOperationRequest:
    """Confirm a preauthorization (``DS_MERCHANT_TRANSACTIONTYPE = "2"``)."""
    return _build_operation_request(
        settings or get_redsys_settings(),
        order_number=order_number,
        amount=amount,
        transaction_type=CONFIRMATION,
    )


def build_refund_request(
    order_number: str, amount: Decimal, *, settings: RedsysSettings | None = None
) -> RestOperationRequest:
    """Refund an already-authorized payment (``DS_MERCHANT_TRANSACTIONTYPE = "3"``)."""
    return _build_operation_request(
        settings or get_redsys_settings(),
        order_number=order_number,
        amount=amount,
        transaction_type=REFUND,
    )


def build_cancellation_request(
    order_number: str, amount: Decimal, *, settings: RedsysSettings | None = None
) -> RestOperationRequest:
    """Cancel an already-authorized payment/preauthorization
    (``DS_MERCHANT_TRANSACTIONTYPE = "9"``)."""
    return _build_operation_request(
        settings or get_redsys_settings(),
        order_number=order_number,
        amount=amount,
        transaction_type=CANCELLATION,
    )


def parse_operation_response(
    body: dict[str, Any], *, settings: RedsysSettings | None = None
) -> RestOperationResult:
    if "errorCode" in body:
        return RestOperationResult(error_code=str(body["errorCode"]))

    settings = settings or get_redsys_settings()
    encoded_parameters = str(body["Ds_MerchantParameters"])
    received_signature = str(body["Ds_Signature"])
    raw_parameters = decode_merchant_parameters(encoded_parameters)

    order_number = str(raw_parameters["Ds_Order"])
    ds_response = str(raw_parameters.get("Ds_Response", ""))
    signature_valid = signatures_match_v1(
        settings.secret_key, order_number, encoded_parameters, received_signature
    )
    return RestOperationResult(
        error_code=None,
        order_number=order_number,
        ds_response=ds_response,
        signature_valid=signature_valid,
        authorized=signature_valid and is_authorized(ds_response),
        raw_parameters=raw_parameters,
    )


def send_operation_request(
    request: RestOperationRequest,
    *,
    settings: RedsysSettings | None = None,
    timeout: float = 45,
) -> RestOperationResult:
    """Actually perform the server-to-server call.

    ``timeout`` defaults to 45s, per the REST manual's own "Timeout"
    section: Redsys's connection to the card-issuer's authorization center
    has its own 30s timeout before Redsys itself replies, so the caller
    needs a longer one to reliably get *any* answer back.
    """
    response = requests.post(request.url, json=request.body, timeout=timeout)
    response.raise_for_status()
    return parse_operation_response(response.json(), settings=settings)
