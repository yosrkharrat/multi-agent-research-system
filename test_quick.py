"""Phase 3 quick test: demonstrates full orchestration with smaller scope."""

import uuid
from agents.graph import build_graph, make_config
from persistence import save_run
from config import PipelineConfig


def test_quick() -> None:
    """Run orchestration with a simpler, faster topic."""

    print("Building graph...")
    graph = build_graph(PipelineConfig())

    print("\n[Quick test] Running research on: 'What is machine learning?'")
    print("=" * 80)

    thread_id = str(uuid.uuid4())
    config = make_config(thread_id)

    result = graph.invoke(
        {
            "messages": [],
            "topic": "What is machine learning?",
            "plan": [],
            "findings": [],
            "critique": "",
            "report": "",
            "next_agent": "",
            "iteration": 0,
        },
        config=config,
    )

    result["eval_scores"] = result.get("eval_scores", {})
    run_id = save_run("What is machine learning?", result)

    print("\n" + "=" * 80)
    print("=== GENERATED REPORT ===\n")
    print(result["report"])
    print("\n" + "=" * 80)
    print(f"[Stats] Iterations: {result['iteration']}, Questions planned: {len(result['plan'])}")
    print(f"[Stats] Saved run: {run_id}")


if __name__ == "__main__":
    test_quick()
