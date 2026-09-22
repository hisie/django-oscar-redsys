from __future__ import annotations

from oscar_redsys.params import decode_merchant_parameters, encode_merchant_parameters


def test_round_trip() -> None:
    data = {"DS_MERCHANT_AMOUNT": "999", "DS_MERCHANT_ORDER": "1234567890"}
    encoded = encode_merchant_parameters(data)
    assert decode_merchant_parameters(encoded) == data


def test_encoded_form_has_no_padding_plus_or_slash() -> None:
    # Long/varied enough input to be likely to contain +//= under standard
    # base64 if urlsafe encoding weren't actually being used.
    data = {"DS_MERCHANT_MERCHANTURL": "http://www.example.com/urlNotificacion.php?a=b&c=d"}
    encoded = encode_merchant_parameters(data)
    assert "=" not in encoded
    assert "+" not in encoded
    assert "/" not in encoded


def test_decode_handles_missing_padding_of_any_length() -> None:
    for data in (
        {"a": "1"},
        {"a": "12"},
        {"a": "123"},
        {"a": "1234"},
    ):
        encoded = encode_merchant_parameters(data)
        assert decode_merchant_parameters(encoded) == data
