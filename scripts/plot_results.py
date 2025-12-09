#!/usr/bin/env python3
"""
Generate plots from moderation loop logs.
Creates visualizations for memory growth, agreement rates, costs, etc.
"""

import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

import matplotlib.pyplot as plt
import numpy as np


def load_logs(log_path: Path):
    """Load events from JSONL log file."""
    events = []
    if not log_path.exists():
        print(f"Log file not found: {log_path}")
        return events

    with log_path.open("r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                events.append(json.loads(line))
    return events


def plot_memory_growth(events, output_dir: Path):
    """Plot memory size over time."""
    indices = [e["idx"] for e in events]
    memory_sizes = [e.get("memory_size", 0) for e in events]

    plt.figure(figsize=(10, 6))
    plt.plot(indices, memory_sizes, linewidth=2, color="blue")
    plt.xlabel("Event Index", fontsize=12)
    plt.ylabel("Memory Size (entries)", fontsize=12)
    plt.title("Memory Growth Over Time", fontsize=14, fontweight="bold")
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(output_dir / "memory_growth.png", dpi=150)
    plt.close()
    print(f"Saved: {output_dir / 'memory_growth.png'}")


def plot_agreement_rate(events, output_dir: Path):
    """Plot agreement rate over time (rolling average)."""
    window_size = max(10, len(events) // 10)
    indices = []
    agreement_rates = []

    for i in range(window_size, len(events) + 1):
        window = events[i - window_size : i]
        agreements = sum(1 for e in window if not e.get("mem_added", False))
        agreement_rates.append(agreements / len(window))
        indices.append(i - 1)

    plt.figure(figsize=(10, 6))
    plt.plot(indices, agreement_rates, linewidth=2, color="green")
    plt.xlabel("Event Index", fontsize=12)
    plt.ylabel("Agreement Rate", fontsize=12)
    plt.title(f"Agreement Rate Over Time (rolling window: {window_size})", fontsize=14, fontweight="bold")
    plt.ylim(0, 1)
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(output_dir / "agreement_rate.png", dpi=150)
    plt.close()
    print(f"Saved: {output_dir / 'agreement_rate.png'}")


def plot_cumulative_cost(events, output_dir: Path):
    """Plot cumulative cost over time."""
    indices = [e["idx"] for e in events]
    costs = [e.get("cumulative_cost", 0) for e in events]

    plt.figure(figsize=(10, 6))
    plt.plot(indices, costs, linewidth=2, color="red")
    plt.xlabel("Event Index", fontsize=12)
    plt.ylabel("Cumulative Cost ($)", fontsize=12)
    plt.title("Cumulative API Cost Over Time", fontsize=14, fontweight="bold")
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(output_dir / "cumulative_cost.png", dpi=150)
    plt.close()
    print(f"Saved: {output_dir / 'cumulative_cost.png'}")


def plot_action_distribution(events, output_dir: Path):
    """Plot action distribution pie chart."""
    from collections import defaultdict

    action_counts = defaultdict(int)
    for event in events:
        for action in event.get("actions_executed", []):
            action_counts[action] += 1

    if not action_counts:
        print("No actions found to plot")
        return

    actions = list(action_counts.keys())
    counts = list(action_counts.values())

    plt.figure(figsize=(10, 8))
    plt.pie(counts, labels=actions, autopct="%1.1f%%", startangle=90)
    plt.title("Action Distribution", fontsize=14, fontweight="bold")
    plt.tight_layout()
    plt.savefig(output_dir / "action_distribution.png", dpi=150)
    plt.close()
    print(f"Saved: {output_dir / 'action_distribution.png'}")


def plot_cost_comparison(eval_results_path: Path, output_dir: Path):
    """Plot cost comparison from eval_compare results."""
    if not eval_results_path.exists():
        print(f"Eval results file not found: {eval_results_path}")
        return

    with eval_results_path.open("r", encoding="utf-8") as f:
        results = json.load(f)

    if "costs" not in results:
        print("No cost data in eval results")
        return

    costs = results["costs"]
    modes = ["Student Only", "Student + Memory", "Expert Only"]
    cost_values = [
        costs["student_only"]["total_cost"],
        costs["student_plus_memory"]["total_cost"],
        costs["expert_only"]["total_cost"],
    ]

    plt.figure(figsize=(10, 6))
    bars = plt.bar(modes, cost_values, color=["blue", "green", "red"], alpha=0.7)
    plt.ylabel("Total Cost ($)", fontsize=12)
    plt.title("Cost Comparison: Student Only vs Student+Memory vs Expert Only", fontsize=14, fontweight="bold")
    plt.grid(True, alpha=0.3, axis="y")

    # Add value labels on bars
    for bar, value in zip(bars, cost_values):
        plt.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height(),
            f"${value:.4f}",
            ha="center",
            va="bottom",
            fontsize=10,
        )

    plt.tight_layout()
    plt.savefig(output_dir / "cost_comparison.png", dpi=150)
    plt.close()
    print(f"Saved: {output_dir / 'cost_comparison.png'}")


def main():
    parser = argparse.ArgumentParser(description="Generate plots from moderation results.")
    parser.add_argument("--log", type=Path, default=Path("logs/run_log.jsonl"))
    parser.add_argument("--eval", type=Path, default=None)
    parser.add_argument("--output", type=Path, default=Path("results/plots"))
    args = parser.parse_args()

    args.output.mkdir(parents=True, exist_ok=True)

    # Load logs
    events = load_logs(args.log)
    if not events:
        print("No events found. Run the moderation loop first.")
        return

    print(f"Generating plots from {len(events)} events...\n")

    # Generate plots
    plot_memory_growth(events, args.output)
    plot_agreement_rate(events, args.output)
    plot_cumulative_cost(events, args.output)
    plot_action_distribution(events, args.output)

    # Cost comparison if eval results available
    if args.eval:
        plot_cost_comparison(args.eval, args.output)
    elif Path("eval_results.json").exists():
        plot_cost_comparison(Path("eval_results.json"), args.output)

    print(f"\n✅ All plots saved to {args.output}")


if __name__ == "__main__":
    main()

