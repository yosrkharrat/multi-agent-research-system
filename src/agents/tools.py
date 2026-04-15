"""Tool definitions for agents: web search and knowledge retrieval."""

from langchain_community.tools import DuckDuckGoSearchRun, WikipediaQueryRun
from langchain_community.utilities import WikipediaAPIWrapper

search_tool = DuckDuckGoSearchRun()

wikipedia_tool = WikipediaQueryRun(
    api_wrapper=WikipediaAPIWrapper(top_k_results=2, doc_content_chars_max=2000)
)

tools = [search_tool, wikipedia_tool]
