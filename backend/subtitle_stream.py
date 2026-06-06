import asyncio
import json
from typing import Any


def format_sse_event(message: dict[str, Any]) -> str:
    data = json.dumps(message, ensure_ascii=False, separators=(",", ":"))
    return f"event: subtitle\ndata: {data}\n\n"


class SubtitleBroadcaster:
    def __init__(self) -> None:
        self._subscribers: set[asyncio.Queue[dict[str, Any]]] = set()

    def subscribe(self) -> asyncio.Queue[dict[str, Any]]:
        queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue()
        self._subscribers.add(queue)
        return queue

    def unsubscribe(self, queue: asyncio.Queue[dict[str, Any]]) -> None:
        self._subscribers.discard(queue)

    async def publish(self, message: dict[str, Any]) -> None:
        for queue in list(self._subscribers):
            await queue.put(message)

    @property
    def subscriber_count(self) -> int:
        return len(self._subscribers)


subtitle_broadcaster = SubtitleBroadcaster()
