from __future__ import annotations

from decimal import Decimal

import pytest
from django.test import Client
from django.urls import reverse

from oscar_redsys import signals
from oscar_redsys.models import RedsysNotification
from oscar_redsys.params import encode_merchant_parameters
from oscar_redsys.signature import sign_merchant_parameters
from oscar_redsys.views import PaymentRedirectView

SECRET_KEY = "sq7HjrUOBfKmC576"


class FixedOrderRedirectView(PaymentRedirectView):
    def get_order_number(self) -> str:
        return "1234567890"

    def get_amount(self) -> Decimal:
        return Decimal("9.99")


def _post_notification(order_number: str, ds_response: str) -> dict[str, str]:
    raw = {"Ds_Order": order_number, "Ds_Response": ds_response}
    encoded = encode_merchant_parameters(raw)
    signature = sign_merchant_parameters(SECRET_KEY, order_number, encoded)
    return {"Ds_MerchantParameters": encoded, "Ds_Signature": signature}


@pytest.mark.django_db
def test_payment_redirect_view_renders_auto_submitting_form(rf) -> None:
    request = rf.get("/whatever/")
    response = FixedOrderRedirectView.as_view()(request)
    response.render()
    content = response.content.decode()

    assert 'name="Ds_SignatureVersion" value="HMAC_SHA512_V2"' in content
    assert "Ds_MerchantParameters" in content
    assert "Ds_Signature" in content
    assert "sis-t.redsys.es" in content  # sandbox URL, per tests/settings.py


@pytest.mark.django_db
def test_notification_view_creates_record_and_fires_confirmed_signal() -> None:
    received = []
    signals.payment_confirmed.connect(lambda sender, **kw: received.append(kw), weak=False)

    client = Client()
    url = reverse("oscar_redsys:notify")
    response = client.post(url, _post_notification("1234567890", "0000"))

    assert response.status_code == 200
    assert RedsysNotification.objects.filter(order_number="1234567890").exists()
    assert len(received) == 1
    assert received[0]["order_number"] == "1234567890"


@pytest.mark.django_db
def test_notification_view_fires_declined_signal_for_error_code() -> None:
    received = []
    signals.payment_declined.connect(lambda sender, **kw: received.append(kw), weak=False)

    client = Client()
    url = reverse("oscar_redsys:notify")
    response = client.post(url, _post_notification("1234567891", "0180"))

    assert response.status_code == 200
    assert len(received) == 1


@pytest.mark.django_db
def test_notification_view_ignores_invalid_signature() -> None:
    received = []
    signals.payment_confirmed.connect(lambda sender, **kw: received.append(kw), weak=False)
    signals.payment_declined.connect(lambda sender, **kw: received.append(kw), weak=False)

    client = Client()
    url = reverse("oscar_redsys:notify")
    post = _post_notification("1234567892", "0000")
    post["Ds_Signature"] = "tampered"
    response = client.post(url, post)

    assert response.status_code == 200
    assert not RedsysNotification.objects.filter(order_number="1234567892").exists()
    assert len(received) == 0


@pytest.mark.django_db
def test_notification_view_is_idempotent_on_resend() -> None:
    received = []
    signals.payment_confirmed.connect(lambda sender, **kw: received.append(kw), weak=False)

    client = Client()
    url = reverse("oscar_redsys:notify")
    post = _post_notification("1234567893", "0000")

    first = client.post(url, post)
    second = client.post(url, post)

    assert first.status_code == 200
    assert second.status_code == 200
    assert RedsysNotification.objects.filter(order_number="1234567893").count() == 1
    assert len(received) == 1  # not fired again on the resend


@pytest.mark.django_db
def test_notification_view_rejects_malformed_payload() -> None:
    client = Client()
    url = reverse("oscar_redsys:notify")
    response = client.post(url, {"Ds_MerchantParameters": "not-valid-base64!!"})
    assert response.status_code == 400


@pytest.mark.django_db
def test_return_view_shows_pending_message_before_notification_arrives() -> None:
    client = Client()
    url = reverse("oscar_redsys:return")
    response = client.get(url, {"order_number": "9999999999"})
    assert response.status_code == 200
    assert b"still confirming" in response.content


@pytest.mark.django_db
def test_return_view_shows_confirmation_after_notification_recorded() -> None:
    client = Client()
    client.post(reverse("oscar_redsys:notify"), _post_notification("1234567894", "0000"))

    response = client.get(reverse("oscar_redsys:return"), {"order_number": "1234567894"})
    assert response.status_code == 200
    assert b"has been processed" in response.content
