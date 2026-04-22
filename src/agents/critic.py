"""Critic agent: evaluates research findings and decides if they are sufficient."""

import re

from langchain_ollama import ChatOllama

from config import PipelineConfig

from .state import AgentState

CRITIC_PROMPT = """You are a research critic. Review the findings below and decide if 
they are sufficient to write a comprehensive report on the topic.

Topic: {topic}
Research plan: {plan}

Findings:
{findings}

Also flag any of these weaknesses:
- Claims without a specific example, date, or figure (e.g. "researchers are developing" with no name)
- Stats cited without a source
- Sentences that could apply to any topic (too generic)

Reject if:
- Fewer than 3 concrete facts per question
- No source URLs present
- Any finding contains only vague generalizations

Before approving, rate every finding with an integer confidence score from 1-5.

Respond using exactly this format:
CONFIDENCE_SCORES:
1: <1-5>
2: <1-5>
...
VERDICT: APPROVED
or
VERDICT: NEEDS_WORK: <one sentence describing what is missing>

Be strict but fair. Only approve if the core questions in the plan are addressed and the writing is specific, grounded, and sourced."""

SCORE_PATTERN = re.compile(r"^\s*[-*]?\s*(\d+)\s*[:=-]\s*([1-5])\b", re.MULTILINE)
VERDICT_PATTERN = re.compile(r"VERDICT\s*:\s*(.+)", re.IGNORECASE)


def _parse_scores(text: str, count: int) -> list[int]:
    scores = [2] * count
    for match in SCORE_PATTERN.finditer(text):
        idx = int(match.group(1)) - 1
        score = int(match.group(2))
        if 0 <= idx < count:
            scores[idx] = score
    return scores


def create_critic_node(config: PipelineConfig, on_agent_status=None):
    llm = ChatOllama(
        model=config.critic_model,
        temperature=0.2,
        base_url=config.ollama_base_url,
        num_predict=config.critic_num_predict,
    )

    def critic_node(state: AgentState) -> AgentState:
        """Evaluate findings and decide if research is sufficient or needs more work."""

        if on_agent_status is not None:
            on_agent_status("critic", "running", "Evaluating research quality...")

        findings_lines = []
        for idx, item in enumerate(state["findings"], start=1):
            if isinstance(item, dict):
                question = str(item.get("question", ""))
                summary = str(item.get("summary", item.get("content", "")))
                key_facts = item.get("key_facts", [])
                sources = item.get("sources", [])
                source_text = ", ".join(
                    str(src.get("url", src)) if isinstance(src, dict) else str(src)
                    for src in sources
                ) if isinstance(sources, list) else ""
                facts_text = "; ".join(str(fact) for fact in key_facts) if isinstance(key_facts, list) else ""
                findings_lines.append(
                    f"{idx}. Question: {question}\nSummary: {summary}\nKey facts: {facts_text or 'None'}\nSources: {source_text or 'None'}"
                )
            else:
                findings_lines.append(f"{idx}. Summary: {str(item)}\nSources: None")

        findings_text = "\n\n".join(findings_lines)
        plan_text = "\n".join(state["plan"])

        response = llm.invoke(
            CRITIC_PROMPT.format(
                topic=state["topic"],
                plan=plan_text,
                findings=findings_text,
            )
        )

        critique_raw = response.content.strip()
        verdict_match = VERDICT_PATTERN.search(critique_raw)
        critique = verdict_match.group(1).strip() if verdict_match else critique_raw

        scores = _parse_scores(critique_raw, len(state["findings"]))
        for i, item in enumerate(state["findings"]):
            score = scores[i] if i < len(scores) else config.confidence_threshold - 1
            if isinstance(item, dict):
                item["confidence"] = score
            else:
                state["findings"][i] = {
                    "question": "",
                    "summary": str(item),
                    "sources": [],
                    "key_facts": [],
                    "confidence": score,
                }

        state["critique"] = critique
        state["iteration"] = state.get("iteration", 0) + 1

        if critique.startswith("APPROVED"):
            state["next_agent"] = "writer"
            print(f"\n[Critic] Approved after {state['iteration']} iteration(s)")
        else:
            state["next_agent"] = "researcher"
            print(f"\n[Critic] Sending back: {critique}")

        if on_agent_status is not None:
            on_agent_status(
                "critic",
                "done",
                critique,
                {"approved": critique.startswith("APPROVED"), "scores": scores},
            )

        return state

    return critic_node


def critic_node(state: AgentState) -> AgentState:
    return create_critic_node(PipelineConfig())(state)
