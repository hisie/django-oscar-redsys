"""HMAC-SHA512 signing, both versions Redsys documents across its manuals.

Algorithm per Redsys's "TPV-Virtual Manual de Integración - Redirección"
(v4.1, 24/09/2025, ref. RS.TE.CEL.MAN.0039) section 3.3, and "TPV-Virtual
Manual Integración-REST" (v4.0.1.1, 17/10/2025, ref. RS.TE.CEL.MAN.0037)
section 3 — the two manuals describe the same core algorithm, used by
two different channels:

1. The merchant secret key is a plain ASCII string, forced to exactly 16
   bytes (truncated if longer, right-padded with ``\\x00`` if shorter).
2. A per-operation signing key is derived by AES-128-CBC-encrypting the
   order number (PKCS#7-padded, UTF-8) with that 16-byte key and an
   all-zero IV, then **base64-encoding that ciphertext** — the order
   number is what "diversifies" the key so a leaked signature for one
   order can't be replayed against another. The base64 *string* (its
   ASCII bytes), not the raw ciphertext, is the actual HMAC key used in
   step 3 — easy to get wrong since a self-consistent sign/verify round
   trip using the raw bytes on both sides "works" too, just not against
   Redsys itself. Caught only by reproducing each manual's own worked
   example end-to-end (see the tests), not by round-trip testing alone.
3. The signature itself is HMAC-SHA512 of the already base64-encoded
   ``Ds_MerchantParameters`` string, keyed by that base64 signing-key
   string's ASCII bytes. The two channels differ only in this last
   encoding step:

   - **V2** (``HMAC_SHA512_V2``, the redirection/browser flow —
     :mod:`oscar_redsys.facade`): ``Ds_MerchantParameters`` is base64
     *URL-safe*; ``Ds_Signature`` is base64 URL-safe with padding
     *stripped* (the redirection manual's own SIS0430 error forbids
     ``=``/``+``/``/`` in these form fields).
   - **V1** (``HMAC_SHA512_V1``, the server-to-server REST channel —
     :mod:`oscar_redsys.rest`, used for confirm/refund/cancel): both
     fields use plain (non-URL-safe) base64, and ``Ds_Signature`` *keeps*
     its ``=`` padding — stated explicitly in the REST manual ("se
     codifica en BASE 64 URL Encoded, manteniendo el padding de =") and
     confirmed byte-exact against that manual's own worked example, which
     reuses the very same key+order as the V2 example above.

Both worked examples are verified byte-exact in ``tests/test_signature.py``.
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


def _hmac_sha512(secret_key: str, order: str, merchant_parameters: str) -> bytes:
    operation_key = derive_operation_key(secret_key, order)
    # The HMAC key is the *base64 string* of the derived key, not its raw
    # bytes — see the module docstring.
    hmac_key = base64.b64encode(operation_key)
    return hmac.new(hmac_key, merchant_parameters.encode("ascii"), hashlib.sha512).digest()


def sign_merchant_parameters(secret_key: str, order: str, merchant_parameters: str) -> str:
    """Compute the V2 ``Ds_Signature`` for an already base64url-encoded
    ``Ds_MerchantParameters`` (the redirection flow — no padding, URL-safe).

    ``merchant_parameters`` is the exact string that will be (or was)
    sent/received as ``Ds_MerchantParameters`` — signing happens over that
    string's ASCII bytes, not over the decoded JSON.
    """
    digest = _hmac_sha512(secret_key, order, merchant_parameters)
    return base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")


def signatures_match(secret_key: str, order: str, merchant_parameters: str, signature: str) -> bool:
    """Constant-time comparison of a received V2 signature against the recomputed one."""
    expected = sign_merchant_parameters(secret_key, order, merchant_parameters)
    return hmac.compare_digest(expected, signature)


def sign_merchant_parameters_v1(secret_key: str, order: str, merchant_parameters: str) -> str:
    """Compute the V1 ``Ds_Signature`` for an already base64-encoded
    ``Ds_MerchantParameters`` (the REST/confirm-refund-cancel channel —
    padding kept, URL-safe alphabet per the REST manual's own worked
    example)."""
    digest = _hmac_sha512(secret_key, order, merchant_parameters)
    return base64.urlsafe_b64encode(digest).decode("ascii")


def signatures_match_v1(
    secret_key: str, order: str, merchant_parameters: str, signature: str
) -> bool:
    """Constant-time comparison of a received V1 signature against the recomputed one."""
    expected = sign_merchant_parameters_v1(secret_key, order, merchant_parameters)
    return hmac.compare_digest(expected, signature)
