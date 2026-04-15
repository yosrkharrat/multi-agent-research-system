"""Phase 3 test: full multi-agent orchestration with Supervisor router."""

from agents.graph import build_graph


def main() -> None:
    """Build orchestration graph and run full research workflow."""

    print("Building graph...")
    graph = build_graph()

    print("\nRunning research on: 'What are the key breakthroughs in quantum computing?'")
    print("=" * 80)

    result = graph.invoke(
        {
            "messages": [],
            "topic": "What are the key breakthroughs in quantum computing?",
            "plan": [],
            "findings": [],
            "critique": "",
            "report": "",
            "next_agent": "",
            "iteration": 0,
        }
    )

    print("\n" + "=" * 80)
    print("=== FINAL REPORT ===")
    print(result["report"])


if __name__ == "__main__":
    main()
