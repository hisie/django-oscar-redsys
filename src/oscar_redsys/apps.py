from __future__ import annotations

from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class OscarRedsysConfig(AppConfig):
    name = "oscar_redsys"
    label = "oscar_redsys"
    verbose_name = _("Redsys payment integration")
    default_auto_field = "django.db.models.BigAutoField"
