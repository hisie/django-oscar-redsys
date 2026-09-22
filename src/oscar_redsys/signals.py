"""How this package tells the host project about a payment outcome.

Deliberately signals, not a subclassable-hook-on-the-view pattern: the
notification view has no idea what "confirming a payment" means in the
host project's own Order model (Oscar's own order chain, a Dolibarr sync
task, whatever) — that's entirely the receiver's business.

Both signals fire at most once per order number, from
:class:`oscar_redsys.views.NotificationView`, guarded by
``RedsysNotification``'s uniqueness on ``order_number`` — a resent Redsys
notification for an already-seen order never fires either signal again.
"""

from __future__ import annotations

import django.dispatch

payment_confirmed = django.dispatch.Signal()
"""Sent with kwargs order_number: str, notification: oscar_redsys.facade.Notification."""

payment_declined = django.dispatch.Signal()
"""Sent with kwargs order_number: str, notification: oscar_redsys.facade.Notification."""
