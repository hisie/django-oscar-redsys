from __future__ import annotations

from decimal import Decimal

import pytest

from oscar_redsys.conf import RedsysSettings
from oscar_redsys.emv3ds import Emv3dsData, MobilePhone, ScaExemption
from oscar_redsys.facade import RedsysFacade, amount_to_minor_units, minor_units_to_amount
from oscar_redsys.params import decode_merchant_parameters
from oscar_redsys.signature import signatures_match

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


def test_amount_to_minor_units_eur() -> None:
    assert amount_to_minor_units(Decimal("9.99"), "978") == "999"
    assert amount_to_minor_units(Decimal("100"), "978") == "10000"
    assert amount_to_minor_units(Decimal("0.01"), "978") == "1"


def test_amount_to_minor_units_unknown_currency_raises() -> None:
    with pytest.raises(ValueError):
        amount_to_minor_units(Decimal("9.99"), "840")  # USD, not in our known-exponent table


def test_minor_units_to_amount_eur() -> None:
    assert minor_units_to_amount("999", "978") == Decimal("9.99")
    assert minor_units_to_amount("1", "978") == Decimal("0.01")


def test_minor_units_to_amount_is_the_inverse_of_amount_to_minor_units() -> None:
    amount = Decimal("42.37")
    assert minor_units_to_amount(amount_to_minor_units(amount, "978"), "978") == amount


def test_minor_units_to_amount_unknown_currency_raises() -> None:
    with pytest.raises(ValueError):
        minor_units_to_amount("999", "840")


def test_build_payment_request_produces_valid_signature() -> None:
    facade = RedsysFacade(settings=SETTINGS)
    request = facade.build_payment_request(order_number="1234567890", amount=Decimal("9.99"))

    assert request.ds_signature_version == "HMAC_SHA512_V2"
    assert request.gateway_url == "https://sis-t.redsys.es:25443/sis/realizarPago"
    assert signatures_match(
        SETTINGS.secret_key,
        "1234567890",
        request.ds_merchant_parameters,
        request.ds_signature,
    )


def test_build_payment_request_encodes_expected_fields() -> None:
    facade = RedsysFacade(settings=SETTINGS)
    request = facade.build_payment_request(order_number="1234567890", amount=Decimal("9.99"))
    decoded = decode_merchant_parameters(request.ds_merchant_parameters)

    assert decoded["DS_MERCHANT_AMOUNT"] == "999"
    assert decoded["DS_MERCHANT_ORDER"] == "1234567890"
    assert decoded["DS_MERCHANT_MERCHANTCODE"] == "999008881"
    assert decoded["DS_MERCHANT_CURRENCY"] == "978"
    assert decoded["DS_MERCHANT_TRANSACTIONTYPE"] == "0"
    assert decoded["DS_MERCHANT_TERMINAL"] == "1"
    assert decoded["DS_MERCHANT_MERCHANTURL"] == "https://example.com/notify/"
    assert decoded["DS_MERCHANT_URLOK"] == "https://example.com/ok/"
    assert decoded["DS_MERCHANT_URLKO"] == "https://example.com/ko/"


def test_build_payment_request_extra_parameters_override_nothing_unexpected() -> None:
    facade = RedsysFacade(settings=SETTINGS)
    request = facade.build_payment_request(
        order_number="1234567890",
        amount=Decimal("9.99"),
        extra_parameters={"DS_MERCHANT_PRODUCTDESCRIPTION": "1x Palmera"},
    )
    decoded = decode_merchant_parameters(request.ds_merchant_parameters)
    assert decoded["DS_MERCHANT_PRODUCTDESCRIPTION"] == "1x Palmera"


def test_build_payment_request_per_call_urls_override_settings() -> None:
    facade = RedsysFacade(settings=SETTINGS)
    request = facade.build_payment_request(
        order_number="1234567890",
        amount=Decimal("9.99"),
        merchant_url="https://override.example.com/notify/",
    )
    decoded = decode_merchant_parameters(request.ds_merchant_parameters)
    assert decoded["DS_MERCHANT_MERCHANTURL"] == "https://override.example.com/notify/"
    assert decoded["DS_MERCHANT_URLOK"] == "https://example.com/ok/"  # unaffected


def test_build_payment_request_with_emv3ds_data() -> None:
    facade = RedsysFacade(settings=SETTINGS)
    emv3ds = Emv3dsData(
        ship_addr_country="840",
        cardholder_name="Cardholder Name",
        email="example@example.com",
        mobile_phone=MobilePhone(country_code="123", subscriber="123456789"),
    )
    request = facade.build_payment_request(
        order_number="1234567890", amount=Decimal("9.99"), emv3ds=emv3ds
    )
    decoded = decode_merchant_parameters(request.ds_merchant_parameters)

    assert decoded["DS_MERCHANT_EMV3DS"] == {
        "shipAddrCountry": "840",
        "cardholderName": "Cardholder Name",
        "email": "example@example.com",
        "mobilePhone": {"cc": "123", "subscriber": "123456789"},
    }
    assert signatures_match(
        SETTINGS.secret_key,
        "1234567890",
        request.ds_merchant_parameters,
        request.ds_signature,
    )


