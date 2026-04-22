"""Planner agent: breaks down research topic into focused questions."""

from langchain_ollama import ChatOllama

from .state import AgentState
from config import PipelineConfig

PLANNER_PROMPT = """You are a research planner. Given a topic, break it down into 3 
specific research questions that together would give a comprehensive understanding.

Topic: {topic}

Return ONLY a numbered list of research questions, nothing else."""


def create_planner_node(config: PipelineConfig, on_agent_status=None):
    llm = ChatOllama(
        model=config.planner_model,
        temperature=0.1,
        base_url=config.ollama_base_url,
        num_predict=config.planner_num_predict,
    )

    def planner_node(state: AgentState) -> AgentState:
        """Generate a research plan by breaking the topic into questions."""

        if on_agent_status is not None:
            on_agent_status("planner", "running", "Breaking topic into research questions...")
        response = llm.invoke(PLANNER_PROMPT.format(topic=state["topic"]))
        questions = [
            line.strip()
            for line in response.content.split("\n")
            if line.strip() and line.strip()[0].isdigit()
        ][: config.planner_max_questions]
        state["plan"] = questions
        state["next_agent"] = "researcher"
        print(f"\n[Planner] Created {len(questions)} research questions")
        if on_agent_status is not None:
            on_agent_status(
                "planner",
                "done",
                f"Created {len(questions)} research questions",
                questions,
            )
        return state

    return planner_node


def planner_node(state: AgentState) -> AgentState:
    return create_planner_node(PipelineConfig())(state)
