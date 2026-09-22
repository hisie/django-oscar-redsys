"""Views for the redirection flow.

Two of these matter for correctness; the third is cosmetic:

- :class:`PaymentRedirectView` sends the customer to Redsys.
- :class:`NotificationView` is the *only* place a payment is ever
  confirmed — Redsys's async server-to-server POST (section 4.1). This is
  deliberately the sole trigger for :data:`oscar_redsys.signals.payment_confirmed`.
- :class:`ReturnView` handles the browser bouncing back via
  ``Ds_Merchant_UrlOK``/``Ds_Merchant_UrlKO``. The manual is explicit
  (section 8, "Nota Importante") that this path must never be used to
  decide whether an order was paid — the customer's browser can vanish
  before ever reaching it, and its own params are trivially replayable by
  the customer themselves. It exists only to show the customer something
  once the async notification (which may not have arrived yet) settles.
"""

from __future__ import annotations

import logging
from decimal import Decimal
from typing import Any

from django.http import HttpRequest, HttpResponse, HttpResponseBadRequest
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import TemplateView

from . import signals
from .facade import Notification, RedsysFacade
from .models import RedsysNotification

logger = logging.getLogger(__name__)


class PaymentRedirectView(TemplateView):
    """Renders the auto-submitting form that sends the customer to Redsys.

    Subclasses must implement :meth:`get_order_number` and
    :meth:`get_amount`; override :meth:`get_redirect_urls` if the
    per-request OK/KO/notification URLs aren't the ones from settings.
    """

    template_name = "oscar_redsys/redirect.html"
    facade_class = RedsysFacade

    def get_order_number(self) -> str:
        raise NotImplementedError

    def get_amount(self) -> Decimal:
        raise NotImplementedError

    def get_redirect_urls(self) -> dict[str, str]:
        return {}

    def get_extra_parameters(self) -> dict[str, Any]:
        return {}

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        facade = self.facade_class()
        payment_request = facade.build_payment_request(
            order_number=self.get_order_number(),
            amount=self.get_amount(),
            extra_parameters=self.get_extra_parameters(),
            **self.get_redirect_urls(),
        )
        context["payment_request"] = payment_request
        return context


@method_decorator(csrf_exempt, name="dispatch")
class NotificationView(View):
    """Redsys's server-to-server notification endpoint (Ds_Merchant_MerchantURL).

    CSRF-exempt because the request comes from Redsys's own servers, not a
    browser with our session/cookies — there's no CSRF token to check.
    Authenticity instead comes entirely from the signature check inside
    ``parse_notification``.
    """

    facade_class = RedsysFacade
    http_method_names = ["post"]

    def post(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        facade = self.facade_class()
        try:
            notification = facade.parse_notification(request.POST)
        except (KeyError, ValueError) as exc:
            logger.warning("Malformed Redsys notification: %s", exc)
            return HttpResponseBadRequest("malformed notification")

        if not notification.signature_valid:
            logger.warning(
                "Redsys notification signature mismatch for order %s",
                notification.order_number,
            )
            # Deliberately still 200 OK: Redsys retries on non-2xx, and a
            # forged/replayed request retrying forever gains nothing since
            # it will never pass the signature check.
            return HttpResponse("signature invalid")

        _, created = RedsysNotification.objects.get_or_create(
            order_number=notification.order_number,
            defaults={
                "ds_response": notification.ds_response,
                "signature_valid": notification.signature_valid,
                "raw_merchant_parameters": notification.raw_parameters,
            },
        )
        if created:
            self._dispatch_signal(notification)
        else:
            logger.info(
                "Duplicate Redsys notification for order %s, ignored",
                notification.order_number,
            )
        return HttpResponse("OK")

    def _dispatch_signal(self, notification: Notification) -> None:
        signal = signals.payment_confirmed if notification.authorized else signals.payment_declined
        signal.send(
            sender=self.__class__,
            order_number=notification.order_number,
            notification=notification,
        )


class ReturnView(TemplateView):
    """The page the customer's browser lands on after Ds_Merchant_UrlOK/KO.

    Looks up whatever :class:`NotificationView` has already recorded for
    this order, purely to decide what to display — never to confirm a
    payment (see module docstring).
    """

    template_name = "oscar_redsys/return.html"

    def get_order_number(self) -> str | None:
        return self.request.GET.get("order_number") or self.request.POST.get("order_number")

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        order_number = self.get_order_number()
        notification = None
        if order_number:
            notification = RedsysNotification.objects.filter(order_number=order_number).first()
        context["order_number"] = order_number
        context["notification"] = notification
        return context
