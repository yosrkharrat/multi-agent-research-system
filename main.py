"""Phase 3 test: full multi-agent orchestration with Supervisor router."""

from agents.graph import build_graph
from persistence import save_run
from config import PipelineConfig


def main() -> None:
    """Build orchestration graph and run full research workflow."""

    print("Building graph...")
    graph = build_graph(PipelineConfig())

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

    result["eval_scores"] = result.get("eval_scores", {})
    run_id = save_run("What are the key breakthroughs in quantum computing?", result)

    print("\n" + "=" * 80)
    print("=== FINAL REPORT ===")
    print(result["report"])
    print(f"\nSaved run: {run_id}")


if __name__ == "__main__":
    main()
