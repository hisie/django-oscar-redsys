from __future__ import annotations

import pytest

from oscar_redsys.order_number import validate_order_number


@pytest.mark.parametrize(
    "order_number",
    [
        "1234",  # minimum length, all numeric
        "1234567890",
        "123456789012",  # maximum length, 12 chars
        "1234ABCabc12",
        "0000AAAAaaaa",
    ],
)
def test_valid_order_numbers(order_number: str) -> None:
    validate_order_number(order_number)  # must not raise


@pytest.mark.parametrize(
    "order_number",
    [
        "",
        "123",  # too short, and first-4-numeric can't even be satisfied
        "12a4567890",  # non-numeric within the first 4 characters
        "12345678901234",  # too long
        "1234-567890",  # punctuation not allowed
        "1234 567890",  # whitespace not allowed
        "1234ü567890",  # non-ASCII not allowed
    ],
)
def test_invalid_order_numbers_raise(order_number: str) -> None:
    with pytest.raises(ValueError):
        validate_order_number(order_number)
