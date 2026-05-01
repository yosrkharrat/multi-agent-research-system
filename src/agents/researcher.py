"""Researcher agent: uses ReAct pattern to research planned questions."""

from __future__ import annotations

import json
import re
from urllib.parse import urlparse

from langchain_core.messages import AIMessage, ToolMessage
from langchain_ollama import ChatOllama
from langgraph.prebuilt import create_react_agent

from .tools import tools, fetch_page
from .state import AgentState
from config import PipelineConfig

_llm = None
_react_agent = None
_active_config = None

# ── URL helpers ────────────────────────────────────────────────────────────────

URL_PATTERN = re.compile(r"https?://[^\s\]\)\}\>,\"']+")

# Domains that are never real sources — always filter these out
_JUNK_DOMAINS = {
    "duckduckgo.com",
    "google.com",
    "bing.com",
    "search.yahoo.com",
    "localhost",
}


def _is_real_url(url: str) -> bool:
    """True only if the URL is a real page, not a search engine query."""
    if not url.startswith("http"):
        return False
    try:
        host = urlparse(url).netloc.lower().replace("www.", "")
    except Exception:
        return False
    return host not in _JUNK_DOMAINS and bool(host)


def extract_urls(text: str) -> list[str]:
    """Extract de-duplicated real page URLs (search engine URLs excluded)."""
    seen: set[str] = set()
    result = []
    for match in URL_PATTERN.findall(text):
        url = match.rstrip(".,;:()")
        if url and url not in seen and _is_real_url(url):
            seen.add(url)
            result.append(url)
    return result


def _title_from_url(url: str) -> str:
    parsed = urlparse(url)
    host = parsed.netloc.replace("www.", "")
    path = parsed.path.strip("/")
    if path:
        first_segment = path.split("/")[0]
        return f"{host}/{first_segment}" if host else first_segment
    return host or url


# ── LLM / agent singletons ─────────────────────────────────────────────────────

def _get_llm(config: PipelineConfig) -> ChatOllama:
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
    global _react_agent
    if _react_agent is None:
        _react_agent = create_react_agent(_get_llm(config), tools)
    return _react_agent


# ── Message parsing ────────────────────────────────────────────────────────────

def _parse_react_messages(messages: list) -> tuple[str, list[str]]:
    """
    Walk the ReAct message list and return:
      (final_answer: str, real_urls: list[str])

    Rules:
    - Final answer = content of the last AIMessage that is NOT a tool call
    - real_urls    = URLs collected only from ToolMessage content (actual
                     search/fetch results), never from AIMessage tool-call JSON
    """
    final_answer = ""
    real_urls: list[str] = []
    seen_urls: set[str] = set()

    for msg in messages:
        # ── ToolMessage: this is actual search/fetch output ──────────────────
        if isinstance(msg, ToolMessage):
            content = str(msg.content)
            for url in extract_urls(content):
                if url not in seen_urls:
                    seen_urls.add(url)
                    real_urls.append(url)

        # ── AIMessage: only capture the final text answer, skip tool calls ───
        elif isinstance(msg, AIMessage):
            # An AIMessage with tool_calls is the agent deciding to call a tool
            # — its .content is empty or raw JSON; skip it entirely.
            has_tool_calls = bool(getattr(msg, "tool_calls", None))
            if not has_tool_calls and msg.content:
                content = str(msg.content).strip()
                # Skip leftover tool-call JSON that sometimes leaks into content
                if not content.startswith("[{") and not content.startswith("{"):
                    final_answer = content

    return final_answer, real_urls


# ── Source normalisation ───────────────────────────────────────────────────────

def _build_sources(
    real_urls: list[str],
    llm_sources: object,
) -> list[dict[str, str]]:
    """
    Build the final sources list.

    Priority:
    1. URLs the LLM explicitly listed in its JSON response, IF they pass
       _is_real_url (prevents the LLM from hallucinating DDG query URLs)
    2. Real URLs captured from ToolMessage content as fallback
    """
    seen: set[str] = set()
    sources: list[dict[str, str]] = []

    # 1. LLM-listed sources (validated)
    if isinstance(llm_sources, list):
        for item in llm_sources:
            url = str(item.get("url", "") if isinstance(item, dict) else item).strip()
            title = str(item.get("title", "") if isinstance(item, dict) else "").strip()
            if url and _is_real_url(url) and url not in seen:
                seen.add(url)
                sources.append({"url": url, "title": title or _title_from_url(url)})

    # 2. Fallback: URLs from tool outputs
    for url in real_urls:
        if url not in seen:
            seen.add(url)
            sources.append({"url": url, "title": _title_from_url(url)})

    return sources


