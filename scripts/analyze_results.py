#!/usr/bin/env python3
"""
Analyze results from moderation loop logs.
Computes metrics, agreement rates, memory growth, etc.
"""

import argparse
import json
from pathlib import Path
from collections import defaultdict
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from rich.console import Console
from rich.table import Table

console = Console()


def analyze_logs(log_path: Path):
    """Analyze JSONL log file and compute metrics."""
    if not log_path.exists():
        console.print(f"[red]Log file not found: {log_path}[/red]")
        return None

    events = []
    with log_path.open("r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                events.append(json.loads(line))

    if not events:
        console.print("[yellow]No events found in log file.[/yellow]")
        return None

    # Compute metrics
    total_events = len(events)
    disagreements = sum(1 for e in events if e.get("mem_added", False))
    agreement_rate = 1.0 - (disagreements / total_events) if total_events > 0 else 0.0

    # Memory growth
    memory_sizes = [e.get("memory_size", 0) for e in events]
    final_memory_size = memory_sizes[-1] if memory_sizes else 0
    initial_memory_size = memory_sizes[0] if memory_sizes else 0

    # Cost tracking
    final_cost = events[-1].get("cumulative_cost", 0) if events else 0
    final_calls = events[-1].get("cumulative_calls", 0) if events else 0

    # Action distribution
    action_counts = defaultdict(int)
    for event in events:
        for action in event.get("actions_executed", []):
            action_counts[action] += 1

    # Agreement rate over time (compute rolling average)
    window_size = max(10, total_events // 10)
    agreement_over_time = []
    for i in range(window_size, total_events + 1):
        window = events[i - window_size : i]
        window_agreements = sum(1 for e in window if not e.get("mem_added", False))
        agreement_over_time.append(window_agreements / len(window))

    return {
        "total_events": total_events,
        "disagreements": disagreements,
        "agreement_rate": round(agreement_rate, 3),
        "memory_growth": final_memory_size - initial_memory_size,
        "final_memory_size": final_memory_size,
        "initial_memory_size": initial_memory_size,
        "total_cost": round(final_cost, 4),
        "total_api_calls": final_calls,
        "avg_cost_per_event": round(final_cost / total_events, 6) if total_events > 0 else 0.0,
        "action_distribution": dict(action_counts),
        "agreement_over_time": agreement_over_time,
        "final_agreement_rate": agreement_over_time[-1] if agreement_over_time else 0.0,
    }


def main():
    parser = argparse.ArgumentParser(description="Analyze moderation loop results.")
    parser.add_argument("--log", type=Path, default=Path("logs/run_log.jsonl"))
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()

    metrics = analyze_logs(args.log)
    if not metrics:
        return

    # Display results
    console.print("\n[bold]Analysis Results[/bold]\n")

    # Summary table
    table = Table(title="Summary Metrics", show_lines=True)
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="green")

    table.add_row("Total Events", str(metrics["total_events"]))
    table.add_row("Disagreements", str(metrics["disagreements"]))
    table.add_row("Agreement Rate", f"{metrics['agreement_rate']:.1%}")
    table.add_row("Final Agreement Rate", f"{metrics['final_agreement_rate']:.1%}")
    table.add_row("Memory Growth", str(metrics["memory_growth"]))
    table.add_row("Final Memory Size", str(metrics["final_memory_size"]))
    table.add_row("Total Cost", f"${metrics['total_cost']:.4f}")
    table.add_row("Total API Calls", str(metrics["total_api_calls"]))
    table.add_row("Avg Cost per Event", f"${metrics['avg_cost_per_event']:.6f}")

    console.print(table)

    # Action distribution
    if metrics["action_distribution"]:
        console.print("\n[bold]Action Distribution[/bold]\n")
        action_table = Table(show_lines=True)
        action_table.add_column("Action", style="cyan")
        action_table.add_column("Count", style="yellow", justify="right")

        sorted_actions = sorted(
            metrics["action_distribution"].items(), key=lambda x: x[1], reverse=True
        )
        for action, count in sorted_actions:
            action_table.add_row(action, str(count))

        console.print(action_table)

    # Save to file if requested
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with args.output.open("w", encoding="utf-8") as f:
            json.dump(metrics, f, indent=2)
        console.print(f"\n[green]Results saved to {args.output}[/green]")


if __name__ == "__main__":
    main()

