from __future__ import annotations

import json
import random
from pathlib import Path
from typing import Dict, List

from rich.console import Console
from rich.table import Table
from tqdm import tqdm

from src.agents import ExpertAgent, ModerationRequest, StudentAgent
from src.config import AppConfig
from src.memory.vector_store import MemoryEntry, SimpleVectorStore

console = Console()


def load_dataset(path: Path) -> List[Dict]:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def disagreement(student_plan: str, expert_plan: str) -> bool:
    return student_plan != expert_plan


def run_moderation_loop(config: AppConfig) -> None:
    random.seed(config.seed)

    data = load_dataset(config.data_path)
    student = StudentAgent(config.student.model_dump(), None)
    expert = ExpertAgent(config.expert.model_dump())
    memory = SimpleVectorStore(
        backend=config.memory.backend,
        embed_model=config.memory.embed_model if config.memory.backend == "sbert" else None,
    )

    # Optional persistence load
    if config.memory.persistence_path:
        memory.load(config.memory.persistence_path)

    table = Table(title="Moderation Loop", show_lines=True)
    table.add_column("User")
    table.add_column("Comment")
    table.add_column("Student Plan", style="cyan")
    table.add_column("Expert Plan", style="magenta")
    table.add_column("Memory Added", style="green")

    log_path = Path(config.loop.log_path) if getattr(config.loop, "log_path", None) else None
    if log_path:
        log_path.parent.mkdir(parents=True, exist_ok=True)

    for idx, row in enumerate(tqdm(data[: config.loop.max_messages], desc="Moderating")):
        retrieved = memory.search(
            query=row["comment"],
            top_k=config.memory.top_k,
            min_similarity=config.memory.min_similarity,
        )
        req = ModerationRequest(
            comment=row["comment"],
            meta=row.get("meta", {}),
            persona=row.get("persona", "firm_professional"),
            retrieved=retrieved,
        )

        student_out = student.moderate(req)
        expert_out = expert.moderate(req)

        mem_added = "no"
        if disagreement(student_out.plan, expert_out.plan):
            mem_entry = MemoryEntry(
                state=row["comment"],
                reasoning=expert_out.reasoning,
                plan=expert_out.plan,
                persona=row.get("persona", "firm_professional"),
            )
            memory.add(mem_entry)
            mem_added = "yes"

        if log_path:
            event = {
                "idx": idx,
                "user": row["meta"]["user"],
                "comment": row["comment"],
                "student_plan": student_out.plan,
                "expert_plan": expert_out.plan,
                "mem_added": mem_added == "yes",
                "retrieved_count": len(retrieved),
            }
            with log_path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(event) + "\n")

        table.add_row(
            str(row["meta"]["user"]),
            row["comment"],
            student_out.plan,
            expert_out.plan,
            mem_added,
        )

        if (idx + 1) % config.loop.audit_every == 0:
            console.print(table)

    console.print("\n[bold]Final memory size:[/bold]", len(memory.entries))

    # Optional persistence save
    if config.memory.persistence_path:
        memory.save(config.memory.persistence_path)
        console.print(f"[bold]Memory saved to[/bold] {config.memory.persistence_path}")

