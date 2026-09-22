from __future__ import annotations

from django.urls import include, path

urlpatterns = [
    path("redsys/", include("oscar_redsys.urls")),
]
