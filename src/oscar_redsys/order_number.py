"""``Ds_Merchant_Order`` format validation.

Confirmed against Redsys's own integration manuals and cross-checked
against several independent third-party integrations that all agree:
at most 12 characters, the first 4 of which must be numeric, and the
remaining characters (if any) restricted to plain ASCII digits and
letters (no punctuation, no non-ASCII). Validating this here, before a
request ever reaches Redsys, turns a guaranteed-but-opaque rejection at
Redsys's end into an immediate, specific local error.
"""

from __future__ import annotations

import re

_ORDER_NUMBER_PATTERN = re.compile(r"^[0-9]{4}[0-9A-Za-z]{0,8}$")


def validate_order_number(order_number: str) -> None:
    if not _ORDER_NUMBER_PATTERN.fullmatch(order_number):
        raise ValueError(
            f"Invalid Ds_Merchant_Order {order_number!r}: must be 4-12 characters, the "
            "first 4 numeric, the rest (if any) plain ASCII digits/letters only."
        )
