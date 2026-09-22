"""Optional EMV3DS/SCA fields: ``DS_MERCHANT_EMV3DS`` and ``DS_MERCHANT_EXCEP_SCA``.

PSD2 requires Strong Customer Authentication (SCA) on most card payments.
Redsys's EMV 3-D Secure v2 flow decides, per transaction, whether the
issuer can authenticate the cardholder "frictionlessly" (no extra step)
or must "challenge" them (OTP, biometrics, ...). Neither field is
required for a payment to work — Redsys/the issuer will decide SCA either
way — but supplying good data here is what lets more transactions go
frictionless instead of interrupting the customer.

Field shape for ``DS_MERCHANT_EMV3DS`` is confirmed against the
redirection manual's own worked example (v4.1, section 3.3.4) — not the
full EMV 3DS 2.x spec, which defines many more optional fields this
manual's example doesn't show; pass those through ``Emv3dsData.extra``
rather than guessing at their names here.

``DS_MERCHANT_EXCEP_SCA``'s three values below are confirmed against
Redsys's own PSD2/SCA documentation page (concrete fraud-rate thresholds
quoted there, not just a code list, is what makes this confirmed rather
than assumed). That page also describes further exemption categories
(corporate cards, MO/TO phone sales) without giving this parameter's
exact code for them — those aren't included here; pass whatever code
Redsys's docs give for them as a plain string, since this field isn't
restricted to :class:`ScaExemption`'s three constants.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class MobilePhone:
    country_code: str
    subscriber: str

    def to_dict(self) -> dict[str, str]:
        return {"cc": self.country_code, "subscriber": self.subscriber}


@dataclass(frozen=True)
class Emv3dsData:
    ship_addr_country: str | None = None  # numeric ISO 3166-1 country code, e.g. "840"
    ship_addr_city: str | None = None
    ship_addr_state: str | None = None
    ship_addr_line1: str | None = None
    ship_addr_line2: str | None = None
    ship_addr_line3: str | None = None
    cardholder_name: str | None = None
    email: str | None = None
    mobile_phone: MobilePhone | None = None
    extra: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        named_fields = {
            "shipAddrCountry": self.ship_addr_country,
            "shipAddrCity": self.ship_addr_city,
            "shipAddrState": self.ship_addr_state,
            "shipAddrLine1": self.ship_addr_line1,
            "shipAddrLine2": self.ship_addr_line2,
            "shipAddrLine3": self.ship_addr_line3,
            "cardholderName": self.cardholder_name,
            "email": self.email,
        }
        result: dict[str, Any] = {k: v for k, v in named_fields.items() if v is not None}
        if self.mobile_phone is not None:
            result["mobilePhone"] = self.mobile_phone.to_dict()
        result.update(self.extra)
        return result


class ScaExemption:
    LOW_VALUE = "LWV"
    """Transaction <= EUR 30. Capped: the issuer can still demand SCA once this
    exemption has been used 5 consecutive times, or EUR 100 has accumulated,
    since the customer's last full authentication."""

    TRANSACTION_RISK_ANALYSIS = "TRA"
    """Bank/PSP-assessed low fraud risk. Subject to the PSP's own real-time
    fraud-rate staying under a threshold that tightens as the amount rises
    (0.13% up to EUR 100, 0.06% up to EUR 250, 0.01% up to EUR 500)."""

    MERCHANT_INITIATED = "MIT"
    """The customer isn't present in this operation's flow at all (e.g. a
    stored-credential recurring charge) — SCA doesn't apply to begin with."""
