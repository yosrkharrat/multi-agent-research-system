import json
import uuid
from datetime import datetime
from pathlib import Path


RUNS_DIR = Path("runs")


def save_run(topic: str, state: dict) -> str:
    run_id = str(uuid.uuid4())[:8]
    RUNS_DIR.mkdir(exist_ok=True)
    payload = {
        "id": run_id,
        "topic": topic,
        "timestamp": datetime.utcnow().isoformat(),
        "plan": state.get("plan", []),
        "findings_count": len(state.get("findings", [])),
        "iterations": state.get("iteration", 0),
        "report": state.get("report", ""),
        "eval": state.get("eval_scores", {}),
    }
    (RUNS_DIR / f"{run_id}.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return run_id


def list_runs() -> list[dict]:
    if not RUNS_DIR.exists():
        return []

    runs = []
    for path in sorted(RUNS_DIR.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True):
        try:
            runs.append(json.loads(path.read_text(encoding="utf-8")))
        except json.JSONDecodeError:
            continue
    return runs


def get_run(run_id: str) -> dict | None:
    path = RUNS_DIR / f"{run_id}.json"
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None