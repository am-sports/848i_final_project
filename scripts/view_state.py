#!/usr/bin/env python3
"""
View user state statistics (ban counts, warnings, etc.)
"""

import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.state.user_state import UserStateManager
from rich.console import Console
from rich.table import Table

console = Console()


def main():
    parser = argparse.ArgumentParser(description="View user state statistics.")
    parser.add_argument("--state", type=Path, default=Path("data/user_state.json"))
    args = parser.parse_args()

    if not args.state.exists():
        console.print(f"[red]State file not found: {args.state}[/red]")
        console.print("Run the moderation loop first to generate state.")
        return

    state_manager = UserStateManager(persistence_path=args.state)
    state_manager.load(args.state)

    all_stats = state_manager.get_all_stats()

    if not all_stats:
        console.print("[yellow]No user state found.[/yellow]")
        return

    table = Table(title="User State Statistics", show_lines=True)
    table.add_column("User ID", style="cyan")
    table.add_column("Bans", style="red", justify="right")
    table.add_column("Warnings", style="yellow", justify="right")
    table.add_column("Timeouts", style="orange1", justify="right")
    table.add_column("Deleted", style="magenta", justify="right")
    table.add_column("Replies", style="green", justify="right")
    table.add_column("Last Action", style="blue")

    # Sort by ban count (descending)
    sorted_users = sorted(all_stats.items(), key=lambda x: x[1]["ban_count"], reverse=True)

    for user_id, stats in sorted_users:
        table.add_row(
            user_id,
            str(stats["ban_count"]),
            str(stats["warning_count"]),
            str(stats["timeout_count"]),
            str(stats["deleted_comments"]),
            str(stats["replies_sent"]),
            stats["last_action"] or "none",
        )

    console.print(table)

    # Summary
    total_bans = sum(s["ban_count"] for s in all_stats.values())
    total_warnings = sum(s["warning_count"] for s in all_stats.values())
    total_timeouts = sum(s["timeout_count"] for s in all_stats.values())
    total_deleted = sum(s["deleted_comments"] for s in all_stats.values())
    total_replies = sum(s["replies_sent"] for s in all_stats.values())

    console.print(f"\n[bold]Summary:[/bold]")
    console.print(f"  Total users: {len(all_stats)}")
    console.print(f"  Total bans: {total_bans}")
    console.print(f"  Total warnings: {total_warnings}")
    console.print(f"  Total timeouts: {total_timeouts}")
    console.print(f"  Total deleted comments: {total_deleted}")
    console.print(f"  Total replies sent: {total_replies}")


if __name__ == "__main__":
    main()

