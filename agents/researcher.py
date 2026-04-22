"""Compatibility exports for legacy `agents.researcher` imports."""

from src.agents.researcher import (
    URL_PATTERN,
    create_researcher_node,
    extract_urls,
    researcher_node,
)

__all__ = ["URL_PATTERN", "create_researcher_node", "extract_urls", "researcher_node"]
