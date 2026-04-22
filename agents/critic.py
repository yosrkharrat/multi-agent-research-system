"""Compatibility exports for legacy `agents.critic` imports."""

from src.agents.critic import (
    CRITIC_PROMPT,
    SCORE_PATTERN,
    VERDICT_PATTERN,
    _parse_scores,
    create_critic_node,
    critic_node,
)

__all__ = [
    "CRITIC_PROMPT",
    "SCORE_PATTERN",
    "VERDICT_PATTERN",
    "_parse_scores",
    "create_critic_node",
    "critic_node",
]
