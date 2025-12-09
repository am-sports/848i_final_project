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


def load_dataset(path: Path) -> List[str]:
    """Load comments as a simple list of strings."""
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    # Handle both old format (list of dicts) and new format (list of strings)
    if isinstance(data, list) and len(data) > 0:
        if isinstance(data[0], str):
            return data
        elif isinstance(data[0], dict):
            return [item.get("comment", "") for item in data if "comment" in item]
    return []


def run_moderation_loop(config: AppConfig) -> None:
    random.seed(config.seed)

    # Load comments as simple list
    all_comments = load_dataset(config.data_path)

    if len(all_comments) < 150:
        console.print(f"[red]Error: Need at least 150 comments, found {len(all_comments)}[/red]")
        return

    # Randomly shuffle comments
    random.shuffle(all_comments)
    console.print(f"[green]Loaded {len(all_comments)} comments (shuffled)[/green]")

    # Split into phases
    baseline_comments = all_comments[:50]
    accumulation_comments = all_comments[50:100]
    evaluation_comments = all_comments[100:150]

    console.print(f"\n[bold]Phase 1: Baseline (50 comments)[/bold]")
    console.print("  - Student model without state or retrieval")

    console.print(f"\n[bold]Phase 2: Accumulation (50 comments)[/bold]")
    console.print("  - Full moderation loop with state and retrieval")
    console.print("  - Builds memory database and user state")

    console.print(f"\n[bold]Phase 3: Evaluation (50 comments)[/bold]")
    console.print("  - Compare Student vs Expert on accumulated state")

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

    log_path = Path(config.loop.log_path) if getattr(config.loop, "log_path", None) else None
    if log_path:
        log_path.parent.mkdir(parents=True, exist_ok=True)
        # Clear log file
        if log_path.exists():
            log_path.unlink()

    # Track current stream context
    current_topic = "gaming"
    current_viewer_count = 1000

    # Determine user ID range based on total iterations
    total_iterations = 150
    max_user_id = total_iterations // 2  # Range [1, total_iterations/2]
    console.print(f"\n[bold]User ID range: 1 to {max_user_id}[/bold]")

    # ===== PHASE 1: BASELINE =====
    console.print("\n" + "="*60)
    console.print("[bold cyan]PHASE 1: BASELINE EVALUATION[/bold cyan]")
    console.print("="*60)

    baseline_table = Table(title="Baseline (Student without state/retrieval)", show_lines=True)
    baseline_table.add_column("Comment")
    baseline_table.add_column("Student Plan", style="cyan")
    baseline_table.add_column("Actions", style="yellow")

    baseline_stats = {"agreements": 0, "disagreements": 0}

    for idx, comment in enumerate(tqdm(baseline_comments, desc="Baseline")):
        # Random user ID from range [1, max_user_id]
        user_id = f"user_{random.randint(1, max_user_id):03d}"

        # Update user state context
        state_manager.update_context(
            user_id,
            follower_count=random.randint(0, 10000),
            viewer_count=current_viewer_count,
            current_topic=current_topic,
        )

        # Get state (but don't use it for baseline)
        user_state = state_manager.get_state_dict(user_id)

        # Student WITHOUT state or retrieval
        req = ModerationRequest(
            comment=comment,
            state=user_state,
            meta={},
            persona="firm_professional",
            retrieved=[],
        )

        student_out = student.moderate(req, use_state=False, use_retrieval=False)

        # Expert reviews
        expert_decision = expert.review_student_plan(req, student_out.plan, student_out.reasoning)

        if expert_decision.agrees:
            final_actions = student_out.actions
            baseline_stats["agreements"] += 1
        else:
            final_actions = expert_decision.actions or []
            baseline_stats["disagreements"] += 1

        # Execute actions
        action_results = executor.execute_actions(final_actions, user_id, comment)
        action_summary = "; ".join([r.message[:50] for r in action_results[:2]])

        baseline_table.add_row(
            comment[:50] + "..." if len(comment) > 50 else comment,
            student_out.plan[:40] + "..." if len(student_out.plan) > 40 else student_out.plan,
            action_summary[:60] + "..." if len(action_summary) > 60 else action_summary,
        )

        # Log
        if log_path:
            cost_stats = cost_tracker.get_stats()
            event = {
                "phase": "baseline",
                "idx": idx,
                "user": user_id,
                "comment": comment,
                "student_plan": student_out.plan,
                "expert_agrees": expert_decision.agrees,
                "actions_executed": [r.action for r in action_results],
            }
            with log_path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(event) + "\n")

    console.print(baseline_table)
    console.print(f"\n[bold]Baseline Results:[/bold] {baseline_stats['agreements']} agreements, {baseline_stats['disagreements']} disagreements")

    # ===== PHASE 2: ACCUMULATION =====
    console.print("\n" + "="*60)
    console.print("[bold cyan]PHASE 2: ACCUMULATION[/bold cyan]")
    console.print("="*60)

    accumulation_table = Table(title="Accumulation (Building Memory)", show_lines=True)
    accumulation_table.add_column("User")
    accumulation_table.add_column("Comment")
    accumulation_table.add_column("Student Plan", style="cyan")
    accumulation_table.add_column("Expert Decision", style="magenta")
    accumulation_table.add_column("Memory Added", style="green")

    for idx, comment in enumerate(tqdm(accumulation_comments, desc="Accumulating")):
        # Random user ID (reuse users to build history)
        user_id = f"user_{random.randint(1, max_user_id):03d}"

        # Update user state context
        state_manager.update_context(
            user_id,
            follower_count=random.randint(0, 10000),
            viewer_count=current_viewer_count,
            current_topic=current_topic,
        )

        # Get current user state
        user_state = state_manager.get_state_dict(user_id)
        state_string = state_manager.get_state_string(user_id)

        # Create combined query: comment + state
        combined_query = f"{comment} | State: {state_string}"

        # Search memory by combined comment+state
        retrieved = memory.search(
            query=combined_query,
            top_k=5,
            min_similarity=config.memory.min_similarity,
        )

        # Student WITH state and retrieval
        req = ModerationRequest(
            comment=comment,
            state=user_state,
            meta={},
            persona="firm_professional",
            retrieved=retrieved,
        )

        student_out = student.moderate(req, use_state=True, use_retrieval=True)

        # Expert reviews
        expert_decision = expert.review_student_plan(req, student_out.plan, student_out.reasoning)

        # Determine final actions
        if expert_decision.agrees:
            final_actions = student_out.actions
            final_plan = student_out.plan
            final_reasoning = student_out.reasoning
            expert_status = "AGREES"
        else:
            final_actions = expert_decision.actions or []
            final_plan = expert_decision.plan or ""
            final_reasoning = expert_decision.reasoning or ""
            expert_status = "DISAGREES"

        # Execute actions
        action_results = executor.execute_actions(final_actions, user_id, comment)

        # If Expert disagreed, store in memory (using combined comment+state)
        mem_added = "no"
        if not expert_decision.agrees:
            mem_entry = MemoryEntry(
                state=combined_query,  # Combined comment + state
                comment=comment,
                state_metrics=state_string,
                reasoning=final_reasoning,
                plan=final_plan,
                persona="firm_professional",
            )
            memory.add(mem_entry)
            mem_added = "yes"

        accumulation_table.add_row(
            str(user_id),
            comment[:50] + "..." if len(comment) > 50 else comment,
            student_out.plan[:40] + "..." if len(student_out.plan) > 40 else student_out.plan,
            expert_status,
            mem_added,
        )

        # Log
        if log_path:
            cost_stats = cost_tracker.get_stats()
            event = {
                "phase": "accumulation",
                "idx": idx,
                "user": user_id,
                "comment": comment,
                "state": user_state,
                "student_plan": student_out.plan,
                "expert_agrees": expert_decision.agrees,
                "expert_plan": final_plan,
                "mem_added": mem_added == "yes",
                "memory_size": len(memory.entries),
            }
            with log_path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(event) + "\n")

    console.print(accumulation_table)
    console.print(f"\n[bold]Memory size after accumulation:[/bold] {len(memory.entries)}")

    # ===== PHASE 3: EVALUATION =====
    console.print("\n" + "="*60)
    console.print("[bold cyan]PHASE 3: EVALUATION[/bold cyan]")
    console.print("="*60)

    evaluation_table = Table(title="Evaluation (Student vs Expert)", show_lines=True)
    evaluation_table.add_column("User")
    evaluation_table.add_column("Comment")
    evaluation_table.add_column("Student Plan", style="cyan")
    evaluation_table.add_column("Expert Decision", style="magenta")
    evaluation_table.add_column("Agreement", style="green")

    evaluation_stats = {"agreements": 0, "disagreements": 0}

    for idx, comment in enumerate(tqdm(evaluation_comments, desc="Evaluating")):
        # Random user ID (reuse users with accumulated history)
        user_id = f"user_{random.randint(1, max_user_id):03d}"

        # Update user state context
        state_manager.update_context(
            user_id,
            follower_count=random.randint(0, 10000),
            viewer_count=current_viewer_count,
            current_topic=current_topic,
        )

        # Get current user state (with accumulated history)
        user_state = state_manager.get_state_dict(user_id)
        state_string = state_manager.get_state_string(user_id)

        # Create combined query
        combined_query = f"{comment} | State: {state_string}"

        # Search memory
        retrieved = memory.search(
            query=combined_query,
            top_k=5,
            min_similarity=config.memory.min_similarity,
        )

        # Student WITH state and retrieval
        req = ModerationRequest(
            comment=comment,
            state=user_state,
            meta={},
            persona="firm_professional",
            retrieved=retrieved,
        )

        student_out = student.moderate(req, use_state=True, use_retrieval=True)

        # Expert reviews
        expert_decision = expert.review_student_plan(req, student_out.plan, student_out.reasoning)

        if expert_decision.agrees:
            final_actions = student_out.actions
            evaluation_stats["agreements"] += 1
            agreement_status = "✓ AGREES"
        else:
            final_actions = expert_decision.actions or []
            evaluation_stats["disagreements"] += 1
            agreement_status = "✗ DISAGREES"

        # Execute actions
        action_results = executor.execute_actions(final_actions, user_id, comment)

        evaluation_table.add_row(
            str(user_id),
            comment[:50] + "..." if len(comment) > 50 else comment,
            student_out.plan[:40] + "..." if len(student_out.plan) > 40 else student_out.plan,
            "AGREES" if expert_decision.agrees else "DISAGREES",
            agreement_status,
        )

        # Log
        if log_path:
            cost_stats = cost_tracker.get_stats()
            event = {
                "phase": "evaluation",
                "idx": idx,
                "user": user_id,
                "comment": comment,
                "state": user_state,
                "student_plan": student_out.plan,
                "expert_agrees": expert_decision.agrees,
                "expert_plan": expert_decision.plan or student_out.plan,
                "agreement": expert_decision.agrees,
            }
            with log_path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(event) + "\n")

    console.print(evaluation_table)

    # ===== FINAL SUMMARY =====
    console.print("\n" + "="*60)
    console.print("[bold]FINAL SUMMARY[/bold]")
    console.print("="*60)

    console.print(f"\n[bold]Phase 1 (Baseline):[/bold]")
    console.print(f"  Agreements: {baseline_stats['agreements']}/{50} ({baseline_stats['agreements']/50*100:.1f}%)")
    console.print(f"  Disagreements: {baseline_stats['disagreements']}/{50} ({baseline_stats['disagreements']/50*100:.1f}%)")

    console.print(f"\n[bold]Phase 2 (Accumulation):[/bold]")
    console.print(f"  Memory entries added: {len(memory.entries)}")

    console.print(f"\n[bold]Phase 3 (Evaluation):[/bold]")
    console.print(f"  Agreements: {evaluation_stats['agreements']}/{50} ({evaluation_stats['agreements']/50*100:.1f}%)")
    console.print(f"  Disagreements: {evaluation_stats['disagreements']}/{50} ({evaluation_stats['disagreements']/50*100:.1f}%)")

    # Save memory
    if config.memory.persistence_path:
        memory.save(config.memory.persistence_path)
        console.print(f"\n[bold]Memory saved to[/bold] {config.memory.persistence_path}")

    # Save user state
    state_manager.save()
    console.print(f"[bold]User state saved to[/bold] {state_path}")

    # Show user stats
    all_stats = state_manager.get_all_stats()
    total_bans = sum(s["ban_count"] for s in all_stats.values())
    total_warnings = sum(s["warning_count"] for s in all_stats.values())
    total_timeouts = sum(s["timeout_count"] for s in all_stats.values())
    console.print(f"\n[bold]User Statistics:[/bold] {len(all_stats)} users, {total_bans} bans, {total_warnings} warnings, {total_timeouts} timeouts")

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
