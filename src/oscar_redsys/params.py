"""Encoding/decoding of the ``Ds_MerchantParameters`` field.

Per section 3.1/6 of the redirection manual: a JSON object, UTF-8 encoded,
then Base64 URL-safe encoded with no padding (Redsys's error SIS0430
explicitly forbids ``=``, ``+``, ``/`` appearing in the field).
"""

from __future__ import annotations

import base64
import json
from typing import Any


def encode_merchant_parameters(data: dict[str, Any]) -> str:
    raw = json.dumps(data, separators=(",", ":")).encode("utf-8")
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def decode_merchant_parameters(encoded: str) -> dict[str, Any]:
    padding = "=" * (-len(encoded) % 4)
    raw = base64.urlsafe_b64decode(encoded + padding)
    result: dict[str, Any] = json.loads(raw.decode("utf-8"))
    return result
