from fastapi.testclient import TestClient

from backend.main import app
from backend.xfyun_ai_correction import AICorrectionError
from backend.xfyun_translation import TranslationError, XFYUNCredentials


client = TestClient(app)


def test_translate_api_returns_translated_text(monkeypatch) -> None:
    async def fake_translate_text(
        text: str,
        credentials: XFYUNCredentials | None = None,
    ) -> str:
        return "大家早上好。"

    monkeypatch.setattr("backend.main.translate_text", fake_translate_text)

    response = client.post(
        "/api/translate",
        json={
            "text": "  Good   morning everyone.  ",
            "xfyunCredentials": {
                "appId": "user_app_id",
                "apiKey": "user_api_key",
                "apiSecret": "user_api_secret",
            },
        },
    )

    assert response.status_code == 200
    assert response.json() == {
        "ok": True,
        "normalizedText": "Good morning everyone.",
        "translatedText": "大家早上好。",
    }


def test_translate_api_uses_corrected_text_before_translation(monkeypatch) -> None:
    captured_text = None

    async def capture_text(
        text: str,
        credentials: XFYUNCredentials | None = None,
    ) -> str:
        nonlocal captured_text
        captured_text = text
        return f"Translated: {text}"

    monkeypatch.setattr("backend.main.translate_text", capture_text)

    response = client.post(
        "/api/translate",
        json={
            "text": "hellow wrold",
        },
    )

    assert response.status_code == 200
    assert response.json()["normalizedText"] == "hellow wrold"
    assert response.json()["translatedText"] == "Translated: Hello world"
    assert captured_text == "Hello world"


def test_translate_api_uses_ai_corrected_text_before_translation(monkeypatch) -> None:
    captured_text = None

    async def fake_ai_correct_text(text: str, previous_context=None) -> str:
        assert text == "Hello world"
        assert previous_context is None
        return "Hello, world."

    async def capture_text(
        text: str,
        credentials: XFYUNCredentials | None = None,
    ) -> str:
        nonlocal captured_text
        captured_text = text
        return f"Translated: {text}"

    monkeypatch.setattr("backend.main.ai_correct_text", fake_ai_correct_text)
    monkeypatch.setattr("backend.main.translate_text", capture_text)

    response = client.post(
        "/api/translate",
        json={
            "text": "hellow wrold",
        },
    )

    assert response.status_code == 200
    assert response.json()["normalizedText"] == "hellow wrold"
    assert response.json()["translatedText"] == "Translated: Hello, world."
    assert captured_text == "Hello, world."


def test_translate_api_falls_back_when_ai_correction_fails(monkeypatch) -> None:
    captured_text = None

    async def fail_ai_correction(text: str, previous_context=None) -> str:
        raise AICorrectionError("failed")

    async def capture_text(
        text: str,
        credentials: XFYUNCredentials | None = None,
    ) -> str:
        nonlocal captured_text
        captured_text = text
        return f"Translated: {text}"

    monkeypatch.setattr("backend.main.ai_correct_text", fail_ai_correction)
    monkeypatch.setattr("backend.main.translate_text", capture_text)

    response = client.post(
        "/api/translate",
        json={
            "text": "hellow wrold",
        },
    )

    assert response.status_code == 200
    assert response.json()["translatedText"] == "Translated: Hello world"
    assert captured_text == "Hello world"


def test_translate_api_passes_previous_correction_context_to_ai(monkeypatch) -> None:
    captured_previous_contexts = []

    async def fake_ai_correct_text(text: str, previous_context=None) -> str:
        captured_previous_contexts.append(previous_context)
        return text

    async def fake_translate_text(
        text: str,
        credentials: XFYUNCredentials | None = None,
    ) -> str:
        return f"Translated: {text}"

    monkeypatch.setattr("backend.main.ai_correct_text", fake_ai_correct_text)
    monkeypatch.setattr("backend.main.translate_text", fake_translate_text)

    first_response = client.post("/api/translate", json={"text": "hellow"})
    second_response = client.post("/api/translate", json={"text": "wrold"})

    assert first_response.status_code == 200
    assert second_response.status_code == 200
    assert captured_previous_contexts[0] is None
    assert captured_previous_contexts[1].original_text == "hellow"
    assert captured_previous_contexts[1].rule_corrected_text == "Hello"
    assert captured_previous_contexts[1].ai_corrected_text == "Hello"


