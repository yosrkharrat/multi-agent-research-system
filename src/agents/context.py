"""
STEP 1 — Context window management
===================================
Counts tokens before every LLM call. Trims + summarises old findings
when the accumulated context approaches the model's limit.

Usage inside any agent node:
    from agents.context import ContextManager
    cm = ContextManager(model_name="mistral", budget=4096)
    state = cm.trim_findings_if_needed(state, llm)
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from langchain_ollama import ChatOllama
    from agents.state import AgentState


# ── Token counting ─────────────────────────────────────────────────────────────
# Ollama does not expose a tokenize endpoint we can rely on locally, so we use
# a character-based heuristic that is accurate to ~5% for English text.
# Rule of thumb: 1 token ≈ 4 characters (GPT/Llama/Mistral all close to this).
CHARS_PER_TOKEN: int = 4


def estimate_tokens(text: str) -> int:
    """Rough token estimate: chars / 4. Fast, no external call needed."""
    return max(1, len(text) // CHARS_PER_TOKEN)


def estimate_state_tokens(state: "AgentState") -> int:
    """Sum token estimates across all text fields that reach the LLM."""
    parts = [
        state.get("topic", ""),
        " ".join(state.get("plan", [])),
        " ".join(state.get("findings", [])),
        state.get("critique", ""),
        state.get("report", ""),
    ]
    return estimate_tokens(" ".join(parts))


# ── ContextManager ─────────────────────────────────────────────────────────────

class ContextManager:
    """
    Keeps the accumulated state within a token budget.

    Parameters
    ----------
    model_name : str
        Ollama model slug — used only for logging.
    budget : int
        Max tokens to allow before trimming. Safe defaults per model:
          mistral   → 6 000   (8k context, leave 2k for generation)
          llama3    → 6 000   (8k context, leave 2k for generation)
    warn_fraction : float
        Log a warning when usage exceeds this fraction of budget (default 0.8).
    """

    def __init__(
        self,
        model_name: str = "mistral",
        budget: int = 6_000,
        warn_fraction: float = 0.8,
    ) -> None:
        self.model_name = model_name
        self.budget = budget
        self.warn_fraction = warn_fraction

    # ── public ────────────────────────────────────────────────────────────────

    def usage(self, state: "AgentState") -> dict:
        """Return a dict with token count and percentage of budget used."""
        tokens = estimate_state_tokens(state)
        return {
            "tokens": tokens,
            "budget": self.budget,
            "pct": round(tokens / self.budget * 100, 1),
            "over": tokens > self.budget,
        }

    def log_usage(self, state: "AgentState", node: str = "") -> None:
        u = self.usage(state)
        tag = f"[{node}] " if node else ""
        if u["over"]:
            print(f"  {tag}⚠ Context OVER budget: {u['tokens']:,} / {u['budget']:,} tokens")
        elif u["pct"] >= self.warn_fraction * 100:
            print(f"  {tag}⚠ Context at {u['pct']}% of budget ({u['tokens']:,} tokens)")
        else:
            print(f"  {tag}Context: {u['tokens']:,} / {u['budget']:,} tokens ({u['pct']}%)")

    def trim_findings_if_needed(
        self,
        state: "AgentState",
        llm: "ChatOllama | None" = None,
    ) -> "AgentState":
        """
        If over budget, either summarise the oldest half of findings (if an
        LLM is provided) or hard-drop them (fallback, no LLM needed).

        Returns a new state dict (does not mutate in place).
        """
        if not self.usage(state)["over"]:
            return state

        findings: list[str] = list(state.get("findings", []))
        if len(findings) <= 1:
            return state  # nothing safe to trim

        half = max(1, len(findings) // 2)
        old, keep = findings[:half], findings[half:]

        if llm is not None:
            summary = self._summarise(old, llm)
            print(f"  [ContextManager] Summarised {half} findings → 1 summary block")
            new_findings = [f"[Summary of earlier research]\n{summary}"] + keep
        else:
            # Hard trim: just drop the oldest findings
            print(f"  [ContextManager] Hard-trimmed {half} oldest findings (no LLM available)")
            new_findings = keep

        return {**state, "findings": new_findings}

    # ── private ───────────────────────────────────────────────────────────────

    def _summarise(self, findings: list[str], llm: "ChatOllama") -> str:
        """Ask the LLM to compress a list of findings into a short paragraph."""
        block = "\n\n---\n\n".join(findings)
        prompt = (
            "You are a research assistant. Compress the following research notes "
            "into a single concise paragraph that preserves all key facts, names, "
            "dates, and URLs. Do not add new information.\n\n"
            f"{block}\n\nSummary:"
        )
        try:
            response = llm.invoke(prompt)
            return response.content.strip()
        except Exception as exc:  # noqa: BLE001
            print(f"  [ContextManager] Summarisation failed ({exc}), falling back to truncation")
            # Return the first 800 chars of the block as a last resort
            return block[:800] + "…"
