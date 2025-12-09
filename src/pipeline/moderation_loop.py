from __future__ import annotations

import json
import random
from pathlib import Path
from typing import Dict, List

from rich.console import Console
from rich.table import Table
from tqdm import tqdm

from src.actions.executor import ActionExecutor
from src.agents import ExpertAgent, ModerationRequest, StudentAgent
from src.config import AppConfig
from src.memory.vector_store import MemoryEntry, SimpleVectorStore
from src.state.user_state import UserStateManager
from src.utils.cost_tracker import CostTracker

console = Console()


def load_dataset(path: Path) -> List[Dict]:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def disagreement(student_plan: str, expert_plan: str) -> bool:
    return student_plan != expert_plan


def run_moderation_loop(config: AppConfig) -> None:
    random.seed(config.seed)

    data = load_dataset(config.data_path)
    
    # Initialize cost tracker
    cost_tracker = CostTracker()
    
    student = StudentAgent(config.student.model_dump(), None, cost_tracker=cost_tracker)
    expert = ExpertAgent(config.expert.model_dump(), cost_tracker=cost_tracker)
    memory = SimpleVectorStore(
        backend=config.memory.backend,
        embed_model=config.memory.embed_model if config.memory.backend == "sbert" else None,
    )

    # Initialize state manager and action executor
    state_path_str = config.loop.state_path or "data/user_state.json"
    state_path = Path(state_path_str)
    state_manager = UserStateManager(persistence_path=state_path)
    executor = ActionExecutor(state_manager)

    # Optional persistence load
    if config.memory.persistence_path:
        memory.load(config.memory.persistence_path)

    table = Table(title="Moderation Loop", show_lines=True)
    table.add_column("User")
    table.add_column("Comment")
    table.add_column("Student Plan", style="cyan")
    table.add_column("Expert Plan", style="magenta")
    table.add_column("Actions Executed", style="yellow")
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

        # Execute expert's actions (expert is ground truth)
        user_id = row["meta"].get("user", "unknown")
        action_results = executor.execute_actions(expert_out.actions, user_id, row["comment"])
        action_summary = "; ".join([r.message[:50] for r in action_results[:2]])  # Show first 2 actions
        if len(action_results) > 2:
            action_summary += f" (+{len(action_results) - 2} more)"

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
            cost_stats = cost_tracker.get_stats()
            event = {
                "idx": idx,
                "user": row["meta"]["user"],
                "comment": row["comment"],
                "student_plan": student_out.plan,
                "expert_plan": expert_out.plan,
                "actions_executed": [r.action for r in action_results],
                "action_results": [{"action": r.action, "success": r.success, "message": r.message} for r in action_results],
                "mem_added": mem_added == "yes",
                "retrieved_count": len(retrieved),
                "memory_size": len(memory.entries),
                "cumulative_cost": cost_stats["total_cost"],
                "cumulative_calls": cost_stats["total_calls"],
            }
            with log_path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(event) + "\n")

        table.add_row(
            str(row["meta"]["user"]),
            row["comment"][:50] + "..." if len(row["comment"]) > 50 else row["comment"],
            student_out.plan[:40] + "..." if len(student_out.plan) > 40 else student_out.plan,
            expert_out.plan[:40] + "..." if len(expert_out.plan) > 40 else expert_out.plan,
            action_summary[:60] + "..." if len(action_summary) > 60 else action_summary,
            mem_added,
        )

        if (idx + 1) % config.loop.audit_every == 0:
            console.print(table)

    console.print("\n[bold]Final memory size:[/bold]", len(memory.entries))

    # Optional persistence save
    if config.memory.persistence_path:
        memory.save(config.memory.persistence_path)
        console.print(f"[bold]Memory saved to[/bold] {config.memory.persistence_path}")

    # Save user state
    state_manager.save()
    console.print(f"[bold]User state saved to[/bold] {state_path}")
    
    # Show summary stats
    all_stats = state_manager.get_all_stats()
    total_bans = sum(s["ban_count"] for s in all_stats.values())
    total_warnings = sum(s["warning_count"] for s in all_stats.values())
    total_timeouts = sum(s["timeout_count"] for s in all_stats.values())
    console.print(f"\n[bold]Summary:[/bold] {len(all_stats)} users, {total_bans} bans, {total_warnings} warnings, {total_timeouts} timeouts")
    
    # Show cost summary
    cost_stats = cost_tracker.get_stats()
    console.print(f"\n[bold]Cost Summary:[/bold]")
    console.print(f"  Total API calls: {cost_stats['total_calls']}")
    console.print(f"  Total tokens: {cost_stats['total_tokens']:,}")
    console.print(f"  Total cost: ${cost_stats['total_cost']:.4f}")
    if cost_stats['by_model']:
        console.print(f"  By model:")
        for model, stats in cost_stats['by_model'].items():
            console.print(f"    {model}: {stats['calls']} calls, {stats['tokens']:,} tokens, ${stats['cost']:.4f}")

