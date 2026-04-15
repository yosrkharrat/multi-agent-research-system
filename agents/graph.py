"""LangGraph StateGraph orchestration with Supervisor router for multi-agent coordination."""

from langgraph.graph import StateGraph, END

from .state import AgentState
from .planner import planner_node
from .researcher import researcher_node
from .critic import critic_node
from .writer import writer_node

MAX_ITERATIONS = 2  # prevent infinite Critic→Researcher loops


def supervisor_router(state: AgentState) -> str:
    """Routes to next agent. Enforces iteration cap on the Critic→Researcher loop."""

    if (
        state["next_agent"] == "researcher"
        and state.get("iteration", 0) >= MAX_ITERATIONS
    ):
        print(f"\n[Supervisor] Max iterations reached, forcing writer")
        return "writer"
    return state["next_agent"]


def build_graph():
    """Build and compile the full multi-agent orchestration graph."""

    graph = StateGraph(AgentState)

    graph.add_node("planner", planner_node)
    graph.add_node("researcher", researcher_node)
    graph.add_node("critic", critic_node)
    graph.add_node("writer", writer_node)

    graph.set_entry_point("planner")
    graph.add_edge("planner", "researcher")
    graph.add_edge("researcher", "critic")

    # Critic either loops back to researcher or proceeds to writer
    graph.add_conditional_edges(
        "critic",
        supervisor_router,
        {
            "researcher": "researcher",
            "writer": "writer",
        },
    )

    graph.add_edge("writer", END)
    return graph.compile()
