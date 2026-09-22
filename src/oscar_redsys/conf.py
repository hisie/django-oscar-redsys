"""Settings this package reads from the consuming Django project.

All of these come from Redsys's merchant portal (Configuración del
Comercio / "Ver clave de firma") — see the redirection manual section
6.1.1 for how to obtain them. Nothing here is guessed; every setting is
required and there is no fallback default for the secret key or merchant
code, since a wrong-but-present default is worse than a loud startup
failure.
"""

from __future__ import annotations

from dataclasses import dataclass

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

TEST_URL = "https://sis-t.redsys.es:25443/sis/realizarPago"
PRODUCTION_URL = "https://sis.redsys.es/sis/realizarPago"

SIGNATURE_VERSION = "HMAC_SHA512_V2"


@dataclass(frozen=True)
class RedsysSettings:
    merchant_code: str
    terminal: str
    secret_key: str
    currency: str
    sandbox: bool
    merchant_url: str
    url_ok: str
    url_ko: str

    @property
    def gateway_url(self) -> str:
        return TEST_URL if self.sandbox else PRODUCTION_URL


def _get_required(name: str) -> str:
    value = getattr(settings, name, None)
    if not value:
        raise ImproperlyConfigured(f"{name} must be set to use django-oscar-redsys.")
    return str(value)


def get_redsys_settings() -> RedsysSettings:
    return RedsysSettings(
        merchant_code=_get_required("REDSYS_MERCHANT_CODE"),
        terminal=_get_required("REDSYS_TERMINAL"),
        secret_key=_get_required("REDSYS_SECRET_KEY"),
        currency=getattr(settings, "REDSYS_CURRENCY", "978"),  # 978 = EUR, ISO 4217
        sandbox=bool(getattr(settings, "REDSYS_SANDBOX", True)),
        merchant_url=_get_required("REDSYS_MERCHANT_URL"),
        url_ok=_get_required("REDSYS_URL_OK"),
        url_ko=_get_required("REDSYS_URL_KO"),
    )