def test_build_payment_request_without_emv3ds_omits_the_field() -> None:
    facade = RedsysFacade(settings=SETTINGS)
    request = facade.build_payment_request(order_number="1234567890", amount=Decimal("9.99"))
    decoded = decode_merchant_parameters(request.ds_merchant_parameters)
    assert "DS_MERCHANT_EMV3DS" not in decoded


def test_build_payment_request_with_sca_exemption() -> None:
    facade = RedsysFacade(settings=SETTINGS)
    request = facade.build_payment_request(
        order_number="1234567890",
        amount=Decimal("9.99"),
        sca_exemption=ScaExemption.TRANSACTION_RISK_ANALYSIS,
    )
    decoded = decode_merchant_parameters(request.ds_merchant_parameters)
    assert decoded["DS_MERCHANT_EXCEP_SCA"] == "TRA"


def test_build_payment_request_without_sca_exemption_omits_the_field() -> None:
    facade = RedsysFacade(settings=SETTINGS)
    request = facade.build_payment_request(order_number="1234567890", amount=Decimal("9.99"))
    decoded = decode_merchant_parameters(request.ds_merchant_parameters)
    assert "DS_MERCHANT_EXCEP_SCA" not in decoded


def test_build_payment_request_with_consumer_language() -> None:
    from oscar_redsys.language import ConsumerLanguage

    facade = RedsysFacade(settings=SETTINGS)
    request = facade.build_payment_request(
        order_number="1234567890",
        amount=Decimal("9.99"),
        consumer_language=ConsumerLanguage.ENGLISH,
    )
    decoded = decode_merchant_parameters(request.ds_merchant_parameters)
    assert decoded["DS_MERCHANT_CONSUMERLANGUAGE"] == "002"


def test_build_payment_request_without_consumer_language_omits_the_field() -> None:
    facade = RedsysFacade(settings=SETTINGS)
    request = facade.build_payment_request(order_number="1234567890", amount=Decimal("9.99"))
    decoded = decode_merchant_parameters(request.ds_merchant_parameters)
    assert "DS_MERCHANT_CONSUMERLANGUAGE" not in decoded


def test_build_payment_request_with_both_emv3ds_and_sca_exemption() -> None:
    facade = RedsysFacade(settings=SETTINGS)
    request = facade.build_payment_request(
        order_number="1234567890",
        amount=Decimal("9.99"),
        emv3ds=Emv3dsData(email="example@example.com"),
        sca_exemption=ScaExemption.LOW_VALUE,
    )
    decoded = decode_merchant_parameters(request.ds_merchant_parameters)
    assert decoded["DS_MERCHANT_EMV3DS"] == {"email": "example@example.com"}
    assert decoded["DS_MERCHANT_EXCEP_SCA"] == "LWV"


def test_production_gateway_url_when_not_sandbox() -> None:
    prod_settings = RedsysSettings(**{**SETTINGS.__dict__, "sandbox": False})
    facade = RedsysFacade(settings=prod_settings)
    request = facade.build_payment_request(order_number="1234567890", amount=Decimal("1"))
    assert request.gateway_url == "https://sis.redsys.es/sis/realizarPago"


def _build_notification_post(order_number: str, ds_response: str) -> dict[str, str]:
    from oscar_redsys.params import encode_merchant_parameters
    from oscar_redsys.signature import sign_merchant_parameters

    raw = {"Ds_Order": order_number, "Ds_Response": ds_response, "Ds_MerchantCode": "999008881"}
    encoded = encode_merchant_parameters(raw)
    signature = sign_merchant_parameters(SETTINGS.secret_key, order_number, encoded)
    return {"Ds_MerchantParameters": encoded, "Ds_Signature": signature}


def test_parse_notification_authorized() -> None:
    facade = RedsysFacade(settings=SETTINGS)
    post = _build_notification_post("1234567890", "0000")
    notification = facade.parse_notification(post)

    assert notification.order_number == "1234567890"
    assert notification.ds_response == "0000"
    assert notification.signature_valid is True
    assert notification.authorized is True


def test_parse_notification_declined_response_code() -> None:
    facade = RedsysFacade(settings=SETTINGS)
    post = _build_notification_post("1234567890", "0180")
    notification = facade.parse_notification(post)

    assert notification.signature_valid is True
    assert notification.authorized is False


def test_parse_notification_tampered_signature() -> None:
    facade = RedsysFacade(settings=SETTINGS)
    post = _build_notification_post("1234567890", "0000")
    post["Ds_Signature"] = post["Ds_Signature"][:-1] + (
        "A" if post["Ds_Signature"][-1] != "A" else "B"
    )
    notification = facade.parse_notification(post)

    assert notification.signature_valid is False
    assert notification.authorized is False


def test_parse_notification_missing_field_raises_key_error() -> None:
    facade = RedsysFacade(settings=SETTINGS)
    with pytest.raises(KeyError):
        facade.parse_notification({"Ds_MerchantParameters": "eyJhIjogMX0"})
