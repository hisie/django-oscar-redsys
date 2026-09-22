from __future__ import annotations

from collections.abc import Iterator

import pytest

from oscar_redsys import signals


@pytest.fixture(autouse=True)
def _isolate_redsys_signals() -> Iterator[None]:
    """Each test starts with a clean slate of signal receivers.

    Without this, receivers connected inside one test (with ``weak=False``,
    since a bare lambda would otherwise be garbage-collected before the
    signal fires) would leak into every later test.
    """
    confirmed_receivers = list(signals.payment_confirmed.receivers)
    declined_receivers = list(signals.payment_declined.receivers)
    try:
        yield
    finally:
        signals.payment_confirmed.receivers = confirmed_receivers
        signals.payment_declined.receivers = declined_receivers
