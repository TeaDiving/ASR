import base64
import hashlib
import hmac
import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from email.utils import format_datetime
from typing import Any

import httpx
from dotenv import load_dotenv


load_dotenv()

TRANSLATION_URL = "https://itrans.xfyun.cn/v2/its"
TRANSLATION_HOST = "itrans.xfyun.cn"
TRANSLATION_PATH = "/v2/its"
SOURCE_LANGUAGE = "en"
TARGET_LANGUAGE = "cn"


class TranslationConfigurationError(Exception):
    pass


class TranslationError(Exception):
    pass


@dataclass(frozen=True)
class XFYUNCredentials:
    app_id: str
    api_key: str
    api_secret: str


def read_xfyun_credentials() -> XFYUNCredentials:
    app_id = os.getenv("XFYUN_APP_ID")
    api_key = os.getenv("XFYUN_API_KEY")
    api_secret = os.getenv("XFYUN_API_SECRET")

    if not app_id or not api_key or not api_secret:
        raise TranslationConfigurationError("Missing XFYUN translation credentials")

    return XFYUNCredentials(app_id=app_id, api_key=api_key, api_secret=api_secret)


def encode_text(text: str) -> str:
    return base64.b64encode(text.encode("utf-8")).decode("utf-8")


def build_translation_payload(text: str, app_id: str) -> dict[str, Any]:
    return {
        "common": {
            "app_id": app_id,
        },
        "business": {
            "from": SOURCE_LANGUAGE,
            "to": TARGET_LANGUAGE,
        },
        "data": {
            "text": encode_text(text),
        },
    }


def dump_payload(payload: dict[str, Any]) -> bytes:
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")


def create_digest(body: bytes) -> str:
    digest = hashlib.sha256(body).digest()
    return "SHA-256=" + base64.b64encode(digest).decode("utf-8")


def create_authorization(api_key: str, api_secret: str, date: str, digest: str) -> str:
    signature_origin = (
        f"host: {TRANSLATION_HOST}\n"
        f"date: {date}\n"
        f"POST {TRANSLATION_PATH} HTTP/1.1\n"
        f"digest: {digest}"
    )
    signature = hmac.new(
        api_secret.encode("utf-8"),
        signature_origin.encode("utf-8"),
        digestmod=hashlib.sha256,
    ).digest()
    signature_base64 = base64.b64encode(signature).decode("utf-8")
    return (
        f'api_key="{api_key}", algorithm="hmac-sha256", '
        f'headers="host date request-line digest", signature="{signature_base64}"'
    )


def build_headers(body: bytes, credentials: XFYUNCredentials) -> dict[str, str]:
    date = format_datetime(datetime.now(timezone.utc), usegmt=True)
    digest = create_digest(body)
    return {
        "Content-Type": "application/json",
        "Accept": "application/json,version=1.0",
        "Host": TRANSLATION_HOST,
        "Date": date,
        "Digest": digest,
        "Authorization": create_authorization(
            credentials.api_key,
            credentials.api_secret,
            date,
            digest,
        ),
    }


def parse_translation_response(response_data: dict[str, Any]) -> str:
    if response_data.get("code") != 0:
        raise TranslationError("XFYUN translation returned an error")

    try:
        translated_text = response_data["data"]["result"]["trans_result"]["dst"]
    except (KeyError, TypeError) as exc:
        raise TranslationError("XFYUN translation response is missing translated text") from exc

    if not isinstance(translated_text, str) or not translated_text:
        raise TranslationError("XFYUN translation response is missing translated text")

    return translated_text


async def translate_text(
    text: str,
    credentials: XFYUNCredentials | None = None,
    client: httpx.AsyncClient | None = None,
) -> str:
    if credentials is None:
        credentials = read_xfyun_credentials()

    payload = build_translation_payload(text, credentials.app_id)
    body = dump_payload(payload)
    headers = build_headers(body, credentials)

    if client is not None:
        try:
            response = await client.post(TRANSLATION_URL, content=body, headers=headers)
            response.raise_for_status()
            response_data = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise TranslationError("XFYUN translation request failed") from exc

        return parse_translation_response(response_data)

    async with httpx.AsyncClient(timeout=15.0) as async_client:
        try:
            response = await async_client.post(TRANSLATION_URL, content=body, headers=headers)
            response.raise_for_status()
            response_data = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise TranslationError("XFYUN translation request failed") from exc

        return parse_translation_response(response_data)
