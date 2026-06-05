from fastapi.testclient import TestClient

from backend.main import app


client = TestClient(app)


def test_health_check() -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"ok": True}


def test_websocket_accepts_valid_asr_message() -> None:
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
    }


def test_websocket_returns_normalized_text() -> None:
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
