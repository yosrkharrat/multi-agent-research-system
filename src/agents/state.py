from typing import Annotated, TypedDict

from langgraph.graph.message import add_messages


class AgentState(TypedDict):
    messages: Annotated[list, add_messages]
    topic: str
    plan: list[str]
    findings: list[str]
    critique: str
    report: str
    next_agent: str
    iteration: int
