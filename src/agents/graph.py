"""LangGraph StateGraph orchestration with Supervisor router for multi-agent coordination."""

from langgraph.graph import END, StateGraph

from .critic import critic_node
from .planner import planner_node
from .researcher import researcher_node
from .state import AgentState
from .writer import writer_node

MAX_ITERATIONS = 2


def supervisor_router(state: AgentState) -> str:
    """Routes to next agent. Enforces iteration cap on the Critic->Researcher loop."""

    if (
        state["next_agent"] == "researcher"
        and state.get("iteration", 0) >= MAX_ITERATIONS
    ):
        return "writer"
    return state["next_agent"]


def build_graph():
    graph = StateGraph(AgentState)

    graph.add_node("planner", planner_node)
    graph.add_node("researcher", researcher_node)
    graph.add_node("critic", critic_node)
    graph.add_node("writer", writer_node)

    graph.set_entry_point("planner")
    graph.add_edge("planner", "researcher")
    graph.add_edge("researcher", "critic")

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
