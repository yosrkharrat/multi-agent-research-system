"""
STEP 6 — FastAPI + SSE streaming backend
=========================================
Full streaming API.  Run with:
    python run.py         (uses uvicorn, as before)

Endpoints
---------
POST /research              Start a new research run (streams SSE events)
GET  /runs                  List all saved runs
GET  /runs/{run_id}         Get a specific saved run
POST /runs/{run_id}/resume  Resume a checkpointed run from where it stopped
GET  /health                Health check

SSE event format
----------------
Each event is a JSON-encoded dict:

    {"type": "node_start",   "node": "planner",    "iteration": 0}
    {"type": "node_end",     "node": "planner",    "plan": [...]}
    {"type": "finding",      "question": "...",    "index": 2}
    {"type": "critic",       "verdict": "APPROVED","iteration": 1}
    {"type": "writer_token", "token": "Quantum"}   ← token-by-token
    {"type": "done",         "run_id": "abc12345", "eval": {...}}
    {"type": "error",        "message": "..."}

FRONT-END USAGE (plain HTML/JS)
--------------------------------
    const es = new EventSource('/research?' +
        new URLSearchParams({topic: 'What is quantum computing?'}));
    es.onmessage = e => {
        const data = JSON.parse(e.data);
        if (data.type === 'writer_token') appendToken(data.token);
        if (data.type === 'done') es.close();
    };

Or POST with fetch (topic as JSON body), handle ReadableStream.
"""

from __future__ import annotations

import asyncio
import json
import uuid
from typing import AsyncGenerator

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

from agents.graph import build_graph, make_config, resume_run
from agents.eval import score_report
from config import PipelineConfig
from persistence import save_run, list_runs, get_run


