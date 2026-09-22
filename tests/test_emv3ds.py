from __future__ import annotations

from oscar_redsys.emv3ds import Emv3dsData, MobilePhone, ScaExemption


def test_mobile_phone_to_dict() -> None:
    phone = MobilePhone(country_code="34", subscriber="600123456")
    assert phone.to_dict() == {"cc": "34", "subscriber": "600123456"}


def test_emv3ds_to_dict_matches_manuals_field_names() -> None:
    data = Emv3dsData(
        ship_addr_country="840",
        ship_addr_city="Ship City Name",
        ship_addr_state="CO",
        ship_addr_line1="Ship Address Line 1",
        ship_addr_line2="Ship Address Line 2",
        ship_addr_line3="Ship Address Line 3",
        cardholder_name="Cardholder Name",
        email="example@example.com",
        mobile_phone=MobilePhone(country_code="123", subscriber="123456789"),
    )
    assert data.to_dict() == {
        "shipAddrCountry": "840",
        "shipAddrCity": "Ship City Name",
        "shipAddrState": "CO",
        "shipAddrLine1": "Ship Address Line 1",
        "shipAddrLine2": "Ship Address Line 2",
        "shipAddrLine3": "Ship Address Line 3",
        "cardholderName": "Cardholder Name",
        "email": "example@example.com",
        "mobilePhone": {"cc": "123", "subscriber": "123456789"},
    }


def test_emv3ds_to_dict_omits_unset_fields() -> None:
    data = Emv3dsData(email="example@example.com")
    assert data.to_dict() == {"email": "example@example.com"}


def test_emv3ds_to_dict_empty_when_nothing_set() -> None:
    assert Emv3dsData().to_dict() == {}


def test_emv3ds_extra_fields_are_merged_in() -> None:
    data = Emv3dsData(email="example@example.com", extra={"acctType": "02"})
    assert data.to_dict() == {"email": "example@example.com", "acctType": "02"}


def test_sca_exemption_constants() -> None:
    assert ScaExemption.LOW_VALUE == "LWV"
    assert ScaExemption.TRANSACTION_RISK_ANALYSIS == "TRA"
    assert ScaExemption.MERCHANT_INITIATED == "MIT"
