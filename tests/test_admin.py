from __future__ import annotations

from typing import Any
from unittest.mock import patch

import pytest
from django.contrib.admin.sites import AdminSite
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.contrib.messages.storage.fallback import FallbackStorage
from django.http import HttpRequest

from oscar_redsys.admin import RedsysNotificationAdmin
from oscar_redsys.models import RedsysNotification, RedsysOperation
from oscar_redsys.rest import RestOperationResult

User = get_user_model()


def _make_request(rf: Any, user: Any) -> HttpRequest:
    request = rf.get("/admin/oscar_redsys/redsysnotification/")
    request.user = user
    request.session = {}  # type: ignore[assignment]
    messages = FallbackStorage(request)
    request._messages = messages  # type: ignore[attr-defined]
    return request


@pytest.fixture
def admin_instance() -> RedsysNotificationAdmin:
    return RedsysNotificationAdmin(RedsysNotification, AdminSite())


@pytest.fixture
def staff_user_without_permission(db: None) -> Any:
    return User.objects.create_user(username="staff-no-perm", password="x", is_staff=True)


@pytest.fixture
def staff_user_with_permission(db: None) -> Any:
    user = User.objects.create_user(username="staff-with-perm", password="x", is_staff=True)
    permission = Permission.objects.get(
        codename="can_refund_or_cancel", content_type__app_label="oscar_redsys"
    )
    user.user_permissions.add(permission)
    return user


@pytest.fixture
def notification(db: None) -> RedsysNotification:
    return RedsysNotification.objects.create(
        order_number="1234567890",
        ds_response="0000",
        signature_valid=True,
        raw_merchant_parameters={
            "Ds_Order": "1234567890",
            "Ds_Response": "0000",
            "Ds_Amount": "999",
            "Ds_Currency": "978",
        },
    )


@pytest.mark.django_db
def test_refund_action_hidden_without_permission(
    rf: Any, admin_instance: RedsysNotificationAdmin, staff_user_without_permission: Any
) -> None:
    request = _make_request(rf, staff_user_without_permission)
    actions = admin_instance.get_actions(request)
    assert "refund_selected" not in actions
    assert "cancel_selected" not in actions


@pytest.mark.django_db
def test_refund_action_visible_with_permission(
    rf: Any, admin_instance: RedsysNotificationAdmin, staff_user_with_permission: Any
) -> None:
    request = _make_request(rf, staff_user_with_permission)
    actions = admin_instance.get_actions(request)
    assert "refund_selected" in actions
    assert "cancel_selected" in actions


@pytest.mark.django_db
def test_refund_selected_denied_without_permission_creates_no_operation(
    rf: Any,
    admin_instance: RedsysNotificationAdmin,
    staff_user_without_permission: Any,
    notification: RedsysNotification,
) -> None:
    request = _make_request(rf, staff_user_without_permission)
    queryset = RedsysNotification.objects.filter(pk=notification.pk)

    with patch("oscar_redsys.admin.rest.send_operation_request") as mock_send:
        admin_instance.refund_selected(request, queryset)

    mock_send.assert_not_called()
    assert RedsysOperation.objects.count() == 0


@pytest.mark.django_db
def test_refund_selected_success_creates_operation_log(
    rf: Any,
    admin_instance: RedsysNotificationAdmin,
    staff_user_with_permission: Any,
    notification: RedsysNotification,
) -> None:
    request = _make_request(rf, staff_user_with_permission)
    queryset = RedsysNotification.objects.filter(pk=notification.pk)
    fake_result = RestOperationResult(
        error_code=None,
        order_number="1234567890",
        ds_response="0900",
        signature_valid=True,
        authorized=True,
        raw_parameters={"Ds_Order": "1234567890"},
    )

    with patch("oscar_redsys.admin.rest.send_operation_request", return_value=fake_result):
        admin_instance.refund_selected(request, queryset)

    operation = RedsysOperation.objects.get()
    assert operation.order_number == "1234567890"
    assert operation.transaction_type == RedsysOperation.TransactionType.REFUND
    assert operation.success is True
    assert operation.requested_by == staff_user_with_permission


@pytest.mark.django_db
def test_cancel_selected_records_failure_on_decline(
    rf: Any,
    admin_instance: RedsysNotificationAdmin,
    staff_user_with_permission: Any,
    notification: RedsysNotification,
) -> None:
    request = _make_request(rf, staff_user_with_permission)
    queryset = RedsysNotification.objects.filter(pk=notification.pk)
    fake_result = RestOperationResult(error_code="SIS0093")

    with patch("oscar_redsys.admin.rest.send_operation_request", return_value=fake_result):
        admin_instance.cancel_selected(request, queryset)

    operation = RedsysOperation.objects.get()
    assert operation.transaction_type == RedsysOperation.TransactionType.CANCELLATION
    assert operation.success is False
    assert operation.error_code == "SIS0093"


@pytest.mark.django_db
def test_refund_selected_skips_notification_with_no_recorded_amount(
    rf: Any, admin_instance: RedsysNotificationAdmin, staff_user_with_permission: Any
) -> None:
    notification_without_amount = RedsysNotification.objects.create(
        order_number="1234567891",
        ds_response="0000",
        signature_valid=True,
        raw_merchant_parameters={"Ds_Order": "1234567891", "Ds_Response": "0000"},
    )
    request = _make_request(rf, staff_user_with_permission)
    queryset = RedsysNotification.objects.filter(pk=notification_without_amount.pk)

    with patch("oscar_redsys.admin.rest.send_operation_request") as mock_send:
        admin_instance.refund_selected(request, queryset)

    mock_send.assert_not_called()
    assert RedsysOperation.objects.count() == 0


@pytest.mark.django_db
def test_refund_selected_skips_notification_with_unknown_currency(
    rf: Any, admin_instance: RedsysNotificationAdmin, staff_user_with_permission: Any
) -> None:
    notification_unknown_currency = RedsysNotification.objects.create(
        order_number="1234567892",
        ds_response="0000",
        signature_valid=True,
        raw_merchant_parameters={
            "Ds_Order": "1234567892",
            "Ds_Response": "0000",
            "Ds_Amount": "999",
            "Ds_Currency": "840",  # USD — not in this package's known-exponent table
        },
    )
    request = _make_request(rf, staff_user_with_permission)
    queryset = RedsysNotification.objects.filter(pk=notification_unknown_currency.pk)

    with patch("oscar_redsys.admin.rest.send_operation_request") as mock_send:
        admin_instance.refund_selected(request, queryset)

    mock_send.assert_not_called()
    assert RedsysOperation.objects.count() == 0


@pytest.mark.django_db
def test_refund_selected_handles_request_exception(
    rf: Any,
    admin_instance: RedsysNotificationAdmin,
    staff_user_with_permission: Any,
    notification: RedsysNotification,
) -> None:
    request = _make_request(rf, staff_user_with_permission)
    queryset = RedsysNotification.objects.filter(pk=notification.pk)

    with patch(
        "oscar_redsys.admin.rest.send_operation_request", side_effect=RuntimeError("network down")
    ):
        admin_instance.refund_selected(request, queryset)

    operation = RedsysOperation.objects.get()
    assert operation.success is False
    assert operation.error_code == "request_failed"


@pytest.mark.django_db
def test_redsys_operation_admin_has_no_add_permission(rf: Any) -> None:
    from oscar_redsys.admin import RedsysOperationAdmin

    admin_instance = RedsysOperationAdmin(RedsysOperation, AdminSite())
    request = rf.get("/admin/oscar_redsys/redsysoperation/")
    assert admin_instance.has_add_permission(request) is False
