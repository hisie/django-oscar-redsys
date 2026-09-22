"""``Ds_Merchant_ConsumerLanguage`` — the language Redsys's own hosted payment
page (and its "Recibo Redsys" confirmation screen) is shown in.

Purely cosmetic: it changes what language the *Redsys-hosted* pages
render in, nothing about the payment itself. Confirmed shape from
Redsys's own parameter reference: exactly 3 numeric digits, ``"000"``
meaning "undetermined" (Redsys defaults to Spanish). The code-to-language
mapping below is **not** confirmed against that first-party reference
directly — it only documents the field's shape, not this table — but is
corroborated by several independent, long-standing third-party Redsys
integrations that all agree on the same 13 values, so it's used here as
community-confirmed rather than invented.
"""

from __future__ import annotations


class ConsumerLanguage:
    UNDETERMINED = "000"
    SPANISH = "001"
    ENGLISH = "002"
    CATALAN = "003"
    FRENCH = "004"
    GERMAN = "005"
    DUTCH = "006"
    ITALIAN = "007"
    SWEDISH = "008"
    PORTUGUESE = "009"
    VALENCIAN = "010"
    POLISH = "011"
    GALICIAN = "012"
    BASQUE = "013"
