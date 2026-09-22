"""Encoding/decoding of the ``Ds_MerchantParameters`` field.

Two variants, matching :mod:`oscar_redsys.signature`'s V1/V2 split — the
redirection manual (section 3.1/6) is explicit that its channel uses
"Base 64 URL-safe" with no padding (its SIS0430 error forbids ``=``,
``+``, ``/`` appearing in the field, since it travels inside an HTML form
field); the REST manual (section on "Estructura de una petición REST")
instead just says "Base 64" for its JSON request body, where there's no
form/URL-encoding concern to avoid those characters for.
"""

from __future__ import annotations

import base64
import json
from typing import Any


def encode_merchant_parameters(data: dict[str, Any]) -> str:
    """V2 (redirection flow): Base64 URL-safe, padding stripped."""
    raw = json.dumps(data, separators=(",", ":")).encode("utf-8")
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def decode_merchant_parameters(encoded: str) -> dict[str, Any]:
    """Decodes either variant — both are valid base64 once padding is restored,
    and neither alphabet's extra characters (``-``/``_`` vs ``+``/``/``) can
    collide with the other, so one lenient decoder covers both."""
    padding = "=" * (-len(encoded) % 4)
    raw = base64.urlsafe_b64decode(encoded + padding)
    result: dict[str, Any] = json.loads(raw.decode("utf-8"))
    return result


def encode_merchant_parameters_v1(data: dict[str, Any]) -> str:
    """V1 (REST confirm/refund/cancel channel): plain Base64, padding kept."""
    raw = json.dumps(data, separators=(",", ":")).encode("utf-8")
    return base64.b64encode(raw).decode("ascii")
