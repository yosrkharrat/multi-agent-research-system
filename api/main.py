import asyncio
import json
import os
import queue
import sys
import threading
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from agents.graph import build_graph

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class ResearchRequest(BaseModel):
    topic: str


def run_graph_with_events(topic: str, event_queue: queue.Queue) -> None:
    """Run the graph in a thread, pushing events into the queue."""

    import agents.critic as critic_mod
    import agents.graph as graph_mod
    import agents.planner as planner_mod
    import agents.researcher as researcher_mod
    import agents.writer as writer_mod

    original_planner = planner_mod.planner_node
    original_researcher = researcher_mod.researcher_node
    original_critic = critic_mod.critic_node
    original_writer = writer_mod.writer_node

    def patched_planner(state):
        event_queue.put(
            {
                "agent": "planner",
                "status": "running",
                "message": "Breaking topic into research questions...",
            }
        )
        result = original_planner(state)
        event_queue.put(
            {
                "agent": "planner",
                "status": "done",
                "message": f"Created {len(result['plan'])} research questions",
                "data": result["plan"],
            }
        )
        return result

    def patched_researcher(state):
        iteration = state.get("iteration", 0)
        label = f"Research pass {iteration + 1}"
        event_queue.put(
            {
                "agent": "researcher",
                "status": "running",
                "message": f"{label} - searching {len(state.get('plan', [state['topic']]))} questions...",
            }
        )
        result = original_researcher(state)
        event_queue.put(
            {
                "agent": "researcher",
                "status": "done",
                "message": f"{label} complete - {len(result['findings'])} findings gathered",
            }
        )
        return result

    def patched_critic(state):
        event_queue.put(
            {
                "agent": "critic",
                "status": "running",
                "message": "Evaluating research quality...",
            }
        )
        result = original_critic(state)
        approved = result["critique"].startswith("APPROVED")
        event_queue.put(
            {
                "agent": "critic",
                "status": "done",
                "message": result["critique"],
                "approved": approved,
            }
        )
        return result

    def patched_writer(state):
        event_queue.put(
            {
                "agent": "writer",
                "status": "running",
                "message": "Writing final report...",
            }
        )
        result = original_writer(state)
        event_queue.put(
            {
                "agent": "writer",
                "status": "done",
                "message": "Report complete",
            }
        )
        return result

    planner_mod.planner_node = patched_planner
    researcher_mod.researcher_node = patched_researcher
    critic_mod.critic_node = patched_critic
    writer_mod.writer_node = patched_writer
    graph_mod.planner_node = patched_planner
    graph_mod.researcher_node = patched_researcher
    graph_mod.critic_node = patched_critic
    graph_mod.writer_node = patched_writer

    try:
        graph = build_graph()
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
        event_queue.put(
            {
                "agent": "done",
                "status": "done",
                "report": final_state["report"],
            }
        )
    except Exception as exc:
        event_queue.put({"agent": "error", "status": "error", "message": str(exc)})
    finally:
        planner_mod.planner_node = original_planner
        researcher_mod.researcher_node = original_researcher
        critic_mod.critic_node = original_critic
        writer_mod.writer_node = original_writer
        graph_mod.planner_node = original_planner
        graph_mod.researcher_node = original_researcher
        graph_mod.critic_node = original_critic
        graph_mod.writer_node = original_writer
        event_queue.put(None)


@app.post("/research")
async def research(request: ResearchRequest):
    event_queue: queue.Queue = queue.Queue()

    thread = threading.Thread(
        target=run_graph_with_events,
        args=(request.topic, event_queue),
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


@app.get("/")
async def root():
    with open(
        os.path.join(os.path.dirname(__file__), "..", "frontend", "index.html"),
        encoding="utf-8",
    ) as file:
        return HTMLResponse(file.read())
