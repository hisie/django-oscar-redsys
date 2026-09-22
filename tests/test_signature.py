"""Signature algorithm tests.

The first two tests are verified against Redsys's own published worked
example (redirection manual v4.1, section 6.1.2/6.1.3) — not invented
fixtures. The rest exercise this package's own guarantees (round-trip,
tamper detection, key normalization edge cases) that the manual doesn't
itself provide vectors for.
"""

from __future__ import annotations

from oscar_redsys.signature import (
    derive_operation_key,
    sign_merchant_parameters,
    signatures_match,
)

MANUAL_SECRET_KEY = "sq7HjrUOBfKmC576"


def test_derive_operation_key_matches_redsys_worked_example() -> None:
    # Manual section 6.1.2: IV all zeros, order "1234567890",
    # key "sq7HjrUOBfKmC576" -> "RWt3/IPTzYRMXsQtkiGRKg==".
    import base64

    key = derive_operation_key(MANUAL_SECRET_KEY, "1234567890")
    assert base64.b64encode(key).decode() == "RWt3/IPTzYRMXsQtkiGRKg=="


def test_derive_operation_key_truncates_long_secret_key() -> None:
    padded = derive_operation_key(MANUAL_SECRET_KEY + "-extra-garbage", "1234567890")
    exact = derive_operation_key(MANUAL_SECRET_KEY, "1234567890")
    assert padded == exact


def test_derive_operation_key_right_pads_short_secret_key() -> None:
    short_key = derive_operation_key("shortkey", "1234567890")
    manually_padded = derive_operation_key("shortkey" + "\x00" * 8, "1234567890")
    assert short_key == manually_padded


def test_derive_operation_key_changes_with_order() -> None:
    key_a = derive_operation_key(MANUAL_SECRET_KEY, "1234567890")
    key_b = derive_operation_key(MANUAL_SECRET_KEY, "1234567891")
    assert key_a != key_b


def test_sign_and_verify_round_trip() -> None:
    params = "eyJmb28iOiAiYmFyIn0"  # arbitrary base64url-looking string
    signature = sign_merchant_parameters(MANUAL_SECRET_KEY, "1234567890", params)
    assert signatures_match(MANUAL_SECRET_KEY, "1234567890", params, signature)


def test_signature_has_no_padding_or_unsafe_characters() -> None:
    params = "eyJmb28iOiAiYmFyIn0"
    signature = sign_merchant_parameters(MANUAL_SECRET_KEY, "1234567890", params)
    assert "=" not in signature
    assert "+" not in signature
    assert "/" not in signature


def test_tampering_with_parameters_invalidates_signature() -> None:
    params = "eyJmb28iOiAiYmFyIn0"
    signature = sign_merchant_parameters(MANUAL_SECRET_KEY, "1234567890", params)
    assert not signatures_match(MANUAL_SECRET_KEY, "1234567890", params + "x", signature)


def test_wrong_order_invalidates_signature() -> None:
    # A signature is diversified by order number, so replaying a valid
    # signature against a *different* order must fail even with the same
    # merchant params string.
    params = "eyJmb28iOiAiYmFyIn0"
    signature = sign_merchant_parameters(MANUAL_SECRET_KEY, "1234567890", params)
    assert not signatures_match(MANUAL_SECRET_KEY, "0000000001", params, signature)


def test_wrong_secret_key_invalidates_signature() -> None:
    params = "eyJmb28iOiAiYmFyIn0"
    signature = sign_merchant_parameters(MANUAL_SECRET_KEY, "1234567890", params)
    assert not signatures_match("a-different-key1", "1234567890", params, signature)
