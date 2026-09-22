"""Django admin — including the *only* path to a refund or cancellation.

Deliberately not exposed anywhere a shopper's session could reach: no
storefront view, no URL under ``oscar_redsys.urls``, nothing wired into
:mod:`oscar_redsys.views`. The two admin actions below are gated by the
``oscar_redsys.can_refund_or_cancel`` permission (see
``RedsysOperation.Meta.permissions``) on top of Django admin's own
``is_staff`` requirement — a plain staff user can view
``RedsysNotification`` rows, but can't refund or cancel one without that
permission explicitly granted, mirroring Redsys's own per-user gating of
refund access in its merchant portal (its REST manual's own FAQ: "no me
aparece la opción de devolución... no tiene permiso").
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from decimal import Decimal
from typing import Any, cast

from django.contrib import admin, messages
from django.db.models import QuerySet
from django.http import HttpRequest

from . import rest
from .facade import minor_units_to_amount
from .models import RedsysNotification, RedsysOperation

logger = logging.getLogger(__name__)


def _amount_from_notification(notification: RedsysNotification) -> Decimal | None:
    params = notification.raw_merchant_parameters
    amount_str = params.get("Ds_Amount")
    currency = params.get("Ds_Currency")
    if amount_str is None or currency is None:
        return None
    try:
        return minor_units_to_amount(str(amount_str), str(currency))
    except ValueError:
        return None


@admin.register(RedsysNotification)
class RedsysNotificationAdmin(admin.ModelAdmin):  # type: ignore[type-arg]
    list_display = ["order_number", "ds_response", "signature_valid", "created_at"]
    list_filter = ["signature_valid"]
    search_fields = ["order_number"]
    readonly_fields = [
        "order_number",
        "ds_response",
        "signature_valid",
        "raw_merchant_parameters",
        "created_at",
    ]
    actions = ["refund_selected", "cancel_selected"]

    def _has_refund_permission(self, request: HttpRequest) -> bool:
        return request.user.has_perm("oscar_redsys.can_refund_or_cancel")

    def get_actions(self, request: HttpRequest, *args: Any, **kwargs: Any) -> dict[str, Any]:
        actions = super().get_actions(request, *args, **kwargs)
        if not self._has_refund_permission(request):
            actions.pop("refund_selected", None)
            actions.pop("cancel_selected", None)
        return actions

    def _perform_operation(
        self,
        request: HttpRequest,
        queryset: QuerySet[RedsysNotification],
        *,
        transaction_type: str,
        build_request: Callable[[str, Decimal], rest.RestOperationRequest],
        verb: str,
    ) -> None:
        if not self._has_refund_permission(request):
            self.message_user(
                request,
                "You don't have permission to refund or cancel Redsys payments.",
                level=messages.ERROR,
            )
            return

        for notification in queryset:
            amount = _amount_from_notification(notification)
            if amount is None:
                self.message_user(
                    request,
                    f"Order {notification.order_number}: no recorded amount to {verb}, skipped.",
                    level=messages.WARNING,
                )
                continue

            try:
                result = rest.send_operation_request(
                    build_request(notification.order_number, amount)
                )
            except Exception:
                logger.exception(
                    "Redsys %s request failed for order %s", verb, notification.order_number
                )
                RedsysOperation.objects.create(
                    order_number=notification.order_number,
                    transaction_type=transaction_type,
                    amount=amount,
                    requested_by=cast(Any, request.user),
                    success=False,
                    error_code="request_failed",
                )
                self.message_user(
                    request,
                    f"Order {notification.order_number}: {verb} request failed — see logs.",
                    level=messages.ERROR,
                )
                continue

            success = result.error_code is None and result.authorized
            RedsysOperation.objects.create(
                order_number=notification.order_number,
                transaction_type=transaction_type,
                amount=amount,
                requested_by=cast(Any, request.user),
                success=success,
                error_code=result.error_code or "",
                ds_response=result.ds_response or "",
                raw_response=result.raw_parameters,
            )
            if success:
                self.message_user(
                    request,
                    f"Order {notification.order_number}: {verb} succeeded.",
                    level=messages.SUCCESS,
                )
            else:
                self.message_user(
                    request,
                    f"Order {notification.order_number}: {verb} failed "
                    f"({result.error_code or result.ds_response}).",
                    level=messages.ERROR,
                )

    @admin.action(description="Refund selected payments (full originally-authorized amount)")
    def refund_selected(self, request: HttpRequest, queryset: QuerySet[RedsysNotification]) -> None:
        self._perform_operation(
            request,
            queryset,
            transaction_type=RedsysOperation.TransactionType.REFUND,
            build_request=rest.build_refund_request,
            verb="refund",
        )

    @admin.action(description="Cancel selected payments")
    def cancel_selected(self, request: HttpRequest, queryset: QuerySet[RedsysNotification]) -> None:
        self._perform_operation(
            request,
            queryset,
            transaction_type=RedsysOperation.TransactionType.CANCELLATION,
            build_request=rest.build_cancellation_request,
            verb="cancellation",
        )


@admin.register(RedsysOperation)
class RedsysOperationAdmin(admin.ModelAdmin):  # type: ignore[type-arg]
    list_display = [
        "order_number",
        "transaction_type",
        "amount",
        "success",
        "requested_by",
        "created_at",
    ]
    list_filter = ["transaction_type", "success"]
    search_fields = ["order_number"]
    readonly_fields = [
        "order_number",
        "transaction_type",
        "amount",
        "requested_by",
        "success",
        "error_code",
        "ds_response",
        "raw_response",
        "created_at",
    ]

    def has_add_permission(self, request: HttpRequest) -> bool:
        return False  # written only from RedsysNotificationAdmin's actions
