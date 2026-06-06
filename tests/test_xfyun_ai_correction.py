import base64
import json
from urllib.parse import parse_qs, urlparse

import pytest

from backend.xfyun_ai_correction import (
    AI_CORRECTION_SYSTEM_PROMPT,
    AICorrectionConfigurationError,
    AICorrectionError,
    CorrectionContext,
    XFYUNSparkCredentials,
    ai_correct_text,
    build_authenticated_spark_url,
    build_correction_payload,
    correction_context_memory,
    read_spark_credentials,
    second_check_corrected_text,
    validate_ai_corrected_text,
)


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


def clear_spark_env(monkeypatch) -> None:
    for name in (
        "XF_APPID",
        "XF_APIKEY",
        "XF_SECRET",
        "XF_SPARK_API_URL",
        "XF_SPARK_DOMAIN",
    ):
        monkeypatch.delenv(name, raising=False)


class FakeWebSocket:
    def __init__(self, frames: list[dict]) -> None:
        self.frames = list(frames)
        self.sent_messages: list[str] = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        return None

    async def send(self, message: str) -> None:
        self.sent_messages.append(message)

    async def recv(self) -> str:
        if not self.frames:
            raise RuntimeError("No more fake frames")

        return json.dumps(self.frames.pop(0), ensure_ascii=False)


class FakeConnector:
    def __init__(self, websocket: FakeWebSocket) -> None:
        self.websocket = websocket
        self.url = None

    def __call__(self, url: str) -> FakeWebSocket:
        self.url = url
        return self.websocket


def success_frame(content: str, status: int = 2) -> dict:
    return {
        "header": {
            "code": 0,
            "status": status,
        },
        "payload": {
            "choices": {
                "status": status,
                "text": [
                    {
                        "role": "assistant",
                        "content": content,
                    }
                ],
            }
        },
    }


def test_read_spark_credentials_uses_xf_env(monkeypatch) -> None:
    clear_spark_env(monkeypatch)
    monkeypatch.setenv("XF_APPID", "app_id")
    monkeypatch.setenv("XF_APIKEY", "api_key")
    monkeypatch.setenv("XF_SECRET", "api_secret")

    assert read_spark_credentials() == XFYUNSparkCredentials(
        app_id="app_id",
        api_key="api_key",
        api_secret="api_secret",
    )


def test_read_spark_credentials_rejects_missing_env(monkeypatch) -> None:
    clear_spark_env(monkeypatch)

    with pytest.raises(AICorrectionConfigurationError):
        read_spark_credentials()


def test_build_authenticated_spark_url_contains_signed_query() -> None:
    credentials = XFYUNSparkCredentials(
        app_id="app_id",
        api_key="api_key",
        api_secret="api_secret",
    )
    date = "Fri, 05 Jun 2026 12:00:00 GMT"

    url = build_authenticated_spark_url(
        "wss://spark-api.xf-yun.com/v4.0/chat",
        credentials,
        date=date,
    )
    parsed_url = urlparse(url)
    query = parse_qs(parsed_url.query)
    authorization = base64.b64decode(query["authorization"][0]).decode("utf-8")

    assert parsed_url.scheme == "wss"
    assert parsed_url.netloc == "spark-api.xf-yun.com"
    assert query["host"] == ["spark-api.xf-yun.com"]
    assert query["date"] == [date]
    assert 'api_key="api_key"' in authorization
    assert 'algorithm="hmac-sha256"' in authorization
    assert 'headers="host date request-line"' in authorization
    assert 'signature="' in authorization


def test_build_correction_payload_contains_prompt_and_previous_context() -> None:
    credentials = XFYUNSparkCredentials(
        app_id="app_id",
        api_key="api_key",
        api_secret="api_secret",
    )
    previous_context = CorrectionContext(
        original_text="hellow",
        rule_corrected_text="Hello",
        ai_corrected_text="Hello",
    )

    payload = build_correction_payload(
        "OpenAI is useful.",
        credentials,
        domain="4.0Ultra",
        previous_context=previous_context,
    )
    messages = payload["payload"]["message"]["text"]

    assert payload["header"]["app_id"] == "app_id"
    assert payload["parameter"]["chat"]["domain"] == "4.0Ultra"
    assert messages[0] == {
        "role": "system",
        "content": AI_CORRECTION_SYSTEM_PROMPT,
    }
    assert messages[1]["role"] == "user"
    assert "previous correction context" in messages[1]["content"].lower()
    assert "originalText: hellow" in messages[1]["content"]
    assert "aiCorrectedText: Hello" in messages[1]["content"]
    assert "Current English ASR text:\nOpenAI is useful." in messages[1]["content"]