def _extract_json_block(text: str) -> str:
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        return text[start: end + 1]
    return text


# ── Node factory ───────────────────────────────────────────────────────────────

def create_researcher_node(config: PipelineConfig, on_agent_status=None):

    def researcher_node(state: AgentState) -> AgentState:
        queries = (state.get("plan") or [state["topic"]])[: config.researcher_max_questions]
        new_findings: list[dict] = []

        if on_agent_status:
            on_agent_status("researcher", "running", f"Researching {len(queries)} questions...")

        for question in queries:
            print(f"\n[Researcher] Researching: {question}")

            # ── 1. Run the ReAct agent ─────────────────────────────────────
            prompt = (
                "You are a research assistant. Use the search tool to find "
                "information, then fetch the most relevant result page to get "
                "full details. Return a factual summary with specific facts.\n\n"
                f"Question: {question}"
            )
            try:
                result = _get_react_agent(config).invoke(
                    {"messages": [{"role": "user", "content": prompt}]},
                    config={"recursion_limit": config.researcher_max_reasoning_steps},
                )
            except Exception as exc:
                print(f"  [Researcher] Agent error: {exc}")
                new_findings.append({
                    "question": question,
                    "summary": f"Research failed: {exc}",
                    "sources": [],
                    "key_facts": [],
                })
                continue

            messages = result.get("messages", []) if isinstance(result, dict) else []

            # ── 2. Parse messages — extract answer + real URLs ─────────────
            final_answer, real_urls = _parse_react_messages(messages)

            if not final_answer:
                final_answer = "No answer returned by agent."

            # ── 3. Fetch the top real URL to get actual page content ───────
            page_content = ""
            if real_urls:
                top_url = real_urls[0]
                print(f"  [Researcher] Fetching: {top_url}")
                try:
                    page_content = fetch_page(top_url)
                    if page_content.startswith("Could not fetch"):
                        print(f"  [Researcher] Fetch failed: {page_content}")
                        page_content = ""
                except Exception as exc:
                    print(f"  [Researcher] fetch_page error: {exc}")
                    page_content = ""

            # ── 4. Extract structured finding using real page content ───────
            grounding = page_content[:2000] if page_content else final_answer[:2000]
            notes_for_extraction = (
                f"Agent summary:\n{final_answer}\n\n"
                f"Page content:\n{grounding}"
            )[: config.researcher_notes_char_limit]

            extraction_prompt = f"""Extract a structured finding from the research notes below.

Return JSON only — no explanation, no markdown fences — with exactly this shape:
{{
    "summary": "one concise factual paragraph, 3-5 sentences, grounded in the notes",
    "key_facts": ["specific fact 1", "specific fact 2", "specific fact 3"],
    "sources": [
        {{"url": "https://example.com/real-page", "title": "short title"}}
    ]
}}

IMPORTANT:
- summary must contain ONLY facts that appear in the notes below
- sources must ONLY list URLs that explicitly appear in the notes below
- do NOT invent URLs or use search engine query URLs
- if no real URL appears in the notes, return "sources": []

Question: {question}

Notes:
{notes_for_extraction}
"""
            raw_structured = _get_llm(config).invoke(extraction_prompt).content
            payload: dict = {}
            try:
                payload = json.loads(_extract_json_block(raw_structured))
            except json.JSONDecodeError:
                pass

            summary = str(payload.get("summary", "")).strip() or final_answer.strip()

            key_facts_raw = payload.get("key_facts", [])
            key_facts = (
                [str(f).strip() for f in key_facts_raw if str(f).strip()]
                if isinstance(key_facts_raw, list)
                else [summary]
            )

            sources = _build_sources(real_urls, payload.get("sources", []))

            # ── 5. If we fetched a page and no LLM source listed it, add it ─
            if page_content and real_urls:
                existing_urls = {s["url"] for s in sources}
                if real_urls[0] not in existing_urls:
                    sources.insert(0, {
                        "url": real_urls[0],
                        "title": _title_from_url(real_urls[0]),
                    })

            new_findings.append({
                "question": question,
                "summary": summary,
                "sources": sources,
                "key_facts": key_facts,
            })

            print(f"  [Researcher] Done. Sources: {[s['url'] for s in sources]}")

        state["findings"].extend(new_findings)
        state["next_agent"] = "critic"

        if on_agent_status:
            on_agent_status(
                "researcher", "done",
                f"Completed {len(new_findings)} findings",
                new_findings,
            )
        return state

    return researcher_node


def researcher_node(state: AgentState) -> AgentState:
    return create_researcher_node(PipelineConfig())(state)