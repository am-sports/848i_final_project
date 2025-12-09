# Quick Start Guide

## What This Project Does

This is an **AI Agents for Twitch Chat Moderation** system that uses a hierarchical learning approach:

1. **Student Agent** (small, fast model) makes quick moderation decisions
2. **Expert Agent** (large, sophisticated model) audits those decisions
3. When they disagree, the Expert's reasoning is saved to **memory**
4. The Student learns from memory to improve over time
5. **Actions are executed** (warn, ban, timeout users) and **state is tracked**

The goal: Get expert-level moderation quality at a fraction of the cost by having the small model learn from the large one.

---

## Prerequisites

- Python 3.10 or higher
- Together.ai API key (get one at https://together.ai)

---

## Step-by-Step Setup

### 1. Install Dependencies

```bash
# Create virtual environment (recommended)
python -m venv .venv

# Activate it
# On Mac/Linux:
source .venv/bin/activate
# On Windows:
# .venv\Scripts\activate

# Install packages
pip3 install -r requirements.txt
```

### 2. Set Up API Key

```bash
# Set your Together.ai API key
export TOGETHER_API_KEY="your-api-key-here"
```

Or create a `.env` file:
```bash
echo "TOGETHER_API_KEY=your-api-key-here" > .env
```

### 3. Test Your Setup

```bash
# Quick API test (2 calls)
python3 scripts/test_api.py

# Full agent test (uses actual moderation logic)
python3 scripts/test_agents.py
```

If both tests pass, you're ready to go!

---

## Running the System

### Basic Run (Moderation Loop)

```bash
python scripts/run_loop.py --config configs/default.yaml
```

**What this does:**
- Processes synthetic Twitch comments
- Student proposes moderation plans
- Expert audits and corrects when needed
- Actions are executed (bans, warnings, etc.)
- Memory grows when Student and Expert disagree
- Shows a table of decisions and costs

**Output:**
- Terminal table showing all decisions
- Log file: `logs/run_log.jsonl`
- User state: `data/user_state.json`
- Cost summary at the end

### View User Statistics

```bash
python scripts/view_state.py --state data/user_state.json
```

Shows ban counts, warnings, timeouts for all users.

---

## Full Analysis Workflow

### Step 1: Run Evaluation Comparison

```bash
python scripts/eval_compare.py --config configs/default.yaml --output eval_results.json
```

**What this does:**
- Compares 3 modes: Student-only, Student+Memory, Expert-only
- Tracks costs for each mode
- Calculates cost savings
- Saves results to `eval_results.json`

### Step 2: Analyze Results

```bash
python scripts/analyze_results.py --log logs/run_log.jsonl --output results/analysis.json
```

**What this does:**
- Computes agreement rates
- Memory growth statistics
- Cost analysis
- Action distributions
- Displays summary table

### Step 3: Generate Plots

```bash
python scripts/plot_results.py --log logs/run_log.jsonl --eval eval_results.json --output results/plots
```

**What this generates:**
- `memory_growth.png` - Memory size over time
- `agreement_rate.png` - Agreement rate improvement
- `cumulative_cost.png` - Cost accumulation
- `action_distribution.png` - Action type breakdown
- `cost_comparison.png` - Cost comparison across modes

### Step 4: Generate Report

```bash
python scripts/generate_report.py --analysis results/analysis.json --eval eval_results.json --output results/report.md
```

Creates a comprehensive markdown report with all findings.

---

## Configuration

Edit `configs/default.yaml` to customize:

```yaml
student:
  backend: "together"    # together | hf | openai | heuristic
  model: "Qwen/Qwen2.5-7B-Instruct-Turbo"
  max_tokens: 256
  temperature: 0.4

expert:
  backend: "together"
  model: "meta-llama/Llama-3.3-70B-Instruct-Turbo"
  max_tokens: 512
  temperature: 0.2

loop:
  max_messages: 50       # Number of comments to process
  audit_every: 1         # How often to show table
  state_path: "data/user_state.json"

memory:
  backend: "tfidf"       # tfidf | sbert
  top_k: 3               # Number of memories to retrieve
```

---

## Common Commands

```bash
# Test API connection
python scripts/test_api.py

# Test agents
python scripts/test_agents.py

# Run moderation loop
python scripts/run_loop.py --config configs/default.yaml

# View user state
python scripts/view_state.py

# Run full evaluation
python scripts/eval_compare.py --config configs/default.yaml

# Analyze results
python scripts/analyze_results.py --log logs/run_log.jsonl

# Generate plots
python scripts/plot_results.py --log logs/run_log.jsonl --eval eval_results.json

# Generate report
python scripts/generate_report.py --analysis results/analysis.json --eval eval_results.json

# Generate more synthetic data
python scripts/generate_data.py --num 400 --output data/synthetic_comments.json
```

---

## Understanding the Output

### Moderation Loop Output

The terminal shows a table with:
- **User**: User ID
- **Comment**: The comment text
- **Student Plan**: What Student decided
- **Expert Plan**: What Expert decided
- **Actions Executed**: What actually happened (e.g., "User banned")
- **Memory Added**: Whether this disagreement was saved to memory

At the end:
- Final memory size
- User statistics (bans, warnings, etc.)
- Cost summary (API calls, tokens, total cost)

### Analysis Output

The analysis script shows:
- Agreement rates
- Memory growth
- Cost breakdown
- Action distribution

### Plots

Visualizations show:
- How memory grows over time
- How agreement rate improves
- Cost accumulation
- Which actions are most common
- Cost comparison across modes

---

## Troubleshooting

### "TOGETHER_API_KEY not set"
```bash
export TOGETHER_API_KEY="your-key-here"
```

### "No module named 'rich'"
```bash
pip install -r requirements.txt
```

### "Log file not found"
Run the moderation loop first:
```bash
python scripts/run_loop.py --config configs/default.yaml
```

### Want to use local models instead?
Edit `configs/default.yaml`:
```yaml
student:
  backend: "hf"  # Uses local Hugging Face models
  model: "gpt2"
```

---

## Project Structure

```
.
├── configs/              # Configuration files
├── data/                 # Synthetic comments, state files
├── logs/                 # Log files from runs
├── results/              # Analysis results, plots, reports
├── scripts/              # All executable scripts
│   ├── test_api.py      # Test API connection
│   ├── test_agents.py   # Test agents
│   ├── run_loop.py      # Main moderation loop
│   ├── eval_compare.py  # Evaluation comparison
│   ├── analyze_results.py  # Analyze logs
│   ├── plot_results.py  # Generate plots
│   └── generate_report.py  # Generate report
└── src/                  # Source code
    ├── agents/          # Student and Expert agents
    ├── actions/         # Action execution
    ├── memory/          # Memory system
    ├── state/           # User state tracking
    ├── utils/           # Cost tracking
    └── pipeline/        # Main loop
```

---

## Next Steps

1. **Run the basic loop** to see it in action
2. **Check the results** in `logs/run_log.jsonl`
3. **View user state** to see ban counts
4. **Run evaluation** to see cost savings
5. **Generate plots** to visualize performance
6. **Read the report** for comprehensive analysis

For more details, see:
- `README.md` - Full documentation
- `ANALYSIS_GUIDE.md` - Analysis tools guide
- `WHAT_IT_DOES.md` - What's implemented vs missing

