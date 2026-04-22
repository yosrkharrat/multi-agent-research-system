from __future__ import annotations

from pydantic import BaseModel


class PipelineConfig(BaseModel):
    planner_model: str = "mistral"
    researcher_model: str = "mistral"
    critic_model: str = "mistral"
    writer_model: str = "llama3"
    max_iterations: int = 1
    confidence_threshold: int = 3
    ollama_base_url: str = "http://localhost:11434"

    # Latency guards to keep runs in minutes instead of drifting into long loops.
    planner_max_questions: int = 3
    researcher_max_questions: int = 3
    researcher_max_reasoning_steps: int = 8
    researcher_notes_char_limit: int = 5000

    # Cap generation length per node.
    planner_num_predict: int = 220
    researcher_num_predict: int = 260
    critic_num_predict: int = 220
    writer_num_predict: int = 900