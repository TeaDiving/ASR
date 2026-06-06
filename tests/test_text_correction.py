from backend.text_correction import auto_correct_text


def test_auto_correct_text_keeps_plain_text_unchanged() -> None:
    assert auto_correct_text("I am a student") == "I am a student"


def test_auto_correct_text_replaces_common_wrong_words() -> None:
    assert auto_correct_text("hellow wrold") == "Hello world"
    assert auto_correct_text("artifcial intelijence") == "Artificial intelligence"


def test_auto_correct_text_replaces_common_wrong_phrases() -> None:
    assert auto_correct_text("recog nize") == "Recognize"
    assert auto_correct_text("open ai") == "OpenAI"
    assert auto_correct_text("ice cream") == "I scream"


def test_auto_correct_text_is_case_insensitive() -> None:
    assert auto_correct_text("Open Ai") == "OpenAI"


def test_auto_correct_text_removes_invalid_single_character_tokens() -> None:
    assert auto_correct_text("hello x y world") == "Hello world"
    assert auto_correct_text("hello . , world") == "Hello world"


def test_auto_correct_text_does_not_remove_meaningful_single_letter_words() -> None:
    assert auto_correct_text("I am a student") == "I am a student"


def test_auto_correct_text_removes_repeated_words() -> None:
    assert auto_correct_text("hello hello") == "Hello"
    assert auto_correct_text("world world world") == "World"
    assert auto_correct_text("hello hello world world") == "Hello world"


def test_auto_correct_text_cleans_extra_spaces() -> None:
    assert auto_correct_text("  hello   world  ") == "Hello world"


def test_auto_correct_text_logs_when_correction_happens(capsys) -> None:
    assert auto_correct_text("hellow") == "Hello"

    captured = capsys.readouterr()
    assert "Auto-corrected text: hellow -> Hello" in captured.out