def test_plugin_page_is_served() -> None:
    response = client.get("/plugin")

    assert response.status_code == 200
    assert "ASR Translation Plugin" in response.text
    assert "/api/translate" in response.text


def test_plugin_page_connects_to_subtitle_stream() -> None:
    response = client.get("/plugin")

    assert response.status_code == 200
    assert 'EventSource("/api/subtitle/stream")' in response.text
    assert 'id="stream-status"' in response.text
    assert "subtitleStream.onopen" in response.text
    assert "Subtitle stream connected" in response.text
    assert "Network disconnected, reconnecting..." in response.text
    assert 'console.log("Subtitle received:", subtitle)' in response.text
    assert "addSubtitleToHistory(subtitle)" in response.text
    assert 'console.error("Subtitle stream error", error)' in response.text


def test_plugin_page_shows_loading_and_failure_states() -> None:
    response = client.get("/plugin")

    assert response.status_code == 200
    assert "function showManualTranslationResult(sourceText, chineseText, isError = false)" in response.text
    assert "function showTranslationFailure(sourceText, error)" in response.text
    assert 'showManualTranslationResult(sourceText, "Translating...");' in response.text
    assert '"Translation failed. Showing original English."' in response.text
    assert "showTranslationFailure(sourceText, error);" in response.text
    assert "button.disabled = true;" in response.text
    assert "button.disabled = false;" in response.text


def test_plugin_page_contains_subtitle_history_ui() -> None:
    response = client.get("/plugin")

    assert response.status_code == 200
    assert 'id="subtitle-history"' in response.text
    assert 'id="subtitle-history-list"' in response.text
    assert "const subtitleHistory = [];" in response.text
    assert "const MAX_SUBTITLE_HISTORY = 5;" in response.text
    assert "function renderSubtitleHistory()" in response.text
    assert "function addSubtitleToHistory(subtitle)" in response.text


def test_plugin_page_keeps_recent_subtitle_history() -> None:
    response = client.get("/plugin")

    assert response.status_code == 200
    assert "subtitleHistory.push(subtitle);" in response.text
    assert "subtitleHistory.length > MAX_SUBTITLE_HISTORY" in response.text
    assert "subtitleHistory.splice(0, subtitleHistory.length - MAX_SUBTITLE_HISTORY);" in response.text
    assert 'document.createElement("article")' in response.text
    assert "subtitleHistoryList.append(item);" in response.text
    assert "subtitleHistoryList.scrollTop = subtitleHistoryList.scrollHeight;" in response.text
    assert "subtitleHistoryContainer.hidden = subtitleHistory.length === 0;" in response.text


def test_plugin_page_translation_failure_preserves_subtitle_history() -> None:
    response = client.get("/plugin")

    assert response.status_code == 200
    assert "subtitleHistory.length = 0" not in response.text
    assert "subtitleHistory.splice(0, subtitleHistory.length)" not in response.text
    assert "subtitleHistoryContainer.hidden = true" not in response.text


def test_translate_api_passes_user_credentials_to_translation(monkeypatch) -> None:
    captured_credentials = None

    async def capture_credentials(
        text: str,
        credentials: XFYUNCredentials | None = None,
    ) -> str:
        nonlocal captured_credentials
        captured_credentials = credentials
        return "大家早上好。"

    monkeypatch.setattr("backend.main.translate_text", capture_credentials)

    response = client.post(
        "/api/translate",
        json={
            "text": "Good morning everyone.",
            "xfyunCredentials": {
                "appId": "user_app_id",
                "apiKey": "user_api_key",
                "apiSecret": "user_api_secret",
            },
        },
    )

    assert response.status_code == 200
    assert captured_credentials == XFYUNCredentials(
        app_id="user_app_id",
        api_key="user_api_key",
        api_secret="user_api_secret",
    )


def test_translate_api_rejects_blank_text() -> None:
    response = client.post(
        "/api/translate",
        json={
            "text": "  \n\t  ",
        },
    )

    assert response.status_code == 400
    assert response.json() == {"detail": "Invalid text"}


def test_translate_api_returns_translation_failure(monkeypatch) -> None:
    async def raise_translation_error(
        text: str,
        credentials: XFYUNCredentials | None = None,
    ) -> str:
        raise TranslationError("unexpected")

    monkeypatch.setattr("backend.main.translate_text", raise_translation_error)

    response = client.post(
        "/api/translate",
        json={
            "text": "Good morning everyone.",
        },
    )

    assert response.status_code == 502
    assert response.json() == {"detail": "Translation failed"}
