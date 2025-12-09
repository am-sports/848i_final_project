#!/usr/bin/env python3
"""
Generate a comprehensive results report from analysis and evaluation.
"""

import argparse
import json
from pathlib import Path
import sys
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))

from rich.console import Console
from rich.markdown import Markdown

console = Console()


def generate_report(analysis_path: Path, eval_path: Path | None, output_path: Path):
    """Generate markdown report from analysis results."""
    
    # Load analysis results
    if not analysis_path.exists():
        console.print(f"[red]Analysis file not found: {analysis_path}[/red]")
        return
    
    with analysis_path.open("r", encoding="utf-8") as f:
        analysis = json.load(f)
    
    # Load eval results if available
    eval_data = None
    if eval_path and eval_path.exists():
        with eval_path.open("r", encoding="utf-8") as f:
            eval_data = json.load(f)
    
    # Generate markdown report
    report = f"""# Moderation System Results Report

Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

## Summary

- **Total Events Processed**: {analysis['total_events']}
- **Final Agreement Rate**: {analysis['agreement_rate']:.1%}
- **Memory Growth**: {analysis['memory_growth']} entries
- **Total Cost**: ${analysis['total_cost']:.4f}
- **Total API Calls**: {analysis['total_api_calls']}

## Performance Metrics

### Agreement Rate
- **Overall Agreement Rate**: {analysis['agreement_rate']:.1%}
- **Final Agreement Rate** (last window): {analysis['final_agreement_rate']:.1%}
- **Total Disagreements**: {analysis['disagreements']}

The system achieved {analysis['agreement_rate']:.1%} agreement between Student and Expert agents, with {analysis['disagreements']} disagreements that led to memory expansion.

### Memory System
- **Initial Memory Size**: {analysis['initial_memory_size']} entries
- **Final Memory Size**: {analysis['final_memory_size']} entries
- **Memory Growth**: {analysis['memory_growth']} new entries

The memory system grew by {analysis['memory_growth']} entries as the Expert corrected Student decisions.

### Cost Analysis
- **Total Cost**: ${analysis['total_cost']:.4f}
- **Average Cost per Event**: ${analysis['avg_cost_per_event']:.6f}
- **Total API Calls**: {analysis['total_api_calls']}

"""
    
    if eval_data and "cost_savings" in eval_data:
        savings = eval_data["cost_savings"]
        report += f"""### Cost Savings vs Expert-Only Baseline
- **Expert-Only Cost**: ${eval_data['costs']['expert_only']['total_cost']:.4f}
- **Hybrid System Cost**: ${eval_data['costs']['student_plus_memory']['total_cost']:.4f}
- **Absolute Savings**: ${savings['absolute']:.4f}
- **Percentage Savings**: {savings['percentage']:.1f}%

The hybrid Student+Memory+Expert system achieved {savings['percentage']:.1f}% cost savings compared to using Expert-only for all decisions.

"""
    
    report += f"""## Action Distribution

"""
    
    if analysis.get("action_distribution"):
        sorted_actions = sorted(
            analysis["action_distribution"].items(), key=lambda x: x[1], reverse=True
        )
        for action, count in sorted_actions:
            percentage = (count / analysis['total_events']) * 100
            report += f"- **{action}**: {count} times ({percentage:.1f}%)\n"
    
    report += f"""
## Methodology

The system uses a hierarchical agentic framework:
1. **Student Agent** (Qwen/Qwen2.5-7B-Instruct-Turbo): Fast, low-cost moderation decisions
2. **Expert Agent** (meta-llama/Llama-3.3-70B-Instruct-Turbo): High-fidelity ground-truth decisions
3. **Memory System**: Retrieval-augmented generation with disagreement-driven learning

When Student and Expert disagree, the Expert's reasoning and plan are stored in memory for future reference.

## Files Generated

- Analysis results: `{analysis_path}`
- Plots: `results/plots/`
  - Memory growth over time
  - Agreement rate over time
  - Cumulative cost over time
  - Action distribution
  - Cost comparison (if eval data available)
"""
    
    # Save report
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(report, encoding="utf-8")
    console.print(f"[green]Report saved to {output_path}[/green]")
    
    # Display report
    console.print(Markdown(report))


def main():
    parser = argparse.ArgumentParser(description="Generate results report.")
    parser.add_argument("--analysis", type=Path, default=Path("results/analysis.json"))
    parser.add_argument("--eval", type=Path, default=None)
    parser.add_argument("--output", type=Path, default=Path("results/report.md"))
    args = parser.parse_args()

    generate_report(args.analysis, args.eval, args.output)


if __name__ == "__main__":
    main()

