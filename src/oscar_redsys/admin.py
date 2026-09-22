from __future__ import annotations

from django.contrib import admin

from .models import RedsysNotification


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
