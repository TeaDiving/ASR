import re


CORRECTION_RULES = {
    "hellow": "hello",
    "wrold": "world",
    "artifcial": "artificial",
    "intelijence": "intelligence",
    "recog nize": "recognize",
    "open ai": "OpenAI",
    "ice cream": "I scream",
}

INVALID_SINGLE_CHARACTER_TOKENS = {"x", "y", "q", "w", ".", ","}

_SPACE_PATTERN = re.compile(r"\s+")
_DUPLICATE_WORD_PATTERN = re.compile(
    r"\b([A-Za-z]+)\b(?:\s+\1\b)+",
    re.IGNORECASE,
)


def _collapse_spaces(text: str) -> str:
    return _SPACE_PATTERN.sub(" ", text).strip()


def _apply_correction_rules(text: str) -> str:
    corrected_text = text

    for wrong_text, correct_text in sorted(
        CORRECTION_RULES.items(),
        key=lambda item: len(item[0]),
        reverse=True,
    ):
        pattern = re.compile(
            rf"(?<!\w){re.escape(wrong_text)}(?!\w)",
            re.IGNORECASE,
        )
        corrected_text = pattern.sub(correct_text, corrected_text)

    return corrected_text


def _remove_invalid_single_character_tokens(text: str) -> str:
    invalid_pattern = "|".join(
        re.escape(token)
        for token in sorted(INVALID_SINGLE_CHARACTER_TOKENS, key=len, reverse=True)
    )
    return re.sub(
        rf"(?<!\w)(?:{invalid_pattern})(?!\w)",
        " ",
        text,
        flags=re.IGNORECASE,
    )


def _remove_repeated_words(text: str) -> str:
    previous_text = None
    corrected_text = text

    while previous_text != corrected_text:
        previous_text = corrected_text
        corrected_text = _DUPLICATE_WORD_PATTERN.sub(r"\1", corrected_text)

    return corrected_text


def _capitalize_sentence_when_lowercase(text: str) -> str:
    if text and text == text.lower():
        return text[0].upper() + text[1:]

    return text


def auto_correct_text(text: str) -> str:
    original_text = text
    corrected_text = _collapse_spaces(text)
    corrected_text = _apply_correction_rules(corrected_text)
    corrected_text = _remove_invalid_single_character_tokens(corrected_text)
    corrected_text = _remove_repeated_words(corrected_text)
    corrected_text = _collapse_spaces(corrected_text)
    corrected_text = _capitalize_sentence_when_lowercase(corrected_text)

    if corrected_text != original_text:
        print(f"Auto-corrected text: {original_text} -> {corrected_text}")

    return corrected_text
