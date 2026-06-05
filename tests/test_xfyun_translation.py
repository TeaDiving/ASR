import base64
import json

import httpx
import pytest

from backend.xfyun_translation import (
    TARGET_LANGUAGE,
    TRANSLATION_URL,
    TranslationConfigurationError,
    TranslationError,
    build_translation_payload,
    encode_text,
    parse_translation_response,
    translate_text,
)


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


class FakeResponse:
    def __init__(self, data: dict, status_code: int = 200) -> None:
        self.data = data
        self.status_code = status_code

    def json(self) -> dict:
        return self.data

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            request = httpx.Request("POST", TRANSLATION_URL)
            response = httpx.Response(self.status_code, request=request)
            raise httpx.HTTPStatusError("HTTP error", request=request, response=response)


class FakeAsyncClient:
    def __init__(self, response: FakeResponse) -> None:
        self.response = response
        self.url = None
        self.content = None
        self.headers = None

    async def post(self, url: str, *, content: bytes, headers: dict[str, str]) -> FakeResponse:
        self.url = url
        self.content = content
        self.headers = headers
        return self.response


def test_encode_text_uses_utf8_base64() -> None:
    assert encode_text("Good morning.") == base64.b64encode(
        "Good morning.".encode("utf-8")
    ).decode("utf-8")


def test_build_translation_payload_uses_english_to_chinese() -> None:
    payload = build_translation_payload("Good morning.", "app_id")

    assert payload["common"]["app_id"] == "app_id"
    assert payload["business"] == {"from": "en", "to": TARGET_LANGUAGE}
    assert payload["data"]["text"] == encode_text("Good morning.")


def test_parse_translation_response_returns_translated_text() -> None:
    response = {
        "code": 0,
        "message": "success",
        "data": {
            "result": {
                "trans_result": {
                    "src": "Good morning.",
                    "dst": "早上好。",
                }
            }
        },
    }

    assert parse_translation_response(response) == "早上好。"


def test_parse_translation_response_rejects_error_code() -> None:
    with pytest.raises(TranslationError):
        parse_translation_response({"code": 10001, "message": "error"})


@pytest.mark.anyio
async def test_translate_text_rejects_missing_credentials(monkeypatch) -> None:
    monkeypatch.delenv("XFYUN_APP_ID", raising=False)
    monkeypatch.delenv("XFYUN_API_KEY", raising=False)
    monkeypatch.delenv("XFYUN_API_SECRET", raising=False)

    with pytest.raises(TranslationConfigurationError):
        await translate_text("Good morning.", client=FakeAsyncClient(FakeResponse({})))


@pytest.mark.anyio
async def test_translate_text_posts_expected_payload(monkeypatch) -> None:
    monkeypatch.setenv("XFYUN_APP_ID", "test_app_id")
    monkeypatch.setenv("XFYUN_API_KEY", "test_api_key")
    monkeypatch.setenv("XFYUN_API_SECRET", "test_api_secret")

    client = FakeAsyncClient(
        FakeResponse(
            {
                "code": 0,
                "message": "success",
                "data": {
                    "result": {
                        "trans_result": {
                            "src": "Good morning.",
                            "dst": "早上好。",
                        }
                    }
                },
            }
        )
    )

    translated_text = await translate_text("Good morning.", client=client)
    payload = json.loads(client.content.decode("utf-8"))

    assert translated_text == "早上好。"
    assert client.url == TRANSLATION_URL
    assert payload == build_translation_payload("Good morning.", "test_app_id")
    assert client.headers["Authorization"].startswith('api_key="test_api_key"')
    assert client.headers["Digest"].startswith("SHA-256=")
