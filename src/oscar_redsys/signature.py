"""HMAC_SHA512_V2 signing for Redsys's redirection integration.

Algorithm per Redsys's "TPV-Virtual Manual de Integración - Redirección"
(v4.1, 24/09/2025, ref. RS.TE.CEL.MAN.0039), section 3.3:

1. The merchant secret key is a plain ASCII string, forced to exactly 16
   bytes (truncated if longer, right-padded with ``\\x00`` if shorter).
2. A per-operation signing key is derived by AES-128-CBC-encrypting the
   order number (PKCS#7-padded, UTF-8) with that 16-byte key and an
   all-zero IV. The order number is what "diversifies" the key so a
   leaked signature for one order can't be replayed against another.
3. The signature itself is HMAC-SHA512 of the (already base64url-encoded)
   ``Ds_MerchantParameters`` string, keyed with the raw bytes from step 2,
   then base64url-encoded with padding stripped (Redsys's own encoding
   rules for this field forbid ``=``, ``+``, ``/``).

The AES key-derivation step is verified against Redsys's own published
worked example in the tests (key ``sq7HjrUOBfKmC576``, order
``1234567890`` -> ``RWt3/IPTzYRMXsQtkiGRKg==``).
"""

from __future__ import annotations

import base64
import hashlib
import hmac

from Crypto.Cipher import AES
from Crypto.Util.Padding import pad

_KEY_LENGTH = 16
_BLOCK_SIZE = 16
_ZERO_IV = b"\x00" * _BLOCK_SIZE


def _normalize_secret_key(secret_key: str) -> bytes:
    """Force the merchant's secret key to exactly 16 bytes, per section 6.1.2."""
    raw = secret_key.encode("utf-8")
    if len(raw) >= _KEY_LENGTH:
        return raw[:_KEY_LENGTH]
    return raw + b"\x00" * (_KEY_LENGTH - len(raw))


def derive_operation_key(secret_key: str, order: str) -> bytes:
    """Derive the per-operation signing key from the merchant key and order id."""
    normalized_key = _normalize_secret_key(secret_key)
    cipher = AES.new(normalized_key, AES.MODE_CBC, _ZERO_IV)
    padded_order = pad(order.encode("utf-8"), _BLOCK_SIZE)
    return bytes(cipher.encrypt(padded_order))


def sign_merchant_parameters(secret_key: str, order: str, merchant_parameters: str) -> str:
    """Compute ``Ds_Signature`` for an already base64url-encoded ``Ds_MerchantParameters``.

    ``merchant_parameters`` is the exact string that will be (or was)
    sent/received as ``Ds_MerchantParameters`` — signing happens over that
    string's ASCII bytes, not over the decoded JSON.
    """
    operation_key = derive_operation_key(secret_key, order)
    digest = hmac.new(operation_key, merchant_parameters.encode("ascii"), hashlib.sha512).digest()
    return base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")


def signatures_match(secret_key: str, order: str, merchant_parameters: str, signature: str) -> bool:
    """Constant-time comparison of a received signature against the recomputed one."""
    expected = sign_merchant_parameters(secret_key, order, merchant_parameters)
    return hmac.compare_digest(expected, signature)
