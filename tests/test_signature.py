"""Signature algorithm tests.

The first two tests are verified against Redsys's own published worked
example (redirection manual v4.1, section 6.1.2/6.1.3) — not invented
fixtures; the manual's example was re-extracted with ``pdftotext`` rather
than read off the rendered PDF page images, since an earlier
transcription-by-eye of the same example (a long, low-entropy base64
string) silently swapped a lowercase ``l`` for an ``i`` and missed a real
bug this test suite's own round-trip tests couldn't otherwise have caught
(see the module docstring in ``signature.py``). The rest exercise this
package's own guarantees (round-trip, tamper detection, key
normalization edge cases) that the manual doesn't itself provide vectors
for.
"""

from __future__ import annotations

from oscar_redsys.signature import (
    derive_operation_key,
    sign_merchant_parameters,
    sign_merchant_parameters_v1,
    signatures_match,
    signatures_match_v1,
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


def test_sign_merchant_parameters_matches_redsys_worked_example_end_to_end() -> None:
    # Manual section 6.1.3 — the full worked example, params string and
    # signature both re-extracted with pdftotext against the source PDF.
    params = (
        "eyJEU19NRVJDSEFOVF9BTU9VTlQiOiI5OTkiLCJEU19NRVJDSEFOVF9PUkRFUiI6IjEyMzQ1Njc4OTAi"
        "LCJEU19NRVJDSEFOVF9NRVJDSEFOVENPREUiOiI5OTkwMDg4ODEiLCJEU19NRVJDSEFOVF9DVVJSRU5DWSI6"
        "Ijk3OCIsIkRTX01FUkNIQU5UX1RSQU5TQUNUSU9OVFlQRSI6IjAiLCJEU19NRVJDSEFOVF9URVJNSU5BTCI6"
        "IjEiLCJEU19NRVJDSEFOVF9NRVJDSEFOVFVSTCI6Imh0dHA6XC9cL3d3dy5wcnVlYmEuY29tXC91cmxOb3Rp"
        "ZmljYWNpb24ucGhwIiwiRFNfTUVSQ0hBTlRfVVJMT0siOiJodHRwOlwvXC93d3cucHJ1ZWJhLmNvbVwvdXJs"
        "T0sucGhwIiwiRFNfTUVSQ0hBTlRfVVJMS08iOiJodHRwOlwvXC93d3cucHJ1ZWJhLmNvbVwvdXJsS08ucGhw"
        "In0"
    )
    expected_signature = (
        "Vjo02eSWq249IeZZp3R-ArFnGLhKY0OuzDDlx1BuVtZDC2yhczA7_11uZhsYzLZBCMFAz8u8uzGDX3AErHKmmw"
    )
    signature = sign_merchant_parameters(MANUAL_SECRET_KEY, "1234567890", params)
    assert signature == expected_signature


def test_sign_merchant_parameters_v1_matches_redsys_rest_worked_example() -> None:
    # REST manual (v4.0.1.1, section 3) worked example — same key + order
    # as the V2 example above, reused there too. Note the params string
    # here is plain (padded) Base64, not URL-safe, per that manual's own
    # wording ("Base 64", not "Base 64 URL-safe") — unlike the V2 example.
    params = (
        "eyJEU19NRVJDSEFOVF9BTU9VTlQiOiI5OTkiLCJEU19NRVJDSEFOVF9PUkRFUiI6IjEyMzQ1Njc4OTAi"
        "LCJEU19NRVJDSEFOVF9NRVJDSEFOVENPREUiOiI5OTkwMDg4ODEiLCJEU19NRVJDSEFOVF9DVVJSRU5DWSI6"
        "Ijk3OCIsIkRTX01FUkNIQU5UX1RSQU5TQUNUSU9OVFlQRSI6IjAiLCJEU19NRVJDSEFOVF9URVJNSU5BTCI6"
        "IjEiLCJEU19NRVJDSEFOVF9NRVJDSEFOVFVSTCI6Imh0dHA6XC9cL3d3dy5wcnVlYmEuY29tXC91cmxOb3Rp"
        "ZmljYWNpb24ucGhwIiwiRFNfTUVSQ0hBTlRfVVJMT0siOiJodHRwOlwvXC93d3cucHJ1ZWJhLmNvbVwvdXJs"
        "T0sucGhwIiwiRFNfTUVSQ0hBTlRfVVJMS08iOiJodHRwOlwvXC93d3cucHJ1ZWJhLmNvbVwvdXJsS08ucGhw"
        "In0="
    )
    expected_signature = (
        "sNshBlGLKfv04FBXKt_lMaueFt_yA7VZ1Mw4USg4HiLehAdiQ8xUt5pEM-oHvXCBNZJKZkk7ogzPjhxDW3hAEQ=="
    )
    signature = sign_merchant_parameters_v1(MANUAL_SECRET_KEY, "1234567890", params)
    assert signature == expected_signature


def test_v1_signature_keeps_base64_padding() -> None:
    params = "eyJmb28iOiAiYmFyIn0="
    signature = sign_merchant_parameters_v1(MANUAL_SECRET_KEY, "1234567890", params)
    assert signature.endswith("==") or signature.endswith("=")


def test_v1_sign_and_verify_round_trip() -> None:
    params = "eyJmb28iOiAiYmFyIn0="
    signature = sign_merchant_parameters_v1(MANUAL_SECRET_KEY, "1234567890", params)
    assert signatures_match_v1(MANUAL_SECRET_KEY, "1234567890", params, signature)


def test_v1_tampering_invalidates_signature() -> None:
    params = "eyJmb28iOiAiYmFyIn0="
    signature = sign_merchant_parameters_v1(MANUAL_SECRET_KEY, "1234567890", params)
    assert not signatures_match_v1(MANUAL_SECRET_KEY, "1234567890", params + "x", signature)


def test_v1_and_v2_signatures_differ_for_the_same_input() -> None:
    params = "eyJmb28iOiAiYmFyIn0"
    v1 = sign_merchant_parameters_v1(MANUAL_SECRET_KEY, "1234567890", params)
    v2 = sign_merchant_parameters(MANUAL_SECRET_KEY, "1234567890", params)
    assert v1.rstrip("=") == v2  # same digest, only the padding differs


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


def test_lenient_comparison_tolerates_punctuation_differences() -> None:
    # Not a real Redsys scenario reproduced here — just proving the
    # sanitize-then-compare mechanics work, per signature.py's own
    # "Lenient comparison" docstring caveat about when this is (and isn't)
    # an appropriate thing to enable.
    params = "eyJmb28iOiAiYmFyIn0"
    signature = sign_merchant_parameters(MANUAL_SECRET_KEY, "1234567890", params)
    mangled = signature.replace("-", " ").replace("_", "+")  # punctuation-only change
    assert not signatures_match(MANUAL_SECRET_KEY, "1234567890", params, mangled)
    assert signatures_match(MANUAL_SECRET_KEY, "1234567890", params, mangled, lenient=True)


def test_lenient_comparison_still_rejects_a_genuinely_different_signature() -> None:
    params = "eyJmb28iOiAiYmFyIn0"
    signature = sign_merchant_parameters(MANUAL_SECRET_KEY, "1234567890", params)
    tampered = "a" + signature[1:]  # an actual alphanumeric character changed
    assert not signatures_match(MANUAL_SECRET_KEY, "1234567890", params, tampered, lenient=True)


def test_v1_lenient_comparison_tolerates_punctuation_differences() -> None:
    params = "eyJmb28iOiAiYmFyIn0="
    signature = sign_merchant_parameters_v1(MANUAL_SECRET_KEY, "1234567890", params)
    mangled = signature.replace("=", "").replace("/", " ")
    assert signatures_match_v1(MANUAL_SECRET_KEY, "1234567890", params, mangled, lenient=True)
