"""LangGraph StateGraph orchestration with Supervisor router for multi-agent coordination."""

from langgraph.graph import END, StateGraph

from config import PipelineConfig

from .critic import create_critic_node
from .planner import create_planner_node
from .researcher import create_researcher_node
from .state import AgentState
from .writer import create_writer_node


def supervisor_router(state: AgentState, max_iterations: int) -> str:
    """Routes to next agent. Enforces iteration cap on the Critic->Researcher loop."""

    if (
        state["next_agent"] == "researcher"
        and state.get("iteration", 0) >= max_iterations
    ):
        return "writer"
    return state["next_agent"]


def build_graph(
    config: PipelineConfig | None = None,
    on_token=None,
    on_agent_status=None,
):
    config = config or PipelineConfig()
    planner_node = create_planner_node(config, on_agent_status=on_agent_status)
    researcher_node = create_researcher_node(config, on_agent_status=on_agent_status)
    critic_node = create_critic_node(config, on_agent_status=on_agent_status)
    writer_node = create_writer_node(
        config,
        on_token=on_token,
        on_agent_status=on_agent_status,
    )

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
        lambda state: supervisor_router(state, config.max_iterations),
        {
            "researcher": "researcher",
            "writer": "writer",
        },
    )

    graph.add_edge("writer", END)
    return graph.compile()
