"""Writer agent: synthesizes findings into a structured markdown report."""

from langchain_ollama import ChatOllama

from .state import AgentState

llm = ChatOllama(model="llama3", temperature=0.4, base_url="http://localhost:11434")

WRITER_PROMPT = """You are a research report writer. Using the findings below, write a 
well-structured markdown report on the topic.

Topic: {topic}

Findings:
{findings}

Structure the report with exactly these sections, in this exact order:
## Executive Summary (3-4 sentences)
## Background
## Key Findings (use sub-headings per research question)
## Evidence & Examples (specific dates, names, figures)
## Open Questions (what is still uncertain)
## Sources

Do not add other top-level sections.
In ## Sources, list only URLs provided below.

Use markdown formatting. Be informative and precise.

URLs to include in ## Sources:
{sources}"""


def writer_node(state: AgentState) -> AgentState:
    """Generate a final markdown report from research findings."""

    print("\n[Writer] Generating final report...")
    findings_blocks = []
    all_sources = []
    seen = set()

    for item in state["findings"]:
        if isinstance(item, dict):
            confidence = int(item.get("confidence", 0))
            if confidence < 3:
                continue
            question = str(item.get("question", ""))
            content = str(item.get("content", ""))
            sources = item.get("sources", [])
            source_lines = []
            if isinstance(sources, list):
                for src in sources:
                    src_str = str(src).strip()
                    if src_str:
                        source_lines.append(f"- {src_str}")
                        if src_str not in seen:
                            seen.add(src_str)
                            all_sources.append(src_str)

            block = f"Question: {question}\nConfidence: {confidence}/5\nSummary: {content}"
            if source_lines:
                block += "\nSources:\n" + "\n".join(source_lines)
            findings_blocks.append(block)

    findings_text = "\n\n".join(findings_blocks) or "No findings passed the confidence threshold (>=3)."
    sources_text = "\n".join(f"- {url}" for url in all_sources) or "- No source URLs available from confidence>=3 findings"

    prompt_text = WRITER_PROMPT.format(
        topic=state["topic"],
        findings=findings_text,
        sources=sources_text,
    )

    event_queue = state.get("_event_queue")
    report_parts = []
    for chunk in llm.stream(prompt_text):
        token = getattr(chunk, "content", "") or ""
        if token:
            report_parts.append(token)
            if event_queue is not None:
                event_queue.put(
                    {
                        "agent": "writer",
                        "status": "streaming",
                        "token": token,
                    }
                )

    state["report"] = "".join(report_parts).strip()
    state["next_agent"] = "end"
    return state