app = FastAPI(title="Multi-Agent Research API", version="4.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Request / Response models ─────────────────────────────────────────────────

class ResearchRequest(BaseModel):
    topic: str
    max_iterations: int = 1


# ── SSE streaming research endpoint ──────────────────────────────────────────

@app.post("/research")
async def start_research(req: ResearchRequest):
    """
    Start a research run and stream progress as Server-Sent Events.
    """
    return EventSourceResponse(
        _stream_research(req.topic, req.max_iterations),
        media_type="text/event-stream",
    )


async def _stream_research(
    topic: str, max_iterations: int
) -> AsyncGenerator[str, None]:
    run_id = str(uuid.uuid4())[:8]
    cfg = PipelineConfig(max_iterations=max_iterations)
    lg_config = make_config(run_id)

    async def emit(data: dict) -> str:
        return json.dumps(data)

    try:
        # Build graph with streaming callback
        graph = build_graph(cfg, enable_checkpointing=True)

        initial_state = {
            "messages": [],
            "topic": topic,
            "plan": [],
            "findings": [],
            "critique": "",
            "report": "",
            "next_agent": "",
            "iteration": 0,
        }

        yield await emit({"type": "run_start", "run_id": run_id, "topic": topic})

        # LangGraph .astream() yields state diffs after each node completes
        async for event in graph.astream(initial_state, config=lg_config):
            for node_name, state_update in event.items():
                if node_name == "__end__":
                    continue

                # ── Node started ──────────────────────────────────────────
                yield await emit({
                    "type": "node_start",
                    "node": node_name,
                    "iteration": state_update.get("iteration", 0),
                })
                await asyncio.sleep(0)  # yield control to event loop

                # ── Per-node enriched events ───────────────────────────────
                if node_name == "planner":
                    plan = state_update.get("plan", [])
                    yield await emit({
                        "type": "node_end",
                        "node": "planner",
                        "plan": plan,
                        "question_count": len(plan),
                    })

                elif node_name == "researcher":
                    findings = state_update.get("findings", [])
                    for i, f in enumerate(findings):
                        if isinstance(f, dict):
                            preview = f.get("summary", str(f))[:120]
                        else:
                            preview = str(f)[:120]
                        if len(preview) > 120:
                            preview = preview[:120] + "…"
                        yield await emit({
                            "type": "finding",
                            "index": i + 1,
                            "total": len(findings),
                            "preview": preview,
                        })
                        await asyncio.sleep(0)

                elif node_name == "critic":
                    yield await emit({
                        "type": "critic",
                        "verdict": state_update.get("next_agent", ""),
                        "critique": state_update.get("critique", ""),
                        "iteration": state_update.get("iteration", 0),
                    })

                elif node_name == "writer":
                    report = state_update.get("report", "")
                    # Stream writer output token-by-token via word split
                    # (real token streaming requires LangChain callbacks — see note)
                    words = report.split()
                    chunk_size = 5  # emit 5 words at a time
                    for i in range(0, len(words), chunk_size):
                        chunk = " ".join(words[i : i + chunk_size])
                        yield await emit({"type": "writer_token", "token": chunk + " "})
                        await asyncio.sleep(0.01)  # small delay for effect

        # ── Finalize ───────────────────────────────────────────────────────
        # Retrieve final state from checkpoint
        final_state = graph.get_state(lg_config).values

        eval_scores = score_report(
            final_state.get("report", ""),
            final_state.get("plan", []),
        )
        final_state["eval_scores"] = eval_scores
        saved_id = save_run(topic, final_state)

        yield await emit({
            "type": "done",
            "run_id": saved_id,
            "thread_id": run_id,
            "eval": eval_scores,
        })

    except Exception as exc:  # noqa: BLE001
        yield await emit({"type": "error", "message": str(exc)})


# ── Run management ────────────────────────────────────────────────────────────

@app.get("/runs")
def get_runs():
    return {"runs": list_runs()}


@app.get("/runs/{run_id}")
def get_run_by_id(run_id: str):
    run = get_run(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail=f"Run '{run_id}' not found")
    return run


@app.post("/runs/{thread_id}/resume")
async def resume_run_endpoint(thread_id: str):
    """
    Resume a checkpointed run that was paused (e.g., interrupted before writer).
    Streams the remaining SSE events just like /research.
    """
    return EventSourceResponse(
        _stream_resume(thread_id),
        media_type="text/event-stream",
    )


async def _stream_resume(thread_id: str) -> AsyncGenerator[str, None]:
    async def emit(data: dict) -> str:
        return json.dumps(data)

    try:
        graph, lg_config = resume_run(thread_id)
        yield await emit({"type": "resume", "thread_id": thread_id})

        async for event in graph.astream(None, config=lg_config):
            for node_name, state_update in event.items():
                if node_name == "__end__":
                    continue
                yield await emit({"type": "node_start", "node": node_name})
                await asyncio.sleep(0)

                if node_name == "writer":
                    report = state_update.get("report", "")
                    for word in report.split():
                        yield await emit({"type": "writer_token", "token": word + " "})
                        await asyncio.sleep(0.01)

        final_state = graph.get_state(lg_config).values
        eval_scores = score_report(
            final_state.get("report", ""),
            final_state.get("plan", []),
        )
        yield await emit({"type": "done", "thread_id": thread_id, "eval": eval_scores})

    except Exception as exc:
        yield await emit({"type": "error", "message": str(exc)})


# ── Health ────────────────────────────────────────────────────────────────────

@app.get("/health")
def health():
    return {"status": "ok", "version": "4.0.0"}


# ── Live demo UI (optional, served at /) ──────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
def demo_ui():
    return """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Research Agent</title>
<style>
  body { font-family: system-ui, sans-serif; max-width: 860px; margin: 40px auto; padding: 0 20px; }
  input { width: 100%; padding: 10px; font-size: 15px; border: 1px solid #ccc; border-radius: 6px; box-sizing: border-box; }
  button { margin-top: 10px; padding: 10px 24px; background: #0066cc; color: white; border: none; border-radius: 6px; cursor: pointer; font-size: 15px; }
  button:disabled { opacity: 0.5; }
  #log { margin-top: 24px; font-size: 13px; color: #555; }
  #report { margin-top: 24px; white-space: pre-wrap; font-size: 15px; line-height: 1.7; border-top: 1px solid #eee; padding-top: 16px; }
  .badge { display: inline-block; padding: 2px 8px; border-radius: 4px; font-size: 12px; font-weight: 600; margin-right: 6px; }
  .planner   { background: #fff3cd; color: #664d03; }
  .researcher{ background: #d1e7dd; color: #0a3622; }
  .critic    { background: #f8d7da; color: #58151c; }
  .writer    { background: #cfe2ff; color: #052c65; }
</style>
</head>
<body>
<h2>Multi-Agent Research</h2>
<input id="topic" placeholder="Enter a research topic…" value="What are the key breakthroughs in quantum computing?" />
<button id="btn" onclick="startResearch()">Start</button>
<div id="log"></div>
<div id="report"></div>
<script>
function startResearch() {
  const topic = document.getElementById('topic').value.trim();
  if (!topic) return;
  document.getElementById('btn').disabled = true;
  document.getElementById('log').innerHTML = '';
  document.getElementById('report').innerHTML = '';

  fetch('/research', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({topic, max_iterations: 1}),
  }).then(res => {
    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';

    function read() {
      reader.read().then(({done, value}) => {
        if (done) { document.getElementById('btn').disabled = false; return; }
        buffer += decoder.decode(value, {stream: true});
        const lines = buffer.split('\\n');
        buffer = lines.pop();
        lines.forEach(line => {
          if (!line.startsWith('data:')) return;
          try {
            const d = JSON.parse(line.slice(5).trim());
            handleEvent(d);
          } catch {}
        });
        read();
      });
    }
    read();
  });
}

function handleEvent(d) {
  const log = document.getElementById('log');
  const report = document.getElementById('report');
  if (d.type === 'node_start') {
    log.innerHTML += `<span class="badge ${d.node}">${d.node}</span> started<br>`;
  } else if (d.type === 'node_end' && d.node === 'planner') {
    log.innerHTML += `&nbsp;&nbsp;Plan: ${d.plan.length} questions<br>`;
  } else if (d.type === 'finding') {
    log.innerHTML += `&nbsp;&nbsp;Finding ${d.index}/${d.total}: ${d.preview}<br>`;
  } else if (d.type === 'critic') {
    log.innerHTML += `&nbsp;&nbsp;Critic: <b>${d.verdict}</b> (iteration ${d.iteration})<br>`;
  } else if (d.type === 'writer_token') {
    report.textContent += d.token;
  } else if (d.type === 'done') {
    log.innerHTML += `<br>✓ Done · run ${d.run_id} · score ${(d.eval.overall * 100).toFixed(0)}%<br>`;
    document.getElementById('btn').disabled = false;
  } else if (d.type === 'error') {
    log.innerHTML += `<span style="color:red">Error: ${d.message}</span><br>`;
    document.getElementById('btn').disabled = false;
  }
  log.scrollTop = log.scrollHeight;
}
</script>
</body>
</html>"""
