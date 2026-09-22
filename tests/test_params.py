from __future__ import annotations

from oscar_redsys.params import (
    decode_merchant_parameters,
    encode_merchant_parameters,
    encode_merchant_parameters_v1,
)


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


def test_v1_round_trip() -> None:
    data = {"DS_MERCHANT_AMOUNT": "999", "DS_MERCHANT_ORDER": "1234567890"}
    encoded = encode_merchant_parameters_v1(data)
    assert decode_merchant_parameters(encoded) == data


def test_v1_encoding_keeps_padding_when_needed() -> None:
    import base64
    import json

    # Pick a payload whose JSON length isn't a multiple of 3 bytes, so
    # standard base64 padding is actually exercised, not just tolerated.
    data = {"a": "12"}
    raw = json.dumps(data, separators=(",", ":")).encode("utf-8")
    assert len(raw) % 3 != 0  # sanity-check the fixture itself needs padding

    encoded = encode_merchant_parameters_v1(data)
    assert encoded == base64.b64encode(raw).decode()
    assert encoded.endswith("=")


def test_v1_uses_standard_alphabet_v2_uses_urlsafe_alphabet() -> None:
    import base64
    import json

    data = {"DS_MERCHANT_MERCHANTURL": "http://www.example.com/urlNotificacion.php"}
    raw = json.dumps(data, separators=(",", ":")).encode("utf-8")

    assert encode_merchant_parameters_v1(data) == base64.b64encode(raw).decode()
    assert encode_merchant_parameters(data) == base64.urlsafe_b64encode(raw).rstrip(b"=").decode()
