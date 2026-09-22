# django-oscar-redsys

Redsys (TPV Virtual) payment integration for [django-oscar](https://github.com/django-oscar/django-oscar),
using Redsys's **redirection** integration method (the customer's browser
is sent to a Redsys-hosted payment page, per Redsys's own EMV 3DS/SCA
support for that flow).

Supports Django 5.2 (LTS) and django-oscar 4.2 only — no support for
older/unmaintained versions.

## What this package does, and doesn't, do

It builds and signs the `Ds_MerchantParameters`/`Ds_Signature` payload
for a redirect (`oscar_redsys.facade.RedsysFacade`), provides the view
that receives and verifies Redsys's async notification
(`oscar_redsys.views.NotificationView`), and fires a
`payment_confirmed`/`payment_declined` Django signal
(`oscar_redsys.signals`) for the host project to hook into its own order
flow.

It does **not** decide what "payment confirmed" means for your Order
model, doesn't place orders, and doesn't ever trust the browser-redirect
(`Ds_Merchant_UrlOK`/`Ds_Merchant_UrlKO`) path to confirm a payment — only
the signed, server-to-server notification does that. See
`oscar_redsys/views.py`'s module docstring for why.

## Installation

```
uv add django-oscar-redsys
```

Add to `INSTALLED_APPS`:

```python
INSTALLED_APPS = [
    ...,
    "oscar_redsys",
]
```

Required settings (from Redsys's merchant portal — "Configuración del
Comercio" → "Ver clave de firma"):

```python
REDSYS_MERCHANT_CODE = "999008881"
REDSYS_TERMINAL = "1"
REDSYS_SECRET_KEY = "..."          # keep this out of version control
REDSYS_SANDBOX = True              # False in production
REDSYS_MERCHANT_URL = "https://example.com/redsys/notify/"
REDSYS_URL_OK = "https://example.com/redsys/return/?ok=1"
REDSYS_URL_KO = "https://example.com/redsys/return/?ok=0"
# REDSYS_CURRENCY defaults to "978" (EUR, ISO 4217)
```

Wire the notification/return endpoints:

```python
urlpatterns = [
    path("redsys/", include("oscar_redsys.urls")),
]
```

Run this package's migration (`oscar_redsys.RedsysNotification`, the
notification audit/idempotency log) as part of the host project's own
`migrate`.

## Building the redirect

Subclass `oscar_redsys.views.PaymentRedirectView`:

```python
from decimal import Decimal
from oscar_redsys.views import PaymentRedirectView


class CheckoutPaymentView(PaymentRedirectView):
    def get_order_number(self) -> str:
        return self.request.basket.order_number  # whatever generates yours

    def get_amount(self) -> Decimal:
        return self.request.basket.total_incl_tax
```

This renders an auto-submitting form pointed at Redsys's payment page.

## Handling the outcome

```python
from django.dispatch import receiver
from oscar_redsys.signals import payment_confirmed, payment_declined


@receiver(payment_confirmed)
def on_payment_confirmed(sender, order_number, notification, **kwargs):
    # place the order / trigger the Dolibarr sync chain / etc.
    ...


@receiver(payment_declined)
def on_payment_declined(sender, order_number, notification, **kwargs):
    ...
```

Both signals fire **at most once** per order number — a resent Redsys
notification (Redsys explicitly documents that it can resend) is a no-op
the second time, per `RedsysNotification`'s uniqueness on `order_number`.

## Signature algorithm

`HMAC_SHA512_V2`, per Redsys's "TPV-Virtual Manual de Integración -
Redirección" (v4.1, 24/09/2025): an AES-128-CBC-derived per-operation
key (merchant secret key, forced to 16 bytes; diversified by the order
number; zero IV), then HMAC-SHA512 of the base64url-encoded
`Ds_MerchantParameters` string, base64url-encoded with padding stripped.
See `oscar_redsys/signature.py`'s module docstring and
`tests/test_signature.py` (verified against Redsys's own published
worked example).

## Development

```
uv sync
uv run pytest
uv run mypy src
uv run black --check src tests
uv run isort --check src tests
```

## License

BSD-3-Clause.
