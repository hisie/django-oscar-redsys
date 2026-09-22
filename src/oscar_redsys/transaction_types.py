"""``Ds_Merchant_TransactionType`` values this package actually uses.

Confirmed against Redsys's "TPV-Virtual Manual Integración-REST" (v4.0.1.1,
17/10/2025, ref. RS.TE.CEL.MAN.0037), "Ejemplos de tipos de operación más
habituales": PAYMENT is what the redirection flow (:mod:`oscar_redsys.facade`)
builds; CONFIRMATION/REFUND/CANCELLATION are only ever sent through the
separate server-to-server REST channel (:mod:`oscar_redsys.rest`), since
Redsys has no redirect-based flow for them — there's no card entry, no
customer involved, just a merchant referencing an already-authorized
order. Not exhaustive (Redsys documents more, e.g. PREAUTHORIZATION="1");
add more only once this package actually needs to build them.
"""

from __future__ import annotations

PAYMENT = "0"
CONFIRMATION = "2"
REFUND = "3"
CANCELLATION = "9"
