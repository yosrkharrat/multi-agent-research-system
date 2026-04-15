"""Researcher agent: uses ReAct pattern to research planned questions."""

import re

from langchain_ollama import ChatOllama
from langgraph.prebuilt import create_react_agent

from .tools import tools
from .state import AgentState

llm = ChatOllama(model="mistral", temperature=0.1, base_url="http://localhost:11434")
react_agent = create_react_agent(llm, tools)

URL_PATTERN = re.compile(r"https?://[^\s\]\)\}\>,\"']+")


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


def researcher_node(state: AgentState) -> AgentState:
    """Research questions from the plan, or fall back to raw topic."""

    queries = state.get("plan") or [state["topic"]]
    new_findings = []

    for question in queries:
        print(f"\n[Researcher] Researching: {question}")
        prompt = f"Research this question and return a detailed factual summary:\n\n{question}"
        result = react_agent.invoke(
            {
                "messages": [{"role": "user", "content": prompt}],
            }
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
                new_findings.append(
                    {
                        "question": question,
                        "content": str(findings),
                        "sources": extract_urls(raw_text),
                    }
                )

    state["findings"].extend(new_findings)
    state["next_agent"] = "critic"
    return state
