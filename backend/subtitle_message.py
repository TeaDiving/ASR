import time
import uuid
from typing import Any


def create_subtitle_id() -> str:
    return f"subtitle_{uuid.uuid4().hex}"


def current_timestamp_ms() -> int:
    return int(time.time() * 1000)


def build_subtitle_message(
    source_text: str,
    normalized_text: str,
    translated_text: str,
    is_final: bool,
) -> dict[str, Any]:
    return {
        "id": create_subtitle_id(),
        "sourceText": source_text,
        "normalizedText": normalized_text,
        "translatedText": translated_text,
        "timestamp": current_timestamp_ms(),
        "isFinal": is_final,
    }
