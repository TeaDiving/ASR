import json
from typing import Any

from fastapi import FastAPI, WebSocket, WebSocketDisconnect


app = FastAPI()


REQUIRED_ASR_FIELDS = {"id", "text", "timestamp", "isFinal"}


def is_valid_asr_text_message(message: Any) -> bool:
    if not isinstance(message, dict):
        return False

    if not REQUIRED_ASR_FIELDS.issubset(message):
        return False

    if not isinstance(message["id"], str):
        return False

    if not isinstance(message["text"], str):
        return False

    if isinstance(message["timestamp"], bool) or not isinstance(
        message["timestamp"], (int, float)
    ):
        return False

    if not isinstance(message["isFinal"], bool):
        return False

    return True


@app.get("/health")
def health() -> dict[str, bool]:
    return {"ok": True}


@app.websocket("/ws/asr")
async def receive_asr_text(websocket: WebSocket) -> None:
    await websocket.accept()

    while True:
        try:
            raw_message = await websocket.receive_text()
        except WebSocketDisconnect:
            break

        try:
            message = json.loads(raw_message)
        except json.JSONDecodeError:
            await websocket.send_json(
                {
                    "type": "error",
                    "ok": False,
                    "message": "Invalid ASRTextMessage",
                }
            )
            continue

        if not is_valid_asr_text_message(message):
            await websocket.send_json(
                {
                    "type": "error",
                    "ok": False,
                    "message": "Invalid ASRTextMessage",
                }
            )
            continue

        print(f"Received ASR text: {message['text']}")
        await websocket.send_json(
            {
                "type": "asr_received",
                "id": message["id"],
                "ok": True,
            }
        )
