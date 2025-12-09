from __future__ import annotations

import argparse
import json
import random
from pathlib import Path

from tqdm import tqdm

from src.agents import ExpertAgent, ModerationRequest, StudentAgent
from src.config import load_config
from src.memory.vector_store import MemoryEntry, SimpleVectorStore
from src.utils.cost_tracker import CostTracker


def load_dataset(path: Path):
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def run_modes(config_path: Path):
    config = load_config(config_path)
    data = load_dataset(config.data_path)
    random.seed(config.seed)

    # Initialize cost trackers for each mode
    cost_tracker_student_only = CostTracker()
    cost_tracker_full = CostTracker()
    cost_tracker_expert_only = CostTracker()

    # Mode A: Student only (no expert, no memory)
    student_only = StudentAgent(config.student.model_dump(), None, cost_tracker=cost_tracker_student_only)

    # Mode B: Student + Expert + Memory (current loop)
    student = StudentAgent(config.student.model_dump(), None, cost_tracker=cost_tracker_full)
    expert = ExpertAgent(config.expert.model_dump(), cost_tracker=cost_tracker_full)

    # Mode C: Expert only
    expert_only = ExpertAgent(config.expert.model_dump(), cost_tracker=cost_tracker_expert_only)
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
            persona="firm_professional",  # Default persona since it's no longer in data
            retrieved=[],
        )

        # Mode A
        _ = student_only.moderate(req)
        stats["student_only"]["count"] += 1

        # Mode C: Expert only as proxy ground truth
        expert_out = expert_only.moderate(req)
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
            persona="firm_professional",  # Default persona since it's no longer in data
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
                persona="firm_professional",  # Default persona since it's no longer in data
            )
            memory.add(mem_entry)
            stats["student_plus_memory"]["memory_adds"] += 1

    total = stats["student_plus_memory"]["count"]
    agree = stats["student_plus_memory"]["agreements"]
    stats["student_plus_memory"]["agreement_rate"] = round(agree / total, 3) if total else 0.0

    # Add cost information
    stats["costs"] = {
        "student_only": cost_tracker_student_only.get_stats(),
        "student_plus_memory": cost_tracker_full.get_stats(),
        "expert_only": cost_tracker_expert_only.get_stats(),
    }

    # Calculate cost savings
    expert_only_cost = stats["costs"]["expert_only"]["total_cost"]
    full_cost = stats["costs"]["student_plus_memory"]["total_cost"]
    if expert_only_cost > 0:
        stats["cost_savings"] = {
            "absolute": round(expert_only_cost - full_cost, 4),
            "percentage": round(((expert_only_cost - full_cost) / expert_only_cost) * 100, 2),
        }

    return stats


def main():
    parser = argparse.ArgumentParser(description="Compare Student-only vs Student+Memory vs Expert-only.")
    parser.add_argument("--config", type=Path, default=Path("configs/default.yaml"))
    parser.add_argument("--output", type=Path, default=Path("eval_results.json"))
    args = parser.parse_args()

    stats = run_modes(args.config)

    # Save to file
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8") as f:
        json.dump(stats, f, indent=2)

    # Also print to console
    print(json.dumps(stats, indent=2))
    print(f"\n✅ Results saved to {args.output}")


if __name__ == "__main__":
    main()
