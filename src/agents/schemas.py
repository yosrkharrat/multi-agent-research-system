"""
STEP 4a — Structured outputs (Pydantic models for each agent)
=============================================================
Replace the regex-based parsing in your critic and planner with these
Pydantic schemas.  LangChain's  .with_structured_output()  will retry
automatically on malformed JSON.

HOW TO USE IN critic.py
------------------------
    from agents.schemas import CriticOutput
    from langchain_ollama import ChatOllama

    llm = ChatOllama(model="mistral", temperature=0.2)
    structured_llm = llm.with_structured_output(CriticOutput)
    output: CriticOutput = structured_llm.invoke(prompt)

    verdict   = output.verdict        # "APPROVED" | "NEEDS_WORK"
    reason    = output.reason         # one-sentence explanation
    scores    = output.scores         # dict[str, int]
    iteration = output.confidence     # 1–5 self-assessed certainty

HOW TO USE IN planner.py
------------------------
    from agents.schemas import PlannerOutput
    structured_llm = llm.with_structured_output(PlannerOutput)
    output: PlannerOutput = structured_llm.invoke(prompt)
    questions = output.questions      # list[str], already validated

HOW TO USE IN researcher.py
---------------------------
    from agents.schemas import Finding
    # Build a Finding after each ReAct loop iteration:
    finding = Finding(
        question=question,
        summary=agent_response,
        sources=extract_urls(agent_response),
        confidence=4,
    )
    # Store as JSON string in state["findings"]
    state["findings"].append(finding.model_dump_json())
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator


# ── Planner ───────────────────────────────────────────────────────────────────

class PlannerOutput(BaseModel):
    """Structured output for the Planner agent."""

    questions: list[str] = Field(
        ...,
        min_length=2,
        max_length=5,
        description="2–5 focused research questions derived from the topic.",
    )

    @field_validator("questions")
    @classmethod
    def strip_numbering(cls, v: list[str]) -> list[str]:
        """Remove leading '1. ' / '- ' prefixes the LLM might add."""
        import re
        cleaned = []
        for q in v:
            q = re.sub(r"^\s*[\d]+[\.\)]\s*", "", q).strip()
            q = re.sub(r"^\s*[-•]\s*", "", q).strip()
            if q:
                cleaned.append(q)
        return cleaned


# ── Researcher ────────────────────────────────────────────────────────────────

class Finding(BaseModel):
    """One unit of research produced by the Researcher agent."""

    question: str = Field(..., description="The research question this answers.")
    summary: str = Field(..., description="Key facts found, 2–6 sentences.")
    sources: list[str] = Field(
        default_factory=list,
        description="URLs cited in the summary.",
    )
    confidence: int = Field(
        default=3,
        ge=1,
        le=5,
        description="Self-assessed confidence in this finding (1=low, 5=high).",
    )

    @field_validator("sources")
    @classmethod
    def deduplicate(cls, v: list[str]) -> list[str]:
        seen: set[str] = set()
        return [u for u in v if not (u in seen or seen.add(u))]  # type: ignore[func-returns-value]

    def to_text(self) -> str:
        """Human-readable form for inclusion in LLM context."""
        src_block = "\n".join(f"  - {s}" for s in self.sources) if self.sources else "  (no sources)"
        return (
            f"Q: {self.question}\n"
            f"A: {self.summary}\n"
            f"Sources:\n{src_block}\n"
            f"Confidence: {self.confidence}/5"
        )


# ── Critic ────────────────────────────────────────────────────────────────────

class CriticOutput(BaseModel):
    """Structured output for the Critic agent."""

    verdict: Literal["APPROVED", "NEEDS_WORK"] = Field(
        ...,
        description="APPROVED if findings are sufficient, NEEDS_WORK if not.",
    )
    reason: str = Field(
        ...,
        max_length=300,
        description="One-sentence explanation of the verdict.",
    )
    scores: dict[str, int] = Field(
        default_factory=lambda: {
            "coverage": 3,
            "specificity": 3,
            "source_quality": 3,
        },
        description="Rubric scores 1–5 for coverage, specificity, source_quality.",
    )
    confidence: int = Field(
        default=3,
        ge=1,
        le=5,
        description="How confident the critic is in this verdict (1=unsure, 5=certain).",
    )

    @field_validator("scores")
    @classmethod
    def clamp_scores(cls, v: dict[str, int]) -> dict[str, int]:
        return {k: max(1, min(5, val)) for k, val in v.items()}

    def average_score(self) -> float:
        if not self.scores:
            return 3.0
        return round(sum(self.scores.values()) / len(self.scores), 2)

    def should_approve(self, threshold: int = 3) -> bool:
        """Returns True if verdict is APPROVED and avg score >= threshold."""
        return self.verdict == "APPROVED" and self.average_score() >= threshold


# ── Writer ────────────────────────────────────────────────────────────────────

class WriterOutput(BaseModel):
    """Structured output for the Writer agent (optional — writer mostly outputs raw markdown)."""

    report: str = Field(..., description="Full markdown research report.")
    title: str = Field(..., description="Report title, no markdown prefix.")
    word_count: int = Field(default=0, description="Approximate word count.")

    @field_validator("word_count", mode="before")
    @classmethod
    def compute_word_count(cls, v: int, info) -> int:
        if v == 0 and "report" in info.data:
            return len(info.data["report"].split())
        return v
