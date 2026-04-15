"""Writer agent: synthesizes findings into a structured markdown report."""

from langchain_ollama import ChatOllama

from .state import AgentState

llm = ChatOllama(model="llama3", temperature=0.4, base_url="http://localhost:11434")

WRITER_PROMPT = """You are a research report writer. Using the findings below, write a 
well-structured markdown report on the topic.

Topic: {topic}

Findings:
{findings}

Write the report with:
- A brief executive summary
- Clearly headed sections covering the key aspects
- A short conclusion

Use markdown formatting. Be informative and precise."""


def writer_node(state: AgentState) -> AgentState:
    """Generate a final markdown report from research findings."""

    print("\n[Writer] Generating final report...")
    findings_text = "\n\n".join(state["findings"])

    response = llm.invoke(
        WRITER_PROMPT.format(
            topic=state["topic"],
            findings=findings_text,
        )
    )

    state["report"] = response.content.strip()
    state["next_agent"] = "end"
    return state
