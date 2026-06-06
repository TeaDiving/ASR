import asyncio
import json

import pytest

from backend.main import subtitle_stream_api
from backend.subtitle_stream import SubtitleBroadcaster, format_sse_event


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


def sample_subtitle_message() -> dict:
    return {
        "id": "subtitle_001",
        "sourceText": "Good morning everyone.",
        "normalizedText": "Good morning everyone.",
        "translatedText": "大家早上好。",
        "timestamp": 1710000000000,
        "isFinal": True,
    }


def test_format_sse_event_contains_subtitle_event_and_json_data() -> None:
    message = sample_subtitle_message()
    event = format_sse_event(message)

    assert event.startswith("event: subtitle\n")
    assert "\ndata: " in event
    assert event.endswith("\n\n")

    data_line = next(line for line in event.splitlines() if line.startswith("data: "))
    assert json.loads(data_line.removeprefix("data: ")) == message


@pytest.mark.anyio
async def test_subtitle_stream_allows_extension_cors() -> None:
    class FakeRequest:
        async def is_disconnected(self) -> bool:
            return True

    response = await subtitle_stream_api(FakeRequest())

    assert response.headers["access-control-allow-origin"] == "*"


@pytest.mark.anyio
async def test_broadcaster_publishes_to_one_subscriber() -> None:
    broadcaster = SubtitleBroadcaster()
    queue = broadcaster.subscribe()
    message = sample_subtitle_message()

    await broadcaster.publish(message)

    assert await asyncio.wait_for(queue.get(), timeout=1) == message


@pytest.mark.anyio
async def test_broadcaster_publishes_to_multiple_subscribers() -> None:
    broadcaster = SubtitleBroadcaster()
    first_queue = broadcaster.subscribe()
    second_queue = broadcaster.subscribe()
    message = sample_subtitle_message()

    await broadcaster.publish(message)

    assert await asyncio.wait_for(first_queue.get(), timeout=1) == message
    assert await asyncio.wait_for(second_queue.get(), timeout=1) == message


@pytest.mark.anyio
async def test_broadcaster_unsubscribe_stops_future_delivery() -> None:
    broadcaster = SubtitleBroadcaster()
    queue = broadcaster.subscribe()
    broadcaster.unsubscribe(queue)

    await broadcaster.publish(sample_subtitle_message())

    assert broadcaster.subscriber_count == 0
    assert queue.empty()
