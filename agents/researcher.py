"""Researcher agent: uses ReAct pattern to research planned questions."""

from langchain_ollama import ChatOllama
from langgraph.prebuilt import create_react_agent

from .tools import tools
from .state import AgentState

# Initialize the LLM with ollama backend; mistral is faster but llama3 is more capable
llm = ChatOllama(model="mistral", temperature=0.1, base_url="http://localhost:11434")

# Create the ReAct agent using LangGraph's built-in factory
react_agent = create_react_agent(llm, tools)


def researcher_node(state: AgentState) -> AgentState:
    """Research questions from the plan, or fall back to raw topic."""

    # Use plan questions if available, otherwise fall back to raw topic
    queries = state.get("plan") or [state["topic"]]
    new_findings = []

    for question in queries:
        print(f"\n[Researcher] Researching: {question}")
        prompt = f"Research this question and return a detailed factual summary:\n\n{question}"
        
        # Invoke the pre-built ReAct agent
        result = react_agent.invoke(
            {
                "messages": [{"role": "user", "content": prompt}],
            }
        )
        
        # Extract the final response from messages
        if isinstance(result, dict) and "messages" in result:
            messages = result["messages"]
            if messages:
                last_message = messages[-1]
                # Handle different message types
                if hasattr(last_message, "content"):
                    findings = last_message.content
                elif isinstance(last_message, dict) and "content" in last_message:
                    findings = last_message["content"]
                else:
                    findings = str(last_message)
                new_findings.append(findings)

    state["findings"].extend(new_findings)
    state["next_agent"] = "critic"
    return state

