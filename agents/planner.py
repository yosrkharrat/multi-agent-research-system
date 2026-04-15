"""Planner agent: breaks down research topic into focused questions."""

from langchain_ollama import ChatOllama

from .state import AgentState

llm = ChatOllama(model="mistral", temperature=0.1, base_url="http://localhost:11434")

PLANNER_PROMPT = """You are a research planner. Given a topic, break it down into 3-5 
specific research questions that together would give a comprehensive understanding.

Topic: {topic}

Return ONLY a numbered list of research questions, nothing else."""


def planner_node(state: AgentState) -> AgentState:
    """Generate a research plan by breaking the topic into questions."""

    response = llm.invoke(PLANNER_PROMPT.format(topic=state["topic"]))
    questions = [
        line.strip()
        for line in response.content.split("\n")
        if line.strip() and line.strip()[0].isdigit()
    ]
    state["plan"] = questions
    state["next_agent"] = "researcher"
    print(f"\n[Planner] Created {len(questions)} research questions")
    return state
