"""Local LLM utilities for the multi-agent research system."""

from .ollama_client import OllamaClient, generate_text

__all__ = ["OllamaClient", "generate_text"]
