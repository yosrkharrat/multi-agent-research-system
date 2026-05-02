"""
Research Runner - Quantum Computing Breakthroughs
Run this script to research: "What are the key breakthroughs in quantum computing?"
"""

import sys
import uuid
from pathlib import Path

# Add src to path
src_path = str((Path(__file__).parent / "src").resolve())
if src_path not in sys.path:
    sys.path.insert(0, src_path)

from agents.graph import build_graph, make_config
from persistence import save_run
from config import PipelineConfig


def run_quantum_research() -> None:
    """Research quantum computing breakthroughs."""
    
    topic = "What are the key breakthroughs in quantum computing?"
    
    print("\n" + "=" * 80)
    print("  MULTI-AGENT RESEARCH SYSTEM")
    print("=" * 80)
    print(f"\n📚 Topic: {topic}\n")
    print("Building research pipeline...")
    
    try:
        graph = build_graph(PipelineConfig())
        print("✅ Graph built\n")
    except Exception as e:
        print(f"❌ Failed to build graph: {e}")
        print("\n⚠️  Check that Ollama is running on localhost:11434")
        print("   Run in a separate terminal: python start-ollama.ps1")
        return
    
    print("Starting research orchestration...")
    print("=" * 80)
    
    thread_id = str(uuid.uuid4())
    config = make_config(thread_id)
    
    try:
        result = graph.invoke(
            {
                "messages": [],
                "topic": topic,
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
        run_id = save_run(topic, result)
        
        print("\n" + "=" * 80)
        print("  ✅ RESEARCH COMPLETE")
        print("=" * 80)
        print("\n📄 GENERATED REPORT:\n")
        print(result["report"])
        print("\n" + "=" * 80)
        print(f"📊 Statistics:")
        print(f"   • Iterations: {result['iteration']}")
        print(f"   • Questions planned: {len(result['plan'])}")
        print(f"   • Findings collected: {len(result['findings'])}")
        print(f"   • Run ID: {run_id}")
        print("=" * 80 + "\n")
        
        return result
        
    except ConnectionError as e:
        print(f"\n❌ Connection Error: {e}")
        print("\n⚠️  Ollama is not running!")
        print("\n📝 To fix this:")
        print("   1. Open a new PowerShell terminal")
        print("   2. Navigate to this directory")
        print("   3. Run: python start-ollama.ps1")
        print("   4. Wait for Ollama to fully start")
        print("   5. Run this script again in another terminal")
        return None
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return None


if __name__ == "__main__":
    run_quantum_research()
