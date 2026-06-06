from backend.text_preprocessing import normalize_text


def test_normalize_text_keeps_plain_text_unchanged() -> None:
    assert normalize_text("Good morning.") == "Good morning."


def test_normalize_text_trims_leading_and_trailing_spaces() -> None:
    assert normalize_text("  Good morning.  ") == "Good morning."


def test_normalize_text_collapses_multiple_spaces() -> None:
    assert normalize_text("Good   morning.") == "Good morning."


def test_normalize_text_converts_newlines_and_tabs_to_spaces() -> None:
    assert normalize_text("Good\nmorning\t everyone.") == "Good morning everyone."


def test_normalize_text_returns_empty_string_for_blank_input() -> None:
    assert normalize_text("   ") == ""
