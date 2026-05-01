"""Tool definitions for agents: web search and knowledge retrieval."""

from langchain_community.tools import DuckDuckGoSearchRun, WikipediaQueryRun
from langchain_community.utilities import WikipediaAPIWrapper
from langchain.tools import tool
import httpx
import re

search_tool = DuckDuckGoSearchRun()

wikipedia_tool = WikipediaQueryRun(
    api_wrapper=WikipediaAPIWrapper(top_k_results=2, doc_content_chars_max=2000)
)


@tool
def fetch_page(url: str) -> str:
    """Fetch the text content of a web page given its URL.

    Returns a plain-text excerpt (HTML crudely stripped), capped at 3000 chars.
    """
    try:
        r = httpx.get(url, timeout=10, follow_redirects=True)
        # crude HTML tag stripping
        text = re.sub(r"<[^>]+>", " ", r.text)
        # collapse whitespace
        text = " ".join(text.split())
        return text[:3000]
    except Exception as exc:  # keep errors stable for agent
        return f"Could not fetch page: {exc}"


tools = [search_tool, wikipedia_tool, fetch_page]

# Export fetch_page for direct invocation from researcher
__all__ = ["search_tool", "wikipedia_tool", "fetch_page", "tools"]
