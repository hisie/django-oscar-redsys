from __future__ import annotations

import pytest

from oscar_redsys.response_codes import is_authorized


@pytest.mark.parametrize(
    "code",
    ["0000", "0099", "0050", "00", "99", "400", "900"],
)
def test_authorized_codes(code: str) -> None:
    assert is_authorized(code) is True


@pytest.mark.parametrize(
    "code",
    ["0100", "0101", "0180", "0190", "9999", "100", "401", "901", "-1", "abc", ""],
)
def test_declined_or_error_codes(code: str) -> None:
    assert is_authorized(code) is False
