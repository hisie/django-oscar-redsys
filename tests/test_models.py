from __future__ import annotations

import pytest

from oscar_redsys.models import RedsysNotification, RedsysOperation


@pytest.mark.django_db
def test_redsys_notification_str() -> None:
    notification = RedsysNotification.objects.create(
        order_number="1234567890",
        ds_response="0000",
        signature_valid=True,
        raw_merchant_parameters={},
    )
    assert "1234567890" in str(notification)
    assert "0000" in str(notification)


@pytest.mark.django_db
def test_redsys_operation_str() -> None:
    operation = RedsysOperation.objects.create(
        order_number="1234567890",
        transaction_type=RedsysOperation.TransactionType.REFUND,
        amount="9.99",
        success=True,
    )
    text = str(operation)
    assert "1234567890" in text
    assert "OK" in text
