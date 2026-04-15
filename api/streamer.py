from __future__ import annotations

import asyncio
import json
from typing import AsyncGenerator

_queue: asyncio.Queue = asyncio.Queue()


def emit(event: str, data: dict) -> None:
    """Called from agent nodes to push an event into the stream."""

    _queue.put_nowait({"event": event, "data": data})


async def event_stream() -> AsyncGenerator[dict, None]:
    """SSE generator consumed by the frontend."""

    while True:
        item = await _queue.get()
        if item is None:
            yield {"event": "done", "data": "{}"}
            break
        payload = json.dumps(item["data"])
        yield {"event": item["event"], "data": payload}


def close_stream() -> None:
    _queue.put_nowait(None)
