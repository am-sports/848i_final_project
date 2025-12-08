from __future__ import annotations

import argparse
import json
import random
from pathlib import Path

from tqdm import tqdm

from src.agents import ExpertAgent, ModerationRequest, StudentAgent
from src.config import load_config
from src.memory.vector_store import MemoryEntry, SimpleVectorStore


def load_dataset(path: Path):
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def run_modes(config_path: Path):
    config = load_config(config_path)
    data = load_dataset(config.data_path)
    random.seed(config.seed)

    # Mode A: Student only (no expert, no memory)
    student_only = StudentAgent(config.student.model_dump(), None)

    # Mode B: Student + Expert + Memory (current loop)
    student = StudentAgent(config.student.model_dump(), None)
    expert = ExpertAgent(config.expert.model_dump())
    memory = SimpleVectorStore(
        backend=config.memory.backend,
        embed_model=config.memory.embed_model if config.memory.backend == "sbert" else None,
    )

    stats = {
        "student_only": {"count": 0},
        "student_plus_memory": {"count": 0, "agreements": 0, "memory_adds": 0},
        "expert_only": {"count": 0},
    }

    for row in tqdm(data[: config.loop.max_messages], desc="Eval"):
        req = ModerationRequest(
            comment=row["comment"],
            meta=row.get("meta", {}),
            persona=row.get("persona", "firm_professional"),
            retrieved=[],
        )

        # Mode A
        _ = student_only.moderate(req)
        stats["student_only"]["count"] += 1

        # Mode C: Expert only as proxy ground truth
        expert_out = expert.moderate(req)
        stats["expert_only"]["count"] += 1

        # Mode B: Student + Memory + Expert audit
        retrieved = memory.search(
            query=row["comment"],
            top_k=config.memory.top_k,
            min_similarity=config.memory.min_similarity,
        )
        req_b = ModerationRequest(
            comment=row["comment"],
            meta=row.get("meta", {}),
            persona=row.get("persona", "firm_professional"),
            retrieved=retrieved,
        )
        student_out = student.moderate(req_b)
        stats["student_plus_memory"]["count"] += 1
        if student_out.plan == expert_out.plan:
            stats["student_plus_memory"]["agreements"] += 1
        else:
            mem_entry = MemoryEntry(
                state=row["comment"],
                reasoning=expert_out.reasoning,
                plan=expert_out.plan,
                persona=row.get("persona", "firm_professional"),
            )
            memory.add(mem_entry)
            stats["student_plus_memory"]["memory_adds"] += 1

    total = stats["student_plus_memory"]["count"]
    agree = stats["student_plus_memory"]["agreements"]
    stats["student_plus_memory"]["agreement_rate"] = round(agree / total, 3) if total else 0.0

    return stats


def main():
    parser = argparse.ArgumentParser(description="Compare Student-only vs Student+Memory vs Expert-only.")
    parser.add_argument("--config", type=Path, default=Path("configs/default.yaml"))
    args = parser.parse_args()

    stats = run_modes(args.config)
    print(json.dumps(stats, indent=2))


if __name__ == "__main__":
    main()

