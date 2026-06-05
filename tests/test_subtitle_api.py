from fastapi.testclient import TestClient

from backend.main import app
from backend.xfyun_translation import TranslationError, XFYUNCredentials


client = TestClient(app)


async def fake_translate_text(
    text: str,
    credentials: XFYUNCredentials | None = None,
) -> str:
    return f"Translated: {text}"


def test_subtitle_api_returns_complete_subtitle_message(monkeypatch) -> None:
    monkeypatch.setattr("backend.main.translate_text", fake_translate_text)

    response = client.post(
        "/api/subtitle",
        json={
            "text": "  Good   morning everyone.  ",
            "isFinal": True,
            "xfyunCredentials": {
                "appId": "user_app_id",
                "apiKey": "user_api_key",
                "apiSecret": "user_api_secret",
            },
        },
    )
    body = response.json()

    assert response.status_code == 200
    assert body["id"].startswith("subtitle_")
    assert body["sourceText"] == "  Good   morning everyone.  "
    assert body["normalizedText"] == "Good morning everyone."
    assert body["translatedText"] == "Translated: Good morning everyone."
    assert isinstance(body["timestamp"], int)
    assert body["isFinal"] is True


def test_subtitle_api_uses_corrected_text_before_translation(monkeypatch) -> None:
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
        "/api/subtitle",
        json={
            "text": "open ai",
        },
    )
    body = response.json()

    assert response.status_code == 200
    assert body["sourceText"] == "open ai"
    assert body["normalizedText"] == "open ai"
    assert body["translatedText"] == "Translated: OpenAI"
    assert captured_text == "OpenAI"


def test_subtitle_api_uses_ai_corrected_text_before_translation(monkeypatch) -> None:
    captured_text = None

    async def fake_ai_correct_text(text: str, previous_context=None) -> str:
        assert text == "OpenAI"
        return "OpenAI."

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
        "/api/subtitle",
        json={
            "text": "open ai",
        },
    )
    body = response.json()

    assert response.status_code == 200
    assert body["sourceText"] == "open ai"
    assert body["normalizedText"] == "open ai"
    assert body["translatedText"] == "Translated: OpenAI."
    assert captured_text == "OpenAI."


def test_subtitle_api_publishes_subtitle_message(monkeypatch) -> None:
    published_messages = []

    async def capture_publish(message: dict) -> None:
        published_messages.append(message)

    monkeypatch.setattr("backend.main.translate_text", fake_translate_text)
    monkeypatch.setattr("backend.main.subtitle_broadcaster.publish", capture_publish)

    response = client.post(
        "/api/subtitle",
        json={
            "text": "Good morning everyone.",
        },
    )
    body = response.json()

    assert response.status_code == 200
    assert published_messages == [body]


def test_subtitle_api_defaults_is_final_to_true(monkeypatch) -> None:
    monkeypatch.setattr("backend.main.translate_text", fake_translate_text)

    response = client.post(
        "/api/subtitle",
        json={
            "text": "Good morning everyone.",
        },
    )

    assert response.status_code == 200
    assert response.json()["isFinal"] is True


def test_subtitle_api_preserves_false_is_final(monkeypatch) -> None:
    monkeypatch.setattr("backend.main.translate_text", fake_translate_text)

    response = client.post(
        "/api/subtitle",
        json={
            "text": "Good morning everyone.",
            "isFinal": False,
        },
    )

    assert response.status_code == 200
    assert response.json()["isFinal"] is False


def test_subtitle_api_passes_user_credentials_to_translation(monkeypatch) -> None:
    captured_credentials = None

    async def capture_credentials(
        text: str,
        credentials: XFYUNCredentials | None = None,
    ) -> str:
        nonlocal captured_credentials
        captured_credentials = credentials
        return "Translated text"

    monkeypatch.setattr("backend.main.translate_text", capture_credentials)

    response = client.post(
        "/api/subtitle",
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


def test_subtitle_api_rejects_blank_text() -> None:
    response = client.post(
        "/api/subtitle",
        json={
            "text": "  \n\t  ",
        },
    )

    assert response.status_code == 400
    assert response.json() == {"detail": "Invalid text"}


def test_subtitle_api_returns_translation_failure(monkeypatch) -> None:
    published_messages = []

    async def raise_translation_error(
        text: str,
        credentials: XFYUNCredentials | None = None,
    ) -> str:
        raise TranslationError("unexpected")

    async def capture_publish(message: dict) -> None:
        published_messages.append(message)

    monkeypatch.setattr("backend.main.translate_text", raise_translation_error)
    monkeypatch.setattr("backend.main.subtitle_broadcaster.publish", capture_publish)

    response = client.post(
        "/api/subtitle",
        json={
            "text": "Good morning everyone.",
        },
    )

    assert response.status_code == 502
    assert response.json() == {"detail": "Translation failed"}
    assert published_messages == []
