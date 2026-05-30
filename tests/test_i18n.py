from recycle_cost.i18n import TEXT


def test_translation_keys_match_across_languages():
    expected = set(TEXT["en"])

    for lang, translations in TEXT.items():
        assert set(translations) == expected, lang
