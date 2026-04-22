"""Researcher agent: uses ReAct pattern to research planned questions."""

import json
import re
from urllib.parse import urlparse

from langchain_ollama import ChatOllama
from langgraph.prebuilt import create_react_agent

from .tools import tools
from .state import AgentState
from config import PipelineConfig

_llm = None
_react_agent = None
_active_config = None


def _get_llm(config: PipelineConfig):
    global _llm, _active_config
    if _llm is None or _active_config != config.model_dump():
        _active_config = config.model_dump()
        _llm = ChatOllama(
            model=config.researcher_model,
            temperature=0.1,
            base_url=config.ollama_base_url,
            num_predict=config.researcher_num_predict,
        )
    return _llm


def _get_react_agent(config: PipelineConfig):
    global _react_agent, _active_config
    if _react_agent is None or _active_config != config.model_dump():
        _active_config = config.model_dump()
        _react_agent = create_react_agent(_get_llm(config), tools)
    return _react_agent

URL_PATTERN = re.compile(r"https?://[^\s\]\)\}\>,\"']+")


def _is_http_url(url: str) -> bool:
    return url.startswith("http://") or url.startswith("https://")


def extract_urls(text: str) -> list[str]:
    """Extract and de-duplicate URLs while preserving first-seen order."""

    urls = []
    seen = set()
    for match in URL_PATTERN.findall(text):
        cleaned = match.rstrip(".,;:")
        if cleaned and cleaned not in seen:
            seen.add(cleaned)
            urls.append(cleaned)
    return urls


def _title_from_url(url: str) -> str:
    parsed = urlparse(url)
    host = parsed.netloc.replace("www.", "")
    path = parsed.path.strip("/")
    if path:
        first_segment = path.split("/")[0]
        return f"{host}/{first_segment}" if host else first_segment
    return host or url


def _extract_json_block(text: str) -> str:
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        return text[start : end + 1]
    return text


def _normalize_sources(raw_text: str, extracted_sources: object) -> list[dict[str, str]]:
    normalized: list[dict[str, str]] = []
    seen = set()

    if isinstance(extracted_sources, list):
        for item in extracted_sources:
            if isinstance(item, dict):
                url = str(item.get("url", "")).strip()
                title = str(item.get("title", "")).strip() or _title_from_url(url)
            else:
                url = str(item).strip()
                title = _title_from_url(url)
            if url and _is_http_url(url) and url not in seen:
                seen.add(url)
                normalized.append({"url": url, "title": title})

    if not normalized:
        for url in extract_urls(raw_text):
            if url not in seen:
                seen.add(url)
                normalized.append({"url": url, "title": _title_from_url(url)})

    return normalized


def _normalize_key_facts(value: object, fallback_summary: str) -> list[str]:
    if isinstance(value, list):
        facts = [str(item).strip() for item in value if str(item).strip()]
        if facts:
            return facts
    if fallback_summary.strip():
        return [fallback_summary.strip()]
    return []


def create_researcher_node(config: PipelineConfig, on_agent_status=None):
    def researcher_node(state: AgentState) -> AgentState:
        """Research questions from the plan, or fall back to raw topic."""

        queries = (state.get("plan") or [state["topic"]])[: config.researcher_max_questions]
        new_findings = []

        if on_agent_status is not None:
            on_agent_status(
                "researcher",
                "running",
                f"Researching {len(queries)} questions...",
            )

        for question in queries:
            print(f"\n[Researcher] Researching: {question}")
            prompt = f"Research this question and return a detailed factual summary:\n\n{question}"
            result = _get_react_agent(config).invoke(
                {
                    "messages": [{"role": "user", "content": prompt}],
                },
                config={"recursion_limit": config.researcher_max_reasoning_steps},
            )

            if isinstance(result, dict) and "messages" in result:
                messages = result["messages"]
                if messages:
                    last_message = messages[-1]
                    if hasattr(last_message, "content"):
                        findings = last_message.content
                    elif isinstance(last_message, dict) and "content" in last_message:
                        findings = last_message["content"]
                    else:
                        findings = str(last_message)

                    raw_parts = []
                    for msg in messages:
                        if hasattr(msg, "content"):
                            raw_parts.append(str(msg.content))
                        elif isinstance(msg, dict) and "content" in msg:
                            raw_parts.append(str(msg["content"]))
                        else:
                            raw_parts.append(str(msg))

                    raw_text = "\n".join(raw_parts)
                    trimmed_notes = raw_text[: config.researcher_notes_char_limit]
                    extraction_prompt = f"""Extract a structured finding from the research notes below.

Return JSON only with this shape:
{{
    "summary": "one concise factual paragraph",
    "key_facts": ["fact 1", "fact 2"],
    "sources": [
        {{"url": "https://...", "title": "short title"}}
    ]
}}

Rules:
- summary must be grounded in the notes
- key_facts must be short, specific, and explicitly stated facts
- sources must use only URLs appearing in the notes
- if a title is not obvious, infer a short descriptive title

Question: {question}
Notes:
{trimmed_notes}
"""

                    structured_result = _get_llm(config).invoke(extraction_prompt).content
                    structured_payload: dict[str, object] = {}
                    try:
                        structured_payload = json.loads(_extract_json_block(structured_result))
                    except json.JSONDecodeError:
                        structured_payload = {}

                    summary = str(structured_payload.get("summary", "")).strip() or str(findings).strip()
                    key_facts = _normalize_key_facts(structured_payload.get("key_facts"), summary)
                    sources = _normalize_sources(raw_text, structured_payload.get("sources"))

                    new_findings.append(
                        {
                            "question": question,
                            "summary": summary,
                            "sources": sources,
                            "key_facts": key_facts,
                        }
                    )

        state["findings"].extend(new_findings)
        state["next_agent"] = "critic"
        if on_agent_status is not None:
            on_agent_status(
                "researcher",
                "done",
                f"Completed research for {len(new_findings)} findings",
                new_findings,
            )
        return state

    return researcher_node


def researcher_node(state: AgentState) -> AgentState:
    return create_researcher_node(PipelineConfig())(state)
