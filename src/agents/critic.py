"""Critic agent: evaluates research findings and decides if they are sufficient."""

from langchain_ollama import ChatOllama

from .state import AgentState

llm = ChatOllama(model="mistral", temperature=0.2, base_url="http://localhost:11434")

CRITIC_PROMPT = """You are a research critic. Review the findings below and decide if 
they are sufficient to write a comprehensive report on the topic.

Topic: {topic}
Research plan: {plan}

Findings:
{findings}

If the findings are sufficient, respond with exactly: APPROVED
If there are gaps, respond with: NEEDS_WORK: <one sentence describing what is missing>

Be strict but fair. Only approve if the core questions in the plan are addressed."""


def critic_node(state: AgentState) -> AgentState:
    """Evaluate findings and decide if research is sufficient or needs more work."""

    findings_text = "\n\n".join(state["findings"])
    plan_text = "\n".join(state["plan"])

    response = llm.invoke(
        CRITIC_PROMPT.format(
            topic=state["topic"],
            plan=plan_text,
            findings=findings_text,
        )
    )

    critique = response.content.strip()

    state["critique"] = critique
    state["iteration"] = state.get("iteration", 0) + 1

    if critique.startswith("APPROVED"):
        state["next_agent"] = "writer"
        print(f"\n[Critic] Approved after {state['iteration']} iteration(s)")
    else:
        state["next_agent"] = "researcher"
        print(f"\n[Critic] Sending back: {critique}")

    return state
