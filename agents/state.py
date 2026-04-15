from typing import Annotated, NotRequired, TypedDict

from langgraph.graph.message import add_messages


class AgentState(TypedDict):
    messages: Annotated[list, add_messages]
    topic: str
    plan: list[str]
    findings: list[dict[str, object]]
    critique: str
    report: str
    next_agent: str
    iteration: int
    _event_queue: NotRequired[object]
