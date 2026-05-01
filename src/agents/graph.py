"""
STEP 3 — LangGraph checkpointing (thread-scoped, automatic)
============================================================
Drop-in replacement for your existing  src/agents/graph.py

What this adds vs Phase 3:
  • SqliteSaver  — every node transition is written to  runs/checkpoints.db
  • thread_id    — every run gets a stable ID so it can be resumed
  • interrupt_before=["writer"]  — pauses for human approval before the
                                   final report is generated (optional)
  • supervisor_router is unchanged — just re-exported here

HOW TO RESUME A CRASHED RUN
-----------------------------
    from agents.graph import build_graph, resume_run
    from config import PipelineConfig

    graph, config = resume_run("abc12345")   # pass the run_id from save_run()
    result = graph.invoke(None, config=config)  # None = resume from checkpoint

HOW TO APPROVE A PAUSED RUN (human-in-the-loop)
-------------------------------------------------
    # Run is paused at the 'writer' node waiting for approval
    graph, config = resume_run("abc12345")
    # Inspect state:
    snapshot = graph.get_state(config)
    print(snapshot.values["critique"])
    # Approve:
    result = graph.invoke(None, config=config)
"""

from __future__ import annotations

import importlib.util
from pathlib import Path
from typing import Literal

if importlib.util.find_spec("langgraph.checkpoint.sqlite") is not None:
    from importlib import import_module

    SqliteSaver = getattr(
        import_module("langgraph.checkpoint.sqlite"),
        "SqliteSaver",
        None,
    )
else:
    SqliteSaver = None

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph

from agents.state import AgentState
from agents.planner import create_planner_node
from agents.researcher import create_researcher_node
from agents.critic import create_critic_node
from agents.writer import create_writer_node
from config import PipelineConfig


# ── Paths ─────────────────────────────────────────────────────────────────────

CHECKPOINT_DB = Path("runs/checkpoints.db")


# ── Supervisor router (unchanged logic, added type hint) ──────────────────────

def supervisor_router(
    state: AgentState,
) -> Literal["researcher", "writer", "__end__"]:
    """
    Read state["next_agent"] and enforce the MAX_ITERATIONS cap.

    Routing table
    -------------
    next_agent == "researcher"  AND  iteration < max  → "researcher"
    next_agent == "researcher"  AND  iteration >= max → "writer"  (cap hit)
    next_agent == "writer"                            → "writer"
    next_agent == "end"  OR  anything else            → "__end__"
    """
    next_agent = state.get("next_agent", "")
    iteration = state.get("iteration", 0)
    max_iterations = state.get("_max_iterations", 2)

    if next_agent == "researcher":
        if iteration >= max_iterations:
            print(
                f"  [Supervisor] Max iterations ({max_iterations}) reached — "
                "forcing Writer"
            )
            return "writer"
        return "researcher"

    if next_agent == "writer":
        return "writer"

    return "__end__"


# ── Graph builder ─────────────────────────────────────────────────────────────

def build_graph(
    config: PipelineConfig,
    *,
    enable_checkpointing: bool = True,
    interrupt_before_writer: bool = False,
) -> StateGraph:
    """
    Build and compile the multi-agent StateGraph.

    Parameters
    ----------
    config : PipelineConfig
        Model names, iteration caps, latency guards.
    enable_checkpointing : bool
        If True (default), attach SqliteSaver so every node transition is
        persisted to  runs/checkpoints.db.
    interrupt_before_writer : bool
        If True, the graph pauses before the Writer node and waits for
        human approval via  graph.invoke(None, config=...)  to resume.

    Returns
    -------
    Compiled StateGraph ready to call .invoke() on.
    """

    # ── Node factories ────────────────────────────────────────────────────────
    planner_node = create_planner_node(config)
    researcher_node = create_researcher_node(config)
    critic_node = create_critic_node(config)
    writer_node = create_writer_node(config)

    # ── Inject max_iterations into state via a thin wrapper ──────────────────
    # This lets supervisor_router read it without touching PipelineConfig.
    _max_iter = config.max_iterations

    def planner_with_meta(state: AgentState) -> AgentState:
        result = planner_node(state)
        return {**result, "_max_iterations": _max_iter}

    # ── Graph definition ──────────────────────────────────────────────────────
    builder = StateGraph(AgentState)

    builder.add_node("planner", planner_with_meta)
    builder.add_node("researcher", researcher_node)
    builder.add_node("critic", critic_node)
    builder.add_node("writer", writer_node)

    builder.set_entry_point("planner")
    builder.add_edge("planner", "researcher")
    builder.add_edge("researcher", "critic")

    builder.add_conditional_edges(
        "critic",
        supervisor_router,
        {
            "researcher": "researcher",
            "writer": "writer",
            "__end__": END,
        },
    )

    builder.add_edge("writer", END)

    # ── Compile ───────────────────────────────────────────────────────────────
    compile_kwargs: dict = {}

    if enable_checkpointing:
        CHECKPOINT_DB.parent.mkdir(exist_ok=True)
        if SqliteSaver is not None:
            # SqliteSaver.from_conn_string creates the DB file if it doesn't exist
            checkpointer = SqliteSaver.from_conn_string(str(CHECKPOINT_DB))
            print(f"  [Graph] Checkpointing enabled → {CHECKPOINT_DB}")
        else:
            checkpointer = MemorySaver()
            print("  [Graph] SqliteSaver unavailable; using in-memory checkpointing")
        compile_kwargs["checkpointer"] = checkpointer

    if interrupt_before_writer:
        compile_kwargs["interrupt_before"] = ["writer"]
        print("  [Graph] Human-in-the-loop: run will pause before Writer")

    return builder.compile(**compile_kwargs)


# ── Thread config helper ──────────────────────────────────────────────────────

def make_config(thread_id: str) -> dict:
    """
    Return the config dict that LangGraph needs to scope a run to a thread.

    Usage:
        config = make_config(run_id)
        result = graph.invoke(initial_state, config=config)
    """
    return {"configurable": {"thread_id": thread_id}}


# ── Resume helper ─────────────────────────────────────────────────────────────

def resume_run(
    thread_id: str,
    config: PipelineConfig | None = None,
    interrupt_before_writer: bool = False,
):
    """
    Rebuild the graph and return (graph, langgraph_config) ready to resume.

    Example
    -------
        graph, lg_config = resume_run("abc12345")
        result = graph.invoke(None, config=lg_config)
        # None means "don't reset state, resume from checkpoint"
    """
    cfg = config or PipelineConfig()
    graph = build_graph(
        cfg,
        enable_checkpointing=True,
        interrupt_before_writer=interrupt_before_writer,
    )
    lg_config = make_config(thread_id)
    return graph, lg_config
