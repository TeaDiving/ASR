import asyncio
import base64
import hashlib
import hmac
import json
import os
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from email.utils import format_datetime
from typing import Any
from urllib.parse import urlencode, urlparse, urlunparse

from dotenv import load_dotenv

from backend.text_correction import auto_correct_text


load_dotenv()

DEFAULT_SPARK_API_URL = "wss://spark-api.xf-yun.com/v4.0/chat"
DEFAULT_SPARK_DOMAIN = "4.0Ultra"
AI_CORRECTION_SYSTEM_PROMPT = (
    "你是一个英文语音识别纠错专家。\n"
    "请只修正拼写错误、断句错误、重复词、乱码。\n"
    "不要改变句子原意，不要加词减词，不要润色，输出纯英文句子。\n"
    "如果没有错误，原样返回。"
)
MAX_SPARK_FRAMES = 20
SPARK_RECV_TIMEOUT_SECONDS = 15

_CJK_PATTERN = re.compile(r"[\u3400-\u9fff]")
_EXPLANATION_PATTERN = re.compile(
    r"(^\s*(corrected|correction|here is|the corrected)\b|```)",
    re.IGNORECASE,
)


class AICorrectionConfigurationError(Exception):
    pass


class AICorrectionError(Exception):
    pass


@dataclass(frozen=True)
class XFYUNSparkCredentials:
    app_id: str
    api_key: str
    api_secret: str


@dataclass(frozen=True)
class CorrectionContext:
    original_text: str
    rule_corrected_text: str
    ai_corrected_text: str


class CorrectionContextMemory:
    def __init__(self) -> None:
        self._previous_context: CorrectionContext | None = None

    def get_previous_context(self) -> CorrectionContext | None:
        return self._previous_context

    def remember(self, context: CorrectionContext) -> None:
        self._previous_context = context

    def clear(self) -> None:
        self._previous_context = None


correction_context_memory = CorrectionContextMemory()


def read_spark_credentials() -> XFYUNSparkCredentials:
    app_id = os.getenv("XF_APPID")
    api_key = os.getenv("XF_APIKEY")
    api_secret = os.getenv("XF_SECRET")

    if not app_id or not api_key or not api_secret:
        raise AICorrectionConfigurationError("Missing XFYUN Spark credentials")

    return XFYUNSparkCredentials(app_id=app_id, api_key=api_key, api_secret=api_secret)


def read_spark_api_url() -> str:
    return os.getenv("XF_SPARK_API_URL", DEFAULT_SPARK_API_URL)


def read_spark_domain() -> str:
    return os.getenv("XF_SPARK_DOMAIN", DEFAULT_SPARK_DOMAIN)


def create_spark_authorization(
    api_key: str,
    api_secret: str,
    host: str,
    path: str,
    date: str,
) -> str:
    signature_origin = f"host: {host}\ndate: {date}\nGET {path} HTTP/1.1"
    signature = hmac.new(
        api_secret.encode("utf-8"),
        signature_origin.encode("utf-8"),
        digestmod=hashlib.sha256,
    ).digest()
    signature_base64 = base64.b64encode(signature).decode("utf-8")
    authorization_origin = (
        f'api_key="{api_key}", algorithm="hmac-sha256", '
        f'headers="host date request-line", signature="{signature_base64}"'
    )
    return base64.b64encode(authorization_origin.encode("utf-8")).decode("utf-8")


def build_authenticated_spark_url(
    api_url: str,
    credentials: XFYUNSparkCredentials,
    date: str | None = None,
) -> str:
    parsed_url = urlparse(api_url)
    host = parsed_url.netloc
    path = parsed_url.path or "/"
    request_date = date or format_datetime(datetime.now(timezone.utc), usegmt=True)
    authorization = create_spark_authorization(
        credentials.api_key,
        credentials.api_secret,
        host,
        path,
        request_date,
    )
    query = urlencode(
        {
            "authorization": authorization,
            "date": request_date,
            "host": host,
        }
    )

    return urlunparse(
        (
            parsed_url.scheme,
            parsed_url.netloc,
            parsed_url.path,
            "",
            query,
            "",
        )
    )


