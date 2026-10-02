# Changelog

All notable changes to this project are documented in this file.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

## [0.2.1] - 2026-10-02

Docs-only — no code change.

### Added

- Documented the Oscar checkout `payment-details` step-skip pattern in
  the README ("Integrating with Oscar's checkout flow").
- `CHANGELOG.md` itself didn't exist until after 0.2.0 was published;
  bumping so PyPI's project page reflects it (PyPI freezes the README/
  description at publish time, so it would otherwise stay stale
  relative to what's in git).

## [0.2.0] - 2026-09-22

### Added

- `Notification`/`RestOperationResult` now expose `transaction_type`
  (`Ds_TransactionType`), so a receiver can tell a payment notification
  apart from a refund/cancellation/confirmation one arriving at the same
  webhook endpoint.
- `signatures_match`/`signatures_match_v1` gained an opt-in `lenient`
  flag (`REDSYS_LENIENT_SIGNATURE_COMPARISON`), off by default — exists
  for hosts that have actually observed receiving-side signature
  corruption, not as a default weakening of verification.
- Documented the `payment_confirmed` no-session pitfall (README and
  `signals.py` docstring): a naive receiver reading session-backed
  checkout state loses orders when the customer closes their browser
  before Redsys's async notification arrives.

Both additions found while reviewing a second, independent Redsys/Django
integration for anything this package had missed. 122 tests (up from
114), 99% coverage, `mypy --strict` clean. Backward-compatible — both new
fields/settings have safe defaults.

## [0.1.0] - 2026-09-22

### Added

- Initial Redsys (TPV Virtual) redirection-method integration for
  django-oscar: `RedsysFacade` (build/verify signed redirect payloads),
  `NotificationView`/`ReturnView`, `payment_confirmed`/`payment_declined`
  signals.
- `HMAC_SHA512_V2` signing (redirect flow) and `HMAC_SHA512_V1` (REST
  confirm/refund/cancel), verified byte-exact against Redsys's own
  published worked examples, not just self-consistent round-trip tests.
- EMV3DS/SCA support (`DS_MERCHANT_EMV3DS`, `DS_MERCHANT_EXCEP_SCA`).
- Order-number validation, refunds/cancellations (admin-gated REST
  channel, audited via `RedsysOperation`), `DS_MERCHANT_CONSUMERLANGUAGE`
  support.

[Unreleased]: https://github.com/hisie/django-oscar-redsys/compare/0.2.1...HEAD
[0.2.1]: https://github.com/hisie/django-oscar-redsys/compare/0.2.0...0.2.1
[0.2.0]: https://github.com/hisie/django-oscar-redsys/compare/0.1.0...0.2.0
[0.1.0]: https://github.com/hisie/django-oscar-redsys/releases/tag/0.1.0
