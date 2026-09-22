"""How this package tells the host project about a payment outcome.

Deliberately signals, not a subclassable-hook-on-the-view pattern: the
notification view has no idea what "confirming a payment" means in the
host project's own Order model (Oscar's own order chain, a Dolibarr sync
task, whatever) — that's entirely the receiver's business.

Both signals fire at most once per order number, from
:class:`oscar_redsys.views.NotificationView`, guarded by
``RedsysNotification``'s uniqueness on ``order_number`` — a resent Redsys
notification for an already-seen order never fires either signal again.

**Fires from an async server-to-server request — no browser, no
session.** A receiver that places an order by reading session-backed
checkout state (e.g. django-oscar's own ``checkout_session``) will find
nothing there, and a customer who pays then closes their browser before
any session-dependent fallback runs would have a confirmed payment with
no resulting order. See the README's "Common pitfall" section for the
fix (snapshot what order placement needs to a durable model *before*
redirecting to Redsys, read from that here instead of the session).
"""

from __future__ import annotations

import django.dispatch

payment_confirmed = django.dispatch.Signal()
"""Sent with kwargs order_number: str, notification: oscar_redsys.facade.Notification."""

payment_declined = django.dispatch.Signal()
"""Sent with kwargs order_number: str, notification: oscar_redsys.facade.Notification."""
