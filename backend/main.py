import asyncio
import json
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, StreamingResponse

from backend.subtitle_message import build_subtitle_message
from backend.subtitle_stream import format_sse_event, subtitle_broadcaster
from backend.text_preprocessing import normalize_text
from backend.xfyun_translation import (
    TranslationConfigurationError,
    TranslationError,
    XFYUNCredentials,
    translate_text,
)


app = FastAPI()


PROJECT_ROOT = Path(__file__).resolve().parent.parent
REQUIRED_ASR_FIELDS = {"id", "text", "timestamp", "isFinal"}
USER_CREDENTIALS_FIELD = "xfyunCredentials"


def is_valid_asr_text_message(message: Any) -> bool:
    if not isinstance(message, dict):
        return False

    if not REQUIRED_ASR_FIELDS.issubset(message):
        return False

    if not isinstance(message["id"], str):
        return False

    if not isinstance(message["text"], str):
        return False

    if not normalize_text(message["text"]):
        return False

    if isinstance(message["timestamp"], bool) or not isinstance(
        message["timestamp"], (int, float)
    ):
        return False

    if not isinstance(message["isFinal"], bool):
        return False

    return True


def read_user_credentials(message: dict[str, Any]) -> XFYUNCredentials | None:
    raw_credentials = message.get(USER_CREDENTIALS_FIELD)

    if raw_credentials is None:
        return None

    if not isinstance(raw_credentials, dict):
        raise TranslationConfigurationError("Invalid user credentials")

    app_id = raw_credentials.get("appId")
    api_key = raw_credentials.get("apiKey")
    api_secret = raw_credentials.get("apiSecret")

    if not all(isinstance(value, str) and value for value in (app_id, api_key, api_secret)):
        raise TranslationConfigurationError("Invalid user credentials")

    return XFYUNCredentials(app_id=app_id, api_key=api_key, api_secret=api_secret)


@app.get("/health")
def health() -> dict[str, bool]:
    return {"ok": True}


@app.get("/plugin")
def plugin_page() -> FileResponse:
    return FileResponse(PROJECT_ROOT / "frontend" / "plugin.html")


@app.post("/api/translate")
async def translate_text_api(payload: dict[str, Any]) -> dict[str, Any]:
    text = payload.get("text")

    if not isinstance(text, str):
        raise HTTPException(status_code=400, detail="Invalid text")

    normalized_text = normalize_text(text)

    if not normalized_text:
        raise HTTPException(status_code=400, detail="Invalid text")

    try:
        credentials = read_user_credentials(payload)
        translated_text = await translate_text(normalized_text, credentials=credentials)
    except (TranslationConfigurationError, TranslationError) as exc:
        raise HTTPException(status_code=502, detail="Translation failed") from exc

    return {
        "ok": True,
        "normalizedText": normalized_text,
        "translatedText": translated_text,
    }


@app.post("/api/subtitle")
async def create_subtitle_api(payload: dict[str, Any]) -> dict[str, Any]:
    source_text = payload.get("text")

    if not isinstance(source_text, str):
        raise HTTPException(status_code=400, detail="Invalid text")

    normalized_text = normalize_text(source_text)

    if not normalized_text:
        raise HTTPException(status_code=400, detail="Invalid text")

    is_final = payload.get("isFinal", True)

    if not isinstance(is_final, bool):
        raise HTTPException(status_code=400, detail="Invalid isFinal")

    try:
        credentials = read_user_credentials(payload)
        translated_text = await translate_text(normalized_text, credentials=credentials)
    except (TranslationConfigurationError, TranslationError) as exc:
        raise HTTPException(status_code=502, detail="Translation failed") from exc

    subtitle_message = build_subtitle_message(
        source_text=source_text,
        normalized_text=normalized_text,
        translated_text=translated_text,
        is_final=is_final,
    )
    await subtitle_broadcaster.publish(subtitle_message)

    return subtitle_message


@app.get("/api/subtitle/stream")
async def subtitle_stream_api(request: Request) -> StreamingResponse:
    async def event_generator():
        queue = subtitle_broadcaster.subscribe()

        try:
            while True:
                if await request.is_disconnected():
                    break

                try:
                    subtitle_message = await asyncio.wait_for(queue.get(), timeout=15)
                except asyncio.TimeoutError:
                    yield ": keep-alive\n\n"
                    continue

                yield format_sse_event(subtitle_message)
        finally:
            subtitle_broadcaster.unsubscribe(queue)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )


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

        normalized_text = normalize_text(message["text"])

        print(f"Received ASR text: {normalized_text}")
        try:
            credentials = read_user_credentials(message)
            translated_text = await translate_text(normalized_text, credentials=credentials)
        except (TranslationConfigurationError, TranslationError):
            await websocket.send_json(
                {
                    "type": "error",
                    "ok": False,
                    "message": "Translation failed",
                }
            )
            continue

        await websocket.send_json(
            {
                "type": "asr_received",
                "id": message["id"],
                "ok": True,
                "normalizedText": normalized_text,
                "translatedText": translated_text,
            }
        )