def build_previous_context_prompt(previous_context: CorrectionContext | None) -> str:
    if previous_context is None:
        return "No previous correction context."

    return (
        "Previous correction context. Use it only to avoid repeating the same "
        "correction mistake:\n"
        f"originalText: {previous_context.original_text}\n"
        f"ruleCorrectedText: {previous_context.rule_corrected_text}\n"
        f"aiCorrectedText: {previous_context.ai_corrected_text}"
    )


def build_correction_payload(
    text: str,
    credentials: XFYUNSparkCredentials,
    domain: str | None = None,
    previous_context: CorrectionContext | None = None,
) -> dict[str, Any]:
    user_prompt = (
        f"{build_previous_context_prompt(previous_context)}\n\n"
        "Current English ASR text:\n"
        f"{text}"
    )

    return {
        "header": {
            "app_id": credentials.app_id,
        },
        "parameter": {
            "chat": {
                "domain": domain or read_spark_domain(),
                "temperature": 0.0,
                "max_tokens": 512,
            },
        },
        "payload": {
            "message": {
                "text": [
                    {
                        "role": "system",
                        "content": AI_CORRECTION_SYSTEM_PROMPT,
                    },
                    {
                        "role": "user",
                        "content": user_prompt,
                    },
                ],
            },
        },
    }


def dump_payload(payload: dict[str, Any]) -> str:
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))


def parse_spark_response_frame(response_data: dict[str, Any]) -> tuple[str, int | None]:
    header = response_data.get("header")

    if not isinstance(header, dict):
        raise AICorrectionError("XFYUN Spark response is missing header")

    if header.get("code") != 0:
        raise AICorrectionError("XFYUN Spark returned an error")

    choices = response_data.get("payload", {}).get("choices", {})
    text_chunks = choices.get("text", [])

    if not isinstance(text_chunks, list):
        raise AICorrectionError("XFYUN Spark response is missing correction text")

    content = ""
    for text_chunk in text_chunks:
        if isinstance(text_chunk, dict) and isinstance(text_chunk.get("content"), str):
            content += text_chunk["content"]

    status = choices.get("status", header.get("status"))
    return content, status if isinstance(status, int) else None


def validate_ai_corrected_text(text: str) -> str:
    corrected_text = re.sub(r"\s+", " ", text).strip()

    if not corrected_text:
        raise AICorrectionError("XFYUN Spark returned empty correction text")

    if _CJK_PATTERN.search(corrected_text):
        raise AICorrectionError("XFYUN Spark returned non-English correction text")

    if _EXPLANATION_PATTERN.search(corrected_text):
        raise AICorrectionError("XFYUN Spark returned explanatory text")

    return corrected_text


def second_check_corrected_text(text: str) -> str:
    return auto_correct_text(text)


async def ai_correct_text(
    text: str,
    previous_context: CorrectionContext | None = None,
    credentials: XFYUNSparkCredentials | None = None,
    connector: Any | None = None,
    api_url: str | None = None,
    domain: str | None = None,
) -> str:
    spark_credentials = credentials or read_spark_credentials()
    spark_api_url = api_url or read_spark_api_url()
    authenticated_url = build_authenticated_spark_url(spark_api_url, spark_credentials)
    payload = build_correction_payload(
        text,
        spark_credentials,
        domain=domain,
        previous_context=previous_context,
    )

    if connector is None:
        import websockets

        connector = websockets.connect

    try:
        async with connector(authenticated_url) as websocket:
            await websocket.send(dump_payload(payload))
            content_parts = []

            for _ in range(MAX_SPARK_FRAMES):
                raw_frame = await asyncio.wait_for(
                    websocket.recv(),
                    timeout=SPARK_RECV_TIMEOUT_SECONDS,
                )
                response_data = json.loads(raw_frame)
                content, status = parse_spark_response_frame(response_data)

                if content:
                    content_parts.append(content)

                if status == 2:
                    corrected_text = validate_ai_corrected_text("".join(content_parts))
                    return validate_ai_corrected_text(second_check_corrected_text(corrected_text))
    except AICorrectionError:
        raise
    except Exception as exc:
        raise AICorrectionError("XFYUN Spark correction request failed") from exc

    raise AICorrectionError("XFYUN Spark correction response did not finish")
