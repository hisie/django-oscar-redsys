from __future__ import annotations

import pytest
from django.core.exceptions import ImproperlyConfigured
from django.test import override_settings

from oscar_redsys.conf import get_redsys_settings


def test_get_redsys_settings_reads_from_django_settings() -> None:
    settings = get_redsys_settings()
    assert settings.merchant_code == "999008881"
    assert settings.terminal == "1"
    assert settings.secret_key == "sq7HjrUOBfKmC576"
    assert settings.currency == "978"
    assert settings.sandbox is True
    assert settings.gateway_url == "https://sis-t.redsys.es:25443/sis/realizarPago"


@override_settings(REDSYS_SANDBOX=False)
def test_get_redsys_settings_production_gateway() -> None:
    assert get_redsys_settings().gateway_url == "https://sis.redsys.es/sis/realizarPago"


@override_settings(REDSYS_MERCHANT_CODE=None)
def test_get_redsys_settings_missing_required_value_raises() -> None:
    with pytest.raises(ImproperlyConfigured):
        get_redsys_settings()
