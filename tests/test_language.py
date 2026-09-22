from __future__ import annotations

from oscar_redsys.language import ConsumerLanguage


def test_consumer_language_constants_are_three_digit_strings() -> None:
    values = [
        ConsumerLanguage.UNDETERMINED,
        ConsumerLanguage.SPANISH,
        ConsumerLanguage.ENGLISH,
        ConsumerLanguage.CATALAN,
        ConsumerLanguage.FRENCH,
        ConsumerLanguage.GERMAN,
        ConsumerLanguage.DUTCH,
        ConsumerLanguage.ITALIAN,
        ConsumerLanguage.SWEDISH,
        ConsumerLanguage.PORTUGUESE,
        ConsumerLanguage.VALENCIAN,
        ConsumerLanguage.POLISH,
        ConsumerLanguage.GALICIAN,
        ConsumerLanguage.BASQUE,
    ]
    assert len(values) == len(set(values))  # all distinct
    for value in values:
        assert len(value) == 3
        assert value.isdigit()
