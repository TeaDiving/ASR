from fastapi.testclient import TestClient

from backend.main import app
from backend.xfyun_translation import TranslationError


client = TestClient(app)


async def fake_translate_text(text: str) -> str:
    return f"中文: {text}"


def test_health_check() -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"ok": True}


def test_websocket_accepts_valid_asr_message(monkeypatch) -> None:
    monkeypatch.setattr("backend.main.translate_text", fake_translate_text)

    payload = {
        "id": "asr_001",
        "text": "Good morning everyone.",
        "timestamp": 1710000000000,
        "isFinal": True,
    }

    with client.websocket_connect("/ws/asr") as websocket:
        websocket.send_json(payload)
        response = websocket.receive_json()

    assert response == {
        "type": "asr_received",
        "id": "asr_001",
        "ok": True,
        "normalizedText": "Good morning everyone.",
        "translatedText": "中文: Good morning everyone.",
    }


def test_websocket_returns_normalized_text(monkeypatch) -> None:
    monkeypatch.setattr("backend.main.translate_text", fake_translate_text)

    payload = {
        "id": "asr_002",
        "text": "  Good   morning\n everyone.  ",
        "timestamp": 1710000000000,
        "isFinal": True,
    }

    with client.websocket_connect("/ws/asr") as websocket:
        websocket.send_json(payload)
        response = websocket.receive_json()

    assert response == {
        "type": "asr_received",
        "id": "asr_002",
        "ok": True,
        "normalizedText": "Good morning everyone.",
        "translatedText": "中文: Good morning everyone.",
    }


def test_websocket_returns_translation_failure(monkeypatch) -> None:
    async def raise_translation_error(text: str) -> str:
        raise TranslationError("unexpected")

    monkeypatch.setattr("backend.main.translate_text", raise_translation_error)

    payload = {
        "id": "asr_004",
        "text": "Good morning everyone.",
        "timestamp": 1710000000000,
        "isFinal": True,
    }

    with client.websocket_connect("/ws/asr") as websocket:
        websocket.send_json(payload)
        response = websocket.receive_json()

    assert response == {
        "type": "error",
        "ok": False,
        "message": "Translation failed",
    }


def test_websocket_rejects_missing_required_field() -> None:
    payload = {
        "id": "asr_001",
        "text": "Good morning everyone.",
        "timestamp": 1710000000000,
    }

    with client.websocket_connect("/ws/asr") as websocket:
        websocket.send_json(payload)
        response = websocket.receive_json()

    assert response == {
        "type": "error",
        "ok": False,
        "message": "Invalid ASRTextMessage",
    }


def test_websocket_rejects_empty_normalized_text() -> None:
    payload = {
        "id": "asr_003",
        "text": "   \n\t   ",
        "timestamp": 1710000000000,
        "isFinal": True,
    }

    with client.websocket_connect("/ws/asr") as websocket:
        websocket.send_json(payload)
        response = websocket.receive_json()

    assert response == {
        "type": "error",
        "ok": False,
        "message": "Invalid ASRTextMessage",
    }


def test_websocket_rejects_invalid_json() -> None:
    with client.websocket_connect("/ws/asr") as websocket:
        websocket.send_text("{invalid json")
        response = websocket.receive_json()

    assert response == {
        "type": "error",
        "ok": False,
        "message": "Invalid ASRTextMessage",
    }
