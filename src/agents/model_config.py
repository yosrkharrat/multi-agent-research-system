"""
STEP 4b — Per-role inference configuration
==========================================
Each agent role needs different generation parameters.
This replaces the single flat config in PipelineConfig with a typed
per-role factory.

  Planner   → temp 0.1, low top_p  (deterministic, structured plans)
  Researcher → temp 0.2, higher top_p (some creativity in tool use)
  Critic    → temp 0.1, very tight   (consistent evaluation)
  Writer    → temp 0.45, high top_p  (varied, readable prose)

USAGE in any agent file
------------------------
    from agents.model_config import build_llm
    from config import PipelineConfig

    cfg = PipelineConfig()
    llm = build_llm("planner", cfg)       # returns ChatOllama, pre-configured
    llm = build_llm("writer", cfg)
"""

from __future__ import annotations

from dataclasses import dataclass

from langchain_ollama import ChatOllama

from config import PipelineConfig


@dataclass(frozen=True)
class RoleConfig:
    temperature: float
    top_p: float
    num_predict: int
    repeat_penalty: float = 1.1   # slight repetition penalty for all roles


# ── Per-role defaults ─────────────────────────────────────────────────────────

ROLE_DEFAULTS: dict[str, RoleConfig] = {
    "planner": RoleConfig(
        temperature=0.1,
        top_p=0.85,
        num_predict=220,   # short, structured list output
    ),
    "researcher": RoleConfig(
        temperature=0.2,
        top_p=0.90,
        num_predict=260,   # ReAct loop needs space for tool calls
    ),
    "critic": RoleConfig(
        temperature=0.1,   # deterministic verdicts
        top_p=0.85,
        num_predict=220,
    ),
    "writer": RoleConfig(
        temperature=0.45,  # readable, varied prose
        top_p=0.95,
        num_predict=900,
    ),
}


def build_llm(role: str, cfg: PipelineConfig) -> ChatOllama:
    """
    Return a ChatOllama instance tuned for the given *role*.

    Falls back to "researcher" defaults for unknown roles.

    Parameters
    ----------
    role : str
        One of  "planner" | "researcher" | "critic" | "writer"
    cfg : PipelineConfig
        Provides model names and Ollama base URL.
    """
    role_cfg = ROLE_DEFAULTS.get(role, ROLE_DEFAULTS["researcher"])

    model_map = {
        "planner": cfg.planner_model,
        "researcher": cfg.researcher_model,
        "critic": cfg.critic_model,
        "writer": cfg.writer_model,
    }
    model_name = model_map.get(role, cfg.researcher_model)

    # num_predict from PipelineConfig overrides the role default if explicitly set
    num_predict_map = {
        "planner": cfg.planner_num_predict,
        "researcher": cfg.researcher_num_predict,
        "critic": cfg.critic_num_predict,
        "writer": cfg.writer_num_predict,
    }
    num_predict = num_predict_map.get(role, role_cfg.num_predict)

    return ChatOllama(
        model=model_name,
        base_url=cfg.ollama_base_url,
        temperature=role_cfg.temperature,
        top_p=role_cfg.top_p,
        num_predict=num_predict,
        repeat_penalty=role_cfg.repeat_penalty,
    )
