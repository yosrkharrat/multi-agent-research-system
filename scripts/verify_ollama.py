from __future__ import annotations

import argparse
import statistics
import time
from typing import List

from local_llm.ollama_client import OllamaClient


def run_probe(model: str, host: str, attempts: int, prompt: str) -> int:
    client = OllamaClient(model=model, host=host, retries=3)

    latencies: List[float] = []
    failures = 0

    print(f"Testing model={model} against {host}")
    for i in range(1, attempts + 1):
        start = time.perf_counter()
        try:
            result = client.generate(prompt)
            latency = time.perf_counter() - start
            latencies.append(latency)
            preview = result.replace("\n", " ")[:120]
            print(f"[{i}/{attempts}] OK  {latency:.2f}s  {preview}")
        except Exception as exc:
            failures += 1
            latency = time.perf_counter() - start
            print(f"[{i}/{attempts}] FAIL {latency:.2f}s  {exc}")

    print("\nSummary")
    print(f"- attempts: {attempts}")
    print(f"- success:  {attempts - failures}")
    print(f"- failed:   {failures}")

    if latencies:
        print(f"- p50 latency: {statistics.median(latencies):.2f}s")
        print(f"- avg latency: {statistics.fmean(latencies):.2f}s")

    return 1 if failures else 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Probe local Ollama completion reliability.")
    parser.add_argument("--model", default="llama3", help="Model to test, e.g. llama3 or mistral")
    parser.add_argument("--host", default="http://localhost:11434", help="Ollama API base URL")
    parser.add_argument("--attempts", type=int, default=5, help="Number of completion attempts")
    parser.add_argument(
        "--prompt",
        default="Give a 2-sentence summary of why local LLMs are useful for agent systems.",
        help="Prompt used for reliability probe",
    )
    args = parser.parse_args()

    if args.attempts < 1:
        raise ValueError("--attempts must be >= 1")

    return run_probe(args.model, args.host, args.attempts, args.prompt)


if __name__ == "__main__":
    raise SystemExit(main())
