import asyncio
import json
import os
import queue
import sys
import threading
import traceback
from typing import AsyncGenerator
from urllib.error import URLError
from urllib.request import urlopen

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from config import PipelineConfig
from src.agents.graph import build_graph
from src.agents.eval import score_report
from persistence import get_run, list_runs, save_run

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class ResearchRequest(BaseModel):
    topic: str


OLLAMA_URL = "http://127.0.0.1:11434/api/tags"


def _ensure_ollama_running() -> None:
    """Fail fast with a clear message when Ollama is not reachable."""

    try:
        with urlopen(OLLAMA_URL, timeout=3) as response:
            if response.status >= 400:
                raise RuntimeError(f"Ollama health check failed with HTTP {response.status}.")
    except URLError as exc:
        raise RuntimeError(
            "Cannot connect to Ollama at http://127.0.0.1:11434. "
            "Start it with `ollama serve`, then retry."
        ) from exc


def _format_runtime_error(exc: Exception) -> str:
    text = str(exc)
    lowered = text.lower()
    if "10061" in text or "actively refused" in lowered or "connection refused" in lowered:
        return (
            "Cannot connect to Ollama at http://127.0.0.1:11434. "
            "Start it with `ollama serve`, then retry."
        )
    return text


def run_graph_with_events(topic: str, event_queue: queue.Queue, config: PipelineConfig | None = None) -> None:
    """Run the graph in a thread, pushing events into the queue."""

    config = config or PipelineConfig()

    def emit_status(agent: str, status: str, message: str, data=None) -> None:
        payload = {
            "agent": agent,
            "status": status,
            "message": message,
        }
        if data is not None:
            payload["data"] = data
        event_queue.put(payload)

    def emit_token(token: str) -> None:
        event_queue.put({"agent": "writer", "status": "streaming", "token": token})

    try:
        _ensure_ollama_running()
        graph = build_graph(config, on_token=emit_token, on_agent_status=emit_status)
        final_state = graph.invoke(
            {
                "messages": [],
                "topic": topic,
                "plan": [],
                "findings": [],
                "critique": "",
                "report": "",
                "next_agent": "",
                "iteration": 0,
            }
        )
        evaluation = score_report(final_state.get("report", ""), final_state.get("findings", []))
        final_state["eval_scores"] = evaluation
        run_id = save_run(topic, final_state)
        event_queue.put(
            {
                "agent": "done",
                "status": "done",
                "report": final_state["report"],
                "evaluation": evaluation,
                "run_id": run_id,
            }
        )
    except Exception as exc:
        traceback.print_exc()
        event_queue.put(
            {
                "agent": "error",
                "status": "error",
                "message": _format_runtime_error(exc),
            }
        )
    finally:
        event_queue.put(None)


@app.post("/research")
async def research(request: ResearchRequest):
    event_queue: queue.Queue = queue.Queue()
    config = PipelineConfig()

    thread = threading.Thread(
        target=run_graph_with_events,
        args=(request.topic, event_queue, config),
        daemon=True,
    )

    async def event_generator() -> AsyncGenerator[dict, None]:
        thread.start()
        while True:
            event = await asyncio.get_event_loop().run_in_executor(
                None,
                event_queue.get,
            )
            if event is None:
                break
            yield {"data": json.dumps(event)}

    return EventSourceResponse(event_generator())


@app.get("/runs")
async def runs():
    return {"runs": list_runs()}


@app.get("/runs/{run_id}")
async def run_detail(run_id: str):
    run = get_run(run_id)
    if run is None:
        return {"error": "run not found"}
    return run


@app.get("/")
async def root():
    with open(
        os.path.join(os.path.dirname(__file__), "..", "frontend", "index.html"),
        encoding="utf-8",
    ) as file:
        return HTMLResponse(file.read())
