"""Audit log of Redsys notifications, and the idempotency mechanism.

One row per *order number* Redsys has ever notified us about. The unique
constraint on ``order_number`` is what makes a resent notification (Redsys
explicitly documents that it can and does resend) a no-op the second time,
rather than a chance to double-register a payment: the view does a
``get_or_create`` and only fires the "payment confirmed" side effect when
``created`` is True.
"""

from __future__ import annotations

from typing import Any

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _


class RedsysNotification(models.Model):
    order_number = models.CharField(_("Order number"), max_length=12, unique=True, db_index=True)
    ds_response = models.CharField(_("Redsys response code"), max_length=8, blank=True)
    signature_valid = models.BooleanField(_("Signature valid"))
    raw_merchant_parameters: models.JSONField[dict[str, Any], dict[str, Any]] = models.JSONField(
        _("Raw merchant parameters")
    )
    created_at = models.DateTimeField(_("Created at"), auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = _("Redsys notification")
        verbose_name_plural = _("Redsys notifications")

    def __str__(self) -> str:
        return _("Redsys notification for order %(order)s (Ds_Response=%(response)s)") % {
            "order": self.order_number,
            "response": self.ds_response,
        }


class RedsysOperation(models.Model):
    """Audit log of every confirm/refund/cancellation attempt (:mod:`oscar_redsys.rest`).

    Written from ``oscar_redsys/admin.py``'s admin actions only — there is
    no other path to one of these operations, so every row here also
    records *who* on staff triggered it, for the same reason Redsys's own
    portal gates refund access per user (see the REST manual's own FAQ on
    exactly that).
    """

    class TransactionType(models.TextChoices):
        CONFIRMATION = "2", _("Confirmation")
        REFUND = "3", _("Refund")
        CANCELLATION = "9", _("Cancellation")

    order_number = models.CharField(_("Order number"), max_length=12, db_index=True)
    transaction_type = models.CharField(
        _("Transaction type"), max_length=1, choices=TransactionType.choices
    )
    amount = models.DecimalField(_("Amount"), max_digits=12, decimal_places=2)
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name=_("Requested by"),
        on_delete=models.SET_NULL,
        null=True,
        related_name="+",
    )
    success = models.BooleanField(_("Success"))
    error_code = models.CharField(_("Error code"), max_length=16, blank=True)
    ds_response = models.CharField(_("Redsys response code"), max_length=8, blank=True)
    raw_response: models.JSONField[dict[str, Any] | None, dict[str, Any] | None] = models.JSONField(
        _("Raw response"), null=True, blank=True
    )
    created_at = models.DateTimeField(_("Created at"), auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = _("Redsys operation")
        verbose_name_plural = _("Redsys operations")
        permissions = [
            ("can_refund_or_cancel", "Can refund or cancel a Redsys payment"),
        ]

    def __str__(self) -> str:
        return _("%(operation)s of order %(order)s (%(result)s)") % {
            "operation": self.get_transaction_type_display(),
            "order": self.order_number,
            "result": _("OK") if self.success else _("FAILED"),
        }
