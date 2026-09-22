from __future__ import annotations

from django.apps import AppConfig


class OscarRedsysConfig(AppConfig):
    name = "oscar_redsys"
    label = "oscar_redsys"
    verbose_name = "Redsys payment integration"
    default_auto_field = "django.db.models.BigAutoField"
