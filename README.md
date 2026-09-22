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

Run this package's migrations (`oscar_redsys.RedsysNotification`, the
notification audit/idempotency log, and `oscar_redsys.RedsysOperation`,
the refund/cancellation audit log) as part of the host project's own
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
`get_order_number()` must return Redsys's own format: at most 12
characters, the first 4 numeric, the rest (if any) plain ASCII
digits/letters — validated up front (`ValueError` if not), rather than
letting a malformed order fail opaquely at Redsys's end.

## EMV3DS / SCA (optional, but improves checkout friction)

PSD2 requires Strong Customer Authentication (SCA) on most card
payments; Redsys's EMV 3DS flow decides per transaction whether the
issuer can authenticate the cardholder "frictionlessly" or must
"challenge" them. Neither of the following is required for a payment to
work, but supplying them lets more transactions go frictionless:

```python
from oscar_redsys.emv3ds import Emv3dsData, MobilePhone, ScaExemption


class CheckoutPaymentView(PaymentRedirectView):
    ...

    def get_emv3ds(self) -> Emv3dsData:
        return Emv3dsData(
            ship_addr_country="724",  # numeric ISO 3166-1, e.g. Spain
            cardholder_name=self.request.user.get_full_name(),
            email=self.request.user.email,
            mobile_phone=MobilePhone(country_code="34", subscriber="600123456"),
        )

    def get_sca_exemption(self) -> str | None:
        if self.get_amount() <= Decimal("30.00"):
            return ScaExemption.LOW_VALUE
        return None
```

`ScaExemption` only defines the three values confirmed against Redsys's
own PSD2/SCA documentation (`LWV`, `TRA`, `MIT`) — pass any other code
Redsys documents as a plain string, it isn't restricted to these.

## Consumer language (cosmetic)

`get_consumer_language()` sets what language *Redsys's own hosted pages*
(the payment form, the "Recibo Redsys" confirmation screen) render in —
it has no effect on the payment itself:

```python
from oscar_redsys.language import ConsumerLanguage


class CheckoutPaymentView(PaymentRedirectView):
    ...

    def get_consumer_language(self) -> str | None:
        return ConsumerLanguage.SPANISH if self.request.LANGUAGE_CODE == "es" else ConsumerLanguage.ENGLISH
```

## Handling the outcome

```python
from django.dispatch import receiver
from oscar_redsys.signals import payment_confirmed, payment_declined


@receiver(payment_confirmed)
def on_payment_confirmed(sender, order_number, notification, **kwargs):
    # place the order / trigger the Dolibarr sync chain / etc.
    # See "Common pitfall" below before reading anything session-backed here.
    ...


@receiver(payment_declined)
def on_payment_declined(sender, order_number, notification, **kwargs):
    ...
```

Both signals fire **at most once** per order number — a resent Redsys
notification (Redsys explicitly documents that it can resend) is a no-op
the second time, per `RedsysNotification`'s uniqueness on `order_number`.

### Common pitfall: `payment_confirmed` has no browser session

`payment_confirmed` fires from `NotificationView` handling Redsys's async
server-to-server POST — there is no browser, no cookies, no session
attached to that request at all. If your receiver's "place the order"
logic reads anything from your checkout framework's *session-backed*
state (e.g. django-oscar's own `checkout_session` — the shipping
address, billing address and shipping method a customer chose only ever
live there until an order is actually placed, per
`CheckoutSessionData.get_shipping_address`'s own docstring), it will find
nothing there. Concretely: a customer who pays and then closes their
browser before your own return/thank-you view ever runs would have a
confirmed Redsys payment with **no corresponding order** — Redsys's own
"síncrona" notification default (the async notification is delivered
*before* the browser redirect, per the redirection manual's section 4.1)
doesn't rescue this, since it only orders the two *deliveries* relative
to each other; it can't force the customer's *browser* to actually
follow the redirect back.

This isn't something this package can fix for you — it doesn't know
anything about your order model or checkout framework — but it's a real
trap worth avoiding deliberately rather than discovering in production:

1. **Before** redirecting to Redsys (wherever you build the
   `PaymentRequest`/raise your framework's redirect), write everything
   your order-placement logic will need to a durable model of your own
   — not just the session. At minimum: the shipping/billing address, the
   shipping method, and the exact amount you're about to charge.
2. Snapshot that amount rather than planning to recompute it later. A
   frozen/locked basket's *contents* usually can't change once payment
   starts, but its *prices* often aren't frozen too — recomputing the
   total from the basket at confirmation time (which can be minutes
   after the redirect) risks placing an order for a different amount
   than what Redsys actually charged, if a price changed in between.
3. In your `payment_confirmed` receiver, read from that durable model,
   never from a session. Make the resulting "place the order" function
   idempotent and callable from more than one place — the signal is the
   normal trigger, but keeping a return-view fallback that calls the
   *same* function is what makes a delayed or lost webhook harmless
   rather than silently dropping the order.

## Refunds and cancellations — staff/admin only, never storefront

Unlike a payment, a refund or cancellation has no browser redirect at
all: it's a direct server-to-server call (`oscar_redsys.rest`, Redsys's
separate REST channel) referencing the original order, with no customer
involved. This package deliberately exposes it **only** as two Django
admin actions on `RedsysNotification` — "Refund selected payments" and
"Cancel selected payments" — never as a storefront view or URL a shopper
could reach.

Both actions are gated by the `oscar_redsys.can_refund_or_cancel`
permission on top of Django admin's own `is_staff` requirement — a
plain staff user can view payment records but can't trigger either
action without that permission explicitly granted (grant it via Django's
own admin, `Permission` model, or a group). Every attempt, successful or
not, is logged to `RedsysOperation` (who triggered it, when, the amount,
the outcome) — nothing here fires silently.

Refunds default to the full originally-authorized amount (recovered from
the stored notification's own `Ds_Amount`/`Ds_Currency`); there's no
partial-refund UI yet — see `oscar_redsys.rest.build_refund_request` if
you need a different amount from your own code.

## Signature algorithm

Two versions, both verified byte-exact against Redsys's own published
worked examples in `tests/test_signature.py` — see
`oscar_redsys/signature.py`'s module docstring for the full detail:

- **V2** (`HMAC_SHA512_V2`) for the redirection/browser flow, per
  "TPV-Virtual Manual de Integración - Redirección" (v4.1, 24/09/2025).
- **V1** (`HMAC_SHA512_V1`) for the server-to-server REST channel
  (confirm/refund/cancel), per "TPV-Virtual Manual Integración-REST"
  (v4.0.1.1, 17/10/2025).

Both derive a per-operation key via AES-128-CBC (merchant secret key
forced to 16 bytes, zero IV, diversified by the order number, then
**base64-encoded** — that base64 string's ASCII bytes are the actual
HMAC key, not the raw ciphertext, a detail easy to get wrong silently
since a self-consistent sign/verify round trip "works" either way and
only breaks against Redsys itself). They differ only in the final
encoding: V2 uses URL-safe base64 with padding stripped, V1 uses
standard base64 with padding kept.

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
