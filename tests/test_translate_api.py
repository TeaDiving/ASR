from fastapi.testclient import TestClient

from backend.main import app
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


def test_plugin_page_is_served() -> None:
    response = client.get("/plugin")

    assert response.status_code == 200
    assert "ASR Translation Plugin" in response.text
    assert "/api/translate" in response.text


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
