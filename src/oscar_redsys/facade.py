"""The public surface of this package: build a payment request, parse a notification.

Deliberately thin — it wires together :mod:`oscar_redsys.params` and
:mod:`oscar_redsys.signature` around the specific fields the redirection
manual's section 3 describes, plus the optional EMV3DS/SCA fields from
:mod:`oscar_redsys.emv3ds`. Line-item detail and anything not covered by
either of those are left to the caller to add via ``extra_parameters``
rather than grown into this class's constructor, since which of those
fields matter is a per-integration decision this package shouldn't guess
at.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal
from typing import Any

from .conf import SIGNATURE_VERSION, RedsysSettings, get_redsys_settings
from .emv3ds import Emv3dsData
from .params import decode_merchant_parameters, encode_merchant_parameters
from .response_codes import is_authorized
from .signature import sign_merchant_parameters, signatures_match

# Standard payment (as opposed to pre-authorization/refund/etc.) — the only
# transaction type this package builds requests for. Confirmed against the
# manual's Ds_MerchantParameters examples (section 3.1/3.3), which all use
# "0" for a plain sale.
TRANSACTION_TYPE_PAYMENT = "0"

# ISO 4217 minor-unit exponents this package has actually had to handle.
# Extend as needed — deliberately not exhaustive, since guessing an
# exponent wrong silently charges the wrong amount.
_CURRENCY_EXPONENTS = {
    "978": 2,  # EUR
}


def amount_to_minor_units(amount: Decimal, currency: str) -> str:
    try:
        exponent = _CURRENCY_EXPONENTS[currency]
    except KeyError as exc:
        raise ValueError(
            f"Unknown minor-unit exponent for currency {currency!r} — add it to "
            "_CURRENCY_EXPONENTS rather than guessing."
        ) from exc
    quantized = amount.scaleb(exponent).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
    return str(int(quantized))


@dataclass(frozen=True)
class PaymentRequest:
    """Everything the redirect form (section 3.3.4/6.1.4) needs to render."""

    gateway_url: str
    ds_signature_version: str
    ds_merchant_parameters: str
    ds_signature: str


@dataclass(frozen=True)
class Notification:
    """A parsed, signature-checked Redsys notification (section 4.1)."""

    order_number: str
    ds_response: str
    authorized: bool
    signature_valid: bool
    raw_parameters: dict[str, Any]


class RedsysFacade:
    def __init__(self, settings: RedsysSettings | None = None) -> None:
        self.settings = settings or get_redsys_settings()

    def build_payment_request(
        self,
        *,
        order_number: str,
        amount: Decimal,
        merchant_url: str | None = None,
        url_ok: str | None = None,
        url_ko: str | None = None,
        emv3ds: Emv3dsData | None = None,
        sca_exemption: str | None = None,
        extra_parameters: Mapping[str, Any] | None = None,
    ) -> PaymentRequest:
        settings = self.settings
        parameters: dict[str, Any] = {
            "DS_MERCHANT_AMOUNT": amount_to_minor_units(amount, settings.currency),
            "DS_MERCHANT_ORDER": order_number,
            "DS_MERCHANT_MERCHANTCODE": settings.merchant_code,
            "DS_MERCHANT_CURRENCY": settings.currency,
            "DS_MERCHANT_TRANSACTIONTYPE": TRANSACTION_TYPE_PAYMENT,
            "DS_MERCHANT_TERMINAL": settings.terminal,
            "DS_MERCHANT_MERCHANTURL": merchant_url or settings.merchant_url,
            "DS_MERCHANT_URLOK": url_ok or settings.url_ok,
            "DS_MERCHANT_URLKO": url_ko or settings.url_ko,
        }
        # Mutually optional, per the manual's own separate examples for each
        # (section 3.3.4) — nothing here forbids sending both at once, so
        # neither is validated against the other.
        if emv3ds is not None:
            parameters["DS_MERCHANT_EMV3DS"] = emv3ds.to_dict()
        if sca_exemption is not None:
            parameters["DS_MERCHANT_EXCEP_SCA"] = sca_exemption
        if extra_parameters:
            parameters.update(extra_parameters)

        encoded_parameters = encode_merchant_parameters(parameters)
        signature = sign_merchant_parameters(settings.secret_key, order_number, encoded_parameters)
        return PaymentRequest(
            gateway_url=settings.gateway_url,
            ds_signature_version=SIGNATURE_VERSION,
            ds_merchant_parameters=encoded_parameters,
            ds_signature=signature,
        )

    def parse_notification(self, post_data: Mapping[str, str]) -> Notification:
        encoded_parameters = post_data["Ds_MerchantParameters"]
        received_signature = post_data["Ds_Signature"]
        raw_parameters = decode_merchant_parameters(encoded_parameters)

        # Response field names ("Ds_Order", "Ds_Response", ...) are distinct
        # from the request's "DS_MERCHANT_*" names. The redirection manual
        # itself doesn't spell these out (they're in the separate, unfetched
        # "TPV-Virtual Parámetros Entrada-Salida.xlsx"); confirmed instead by
        # cross-checking several independent third-party Redsys client
        # implementations (PHP/Node/Go) that all decode the same field names
        # from a notification payload.
        order_number = str(raw_parameters["Ds_Order"])
        ds_response = str(raw_parameters.get("Ds_Response", ""))

        signature_valid = signatures_match(
            self.settings.secret_key, order_number, encoded_parameters, received_signature
        )
        return Notification(
            order_number=order_number,
            ds_response=ds_response,
            authorized=signature_valid and is_authorized(ds_response),
            signature_valid=signature_valid,
            raw_parameters=raw_parameters,
        )
