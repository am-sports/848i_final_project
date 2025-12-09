# Analysis and Visualization Guide

This guide explains how to use the analysis and visualization tools added to the project.

## Quick Start

After running the moderation loop, generate a complete analysis:

```bash
# 1. Run evaluation comparison
python scripts/eval_compare.py --config configs/default.yaml --output eval_results.json

# 2. Analyze results
python scripts/analyze_results.py --log logs/run_log.jsonl --output results/analysis.json

# 3. Generate plots
python scripts/plot_results.py --log logs/run_log.jsonl --eval eval_results.json --output results/plots

# 4. Generate report
python scripts/generate_report.py --analysis results/analysis.json --eval eval_results.json --output results/report.md
```

## Cost Tracking

Cost tracking is automatically enabled when using Together.ai models. The system tracks:
- API calls per model (Student vs Expert)
- Token usage (prompt + completion tokens)
- Cost calculations based on Together.ai pricing:
  - Qwen/Qwen2.5-7B-Instruct-Turbo: ~$0.0002 per 1K tokens
  - meta-llama/Llama-3.3-70B-Instruct-Turbo: ~$0.0007 per 1K tokens

Costs are displayed at the end of the moderation loop and included in logs.

## Analysis Scripts

### `analyze_results.py`
Computes comprehensive metrics from log files:
- Agreement rates (overall and over time)
- Memory growth statistics
- Cost analysis
- Action distribution
- API call statistics

**Usage:**
```bash
python scripts/analyze_results.py --log logs/run_log.jsonl --output results/analysis.json
```

### `plot_results.py`
Generates visualizations:
- **memory_growth.png**: Memory size over time
- **agreement_rate.png**: Agreement rate improvement (rolling average)
- **cumulative_cost.png**: Cost accumulation over time
- **action_distribution.png**: Pie chart of action types
- **cost_comparison.png**: Bar chart comparing costs across modes

**Usage:**
```bash
python scripts/plot_results.py --log logs/run_log.jsonl --eval eval_results.json --output results/plots
```

### `generate_report.py`
Creates a markdown report summarizing all findings:
- Performance metrics
- Cost analysis and savings
- Action distribution
- Methodology overview

**Usage:**
```bash
python scripts/generate_report.py --analysis results/analysis.json --eval eval_results.json --output results/report.md
```

## Output Files

All analysis outputs are saved to the `results/` directory:

```
results/
├── analysis.json          # Detailed metrics
├── report.md              # Comprehensive report
└── plots/
    ├── memory_growth.png
    ├── agreement_rate.png
    ├── cumulative_cost.png
    ├── action_distribution.png
    └── cost_comparison.png
```

## Cost Savings Analysis

The evaluation script compares three modes:
1. **Student-only**: Fast, low-cost decisions (no expert, no memory)
2. **Student + Memory + Expert**: Hybrid system (current approach)
3. **Expert-only**: High-fidelity decisions for all messages

The cost comparison shows:
- Absolute cost savings
- Percentage savings vs Expert-only baseline
- Cost per mode breakdown

## Example Workflow

```bash
# Step 1: Run moderation loop (generates logs)
python scripts/run_loop.py --config configs/default.yaml

# Step 2: Run evaluation (compares modes, includes costs)
python scripts/eval_compare.py --config configs/default.yaml --output eval_results.json

# Step 3: Analyze logs
python scripts/analyze_results.py --log logs/run_log.jsonl --output results/analysis.json

# Step 4: Generate visualizations
python scripts/plot_results.py --log logs/run_log.jsonl --eval eval_results.json

# Step 5: Generate report
python scripts/generate_report.py --analysis results/analysis.json --eval eval_results.json

# View results
cat results/report.md
open results/plots/*.png  # On Mac
```

## Interpreting Results

### Agreement Rate
- Higher is better (Student matches Expert more often)
- Should improve over time as memory grows
- Final agreement rate shows learning effectiveness

### Memory Growth
- Shows how many corrections were needed
- Steeper growth = more disagreements early on
- Should plateau as Student learns

### Cost Savings
- Compare hybrid system vs Expert-only
- Target: 50-80% cost savings (as mentioned in proposal)
- Actual savings depend on disagreement rate

### Action Distribution
- Shows which moderation actions are most common
- Helps understand moderation patterns
- Can identify if certain actions are over/under-used