@pytest.mark.anyio
async def test_ai_correct_text_returns_spark_correction() -> None:
    websocket = FakeWebSocket([success_frame("Hello world")])
    connector = FakeConnector(websocket)
    credentials = XFYUNSparkCredentials(
        app_id="app_id",
        api_key="api_key",
        api_secret="api_secret",
    )

    corrected_text = await ai_correct_text(
        "hellow wrold",
        credentials=credentials,
        connector=connector,
        api_url="wss://spark-api.xf-yun.com/v4.0/chat",
        domain="4.0Ultra",
    )
    sent_payload = json.loads(websocket.sent_messages[0])

    assert corrected_text == "Hello world"
    assert connector.url.startswith("wss://spark-api.xf-yun.com/v4.0/chat?")
    assert sent_payload["header"]["app_id"] == "app_id"
    assert sent_payload["payload"]["message"]["text"][0]["content"] == AI_CORRECTION_SYSTEM_PROMPT


@pytest.mark.anyio
async def test_ai_correct_text_rejects_spark_error_response() -> None:
    websocket = FakeWebSocket(
        [
            {
                "header": {
                    "code": 10001,
                    "message": "error",
                    "status": 2,
                }
            }
        ]
    )
    connector = FakeConnector(websocket)

    with pytest.raises(AICorrectionError):
        await ai_correct_text(
            "hello",
            credentials=XFYUNSparkCredentials("app_id", "api_key", "api_secret"),
            connector=connector,
        )


@pytest.mark.anyio
async def test_ai_correct_text_rejects_empty_output() -> None:
    websocket = FakeWebSocket([success_frame("")])
    connector = FakeConnector(websocket)

    with pytest.raises(AICorrectionError):
        await ai_correct_text(
            "hello",
            credentials=XFYUNSparkCredentials("app_id", "api_key", "api_secret"),
            connector=connector,
        )


@pytest.mark.anyio
async def test_ai_correct_text_rejects_output_empty_after_second_check() -> None:
    websocket = FakeWebSocket([success_frame("x")])
    connector = FakeConnector(websocket)

    with pytest.raises(AICorrectionError):
        await ai_correct_text(
            "hello",
            credentials=XFYUNSparkCredentials("app_id", "api_key", "api_secret"),
            connector=connector,
        )


@pytest.mark.anyio
async def test_ai_correct_text_rejects_chinese_output() -> None:
    websocket = FakeWebSocket([success_frame("你好")])
    connector = FakeConnector(websocket)

    with pytest.raises(AICorrectionError):
        await ai_correct_text(
            "hello",
            credentials=XFYUNSparkCredentials("app_id", "api_key", "api_secret"),
            connector=connector,
        )


@pytest.mark.anyio
async def test_ai_correct_text_rejects_connection_failure() -> None:
    def broken_connector(url: str):
        raise RuntimeError("connection failed")

    with pytest.raises(AICorrectionError):
        await ai_correct_text(
            "hello",
            credentials=XFYUNSparkCredentials("app_id", "api_key", "api_secret"),
            connector=broken_connector,
        )


def test_validate_ai_corrected_text_rejects_explanatory_text() -> None:
    with pytest.raises(AICorrectionError):
        validate_ai_corrected_text("Corrected: Hello world")


def test_second_check_corrected_text_reuses_rule_cleanup() -> None:
    assert second_check_corrected_text("hello hello x world") == "Hello world"


def test_correction_context_memory_keeps_only_latest_context() -> None:
    first_context = CorrectionContext(
        original_text="first",
        rule_corrected_text="First",
        ai_corrected_text="First",
    )
    second_context = CorrectionContext(
        original_text="second",
        rule_corrected_text="Second",
        ai_corrected_text="Second",
    )

    correction_context_memory.clear()
    correction_context_memory.remember(first_context)
    correction_context_memory.remember(second_context)

    assert correction_context_memory.get_previous_context() == second_context
