"""Writer agent: synthesizes findings into a structured markdown report."""

from langchain_ollama import ChatOllama

from .state import AgentState
from config import PipelineConfig

WRITER_PROMPT = """You are a research report writer. Using the findings below, write a 
well-structured markdown report on the topic.

Topic: {topic}

Findings:
{findings}

For every claim, cite the source URL in markdown link format. Do not include any claim without a source.
Use inline citations immediately after each factual claim, for example: ... [source](https://example.com).

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


def create_writer_node(config: PipelineConfig, on_token=None, on_agent_status=None):
    llm = ChatOllama(
        model=config.writer_model,
        temperature=0.4,
        base_url=config.ollama_base_url,
        num_predict=config.writer_num_predict,
    )

    def writer_node(state: AgentState) -> AgentState:
        """Generate a final markdown report from research findings."""

        print("\n[Writer] Generating final report...")
        if on_agent_status is not None:
            on_agent_status("writer", "running", "Writing final report...")
        findings_blocks = []
        all_sources = []
        seen = set()

        for item in state["findings"]:
            if isinstance(item, dict):
                confidence = int(item.get("confidence", 0))
                if confidence < config.confidence_threshold:
                    continue
                question = str(item.get("question", ""))
                summary = str(item.get("summary", item.get("content", "")))
                key_facts = item.get("key_facts", [])
                sources = item.get("sources", [])
                source_lines = []
                if isinstance(sources, list):
                    for src in sources:
                        if isinstance(src, dict):
                            src_url = str(src.get("url", "")).strip()
                            src_title = str(src.get("title", "")).strip() or src_url
                        else:
                            src_url = str(src).strip()
                            src_title = src_url

                        if src_url:
                            source_lines.append(f"- {src_title}: {src_url}")
                            if src_url not in seen:
                                seen.add(src_url)
                                all_sources.append(src_url)

                fact_lines = []
                if isinstance(key_facts, list):
                    for fact in key_facts:
                        fact_text = str(fact).strip()
                        if fact_text:
                            fact_lines.append(f"- {fact_text}")

                block = f"Question: {question}\nConfidence: {confidence}/5\nSummary: {summary}"
                if fact_lines:
                    block += "\nKey facts:\n" + "\n".join(fact_lines)
                if source_lines:
                    block += "\nSources:\n" + "\n".join(source_lines)
                findings_blocks.append(block)

        findings_text = "\n\n".join(findings_blocks) or f"No findings passed the confidence threshold (>={config.confidence_threshold})."
        sources_text = "\n".join(f"- {url}" for url in all_sources) or f"- No source URLs available from confidence>={config.confidence_threshold} findings"

        prompt_text = WRITER_PROMPT.format(
            topic=state["topic"],
            findings=findings_text,
            sources=sources_text,
        )

        report_parts = []
        for chunk in llm.stream(prompt_text):
            token = getattr(chunk, "content", "") or ""
            if token:
                report_parts.append(token)
                if on_token is not None:
                    on_token(token)

        state["report"] = "".join(report_parts).strip()
        state["next_agent"] = "end"
        if on_agent_status is not None:
            on_agent_status("writer", "done", "Report complete")
        return state

    return writer_node


def writer_node(state: AgentState) -> AgentState:
    return create_writer_node(PipelineConfig())(state)
