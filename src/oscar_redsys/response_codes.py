"""Interpretation of ``Ds_Response``, per section 4.1 of the redirection manual.

Redsys overloads this single field for several transaction types:

- ``0000``-``0099``: authorized payment/pre-authorization.
- ``0400``: authorized cancellation (anulación).
- ``0900``: authorized refund/confirmation (devolución/confirmación).
- anything else: the operation did not complete successfully — the exact
  value is a decline/error code (see Redsys's own "Códigos de respuesta"
  reference for the full list; not reproduced here since this package
  only needs authorized-or-not to drive the Oscar payment flow).
"""

from __future__ import annotations


def is_authorized(ds_response: str) -> bool:
    if not ds_response.isdigit():
        return False
    code = int(ds_response)
    return 0 <= code <= 99 or code in (400, 900)
