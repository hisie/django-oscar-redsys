from __future__ import annotations

from django.urls import path

from .views import NotificationView, ReturnView

app_name = "oscar_redsys"

urlpatterns = [
    path("notify/", NotificationView.as_view(), name="notify"),
    path("return/", ReturnView.as_view(), name="return"),
]
