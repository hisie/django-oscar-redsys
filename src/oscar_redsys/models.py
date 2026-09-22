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

from django.db import models


class RedsysNotification(models.Model):
    order_number = models.CharField(max_length=12, unique=True, db_index=True)
    ds_response = models.CharField(max_length=8, blank=True)
    signature_valid = models.BooleanField()
    raw_merchant_parameters: models.JSONField[dict[str, Any], dict[str, Any]] = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"Redsys notification for order {self.order_number} (Ds_Response={self.ds_response})"
