# Quick Start Guide

## What This Project Does

This is a **simple LLM-based moderation system** with two agents that runs a three-phase experiment:

1. **Student Agent** (fast, low-cost) proposes moderation plans
2. **Expert Agent** (high-fidelity) reviews and corrects when needed
3. When Expert disagrees, the case is stored in memory (keyed by comment+state)
4. Student learns from similar past cases retrieved from memory
5. Actions are executed and user state is tracked

## Prerequisites

- Python 3.10 or higher
- Together.ai API key (get one at https://together.ai)
- At least 150 comments in `data/synthetic_comments.json`

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
pip install -r requirements.txt
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
# Quick API test
python scripts/test_api.py

# Full agent test
python scripts/test_agents.py
```

If both tests pass, you're ready to go!

## Running the Experiment

### Basic Run (Three-Phase Experiment)

```bash
python scripts/run_loop.py --config configs/default.yaml
```

**What this does:**

The system randomly shuffles comments and processes them in three phases:

#### Phase 1: Baseline (50 comments)
- Student model **without** state or retrieval
- Evaluates base performance of Student alone
- Shows agreement rate: how often Expert agrees with Student

#### Phase 2: Accumulation (50 comments)
- Full moderation loop **with** state and retrieval
- Builds memory database (stores Expert overrides)
- Accumulates user state history
- Users are randomly assigned IDs in range [1, 75] to build history

#### Phase 3: Evaluation (50 comments)
- Student **with** state and retrieval (learned from Phase 2)
- Compares Student vs Expert on accumulated state
- Measures improvement over baseline

**Output:**
- Three separate tables (one per phase)
- Final summary comparing all phases
- Log file: `logs/run_log.jsonl`
- User state: `data/user_state.json`
- Cost summary at the end

### Understanding the Results

The experiment is designed to answer: **Does the architecture (state + retrieval) help the small model match the big model?**

**Key Metrics to Compare:**

1. **Phase 1 Agreement Rate**: Baseline performance without help
   - Example: 84% means Expert agreed with Student 84% of the time

2. **Phase 3 Agreement Rate**: Performance with state + retrieval
   - Compare to Phase 1 to see if it improved

3. **Memory Size**: How many cases were learned in Phase 2
   - More cases = more learning opportunities

**Interpreting Results:**

- **If Phase 3 > Phase 1**: Architecture is helping! Student learned from examples.
- **If Phase 3 < Phase 1**: Architecture may not be helping yet, or:
  - Memory database too small (need more accumulation)
  - Phase 3 cases more difficult
  - Expert stricter with state context

### View User Statistics

```bash
python scripts/view_state.py --state data/user_state.json
```

Shows ban counts, warnings, timeouts for all users.

## How It Works

### Experiment Design

1. **Comments are randomly shuffled** before processing
2. **User IDs are randomly generated** in range [1, total_iterations/2]
   - For 150 iterations: users 1-75
   - Users are reused to build history across phases
3. **Three phases** test different configurations

### For Each Comment:

1. **State Update**: User's state is updated with current metrics:
   - Ban count, warning count, timeout count
   - Deleted comments, replies sent
   - Follower count, viewer count, current topic

2. **Memory Retrieval**: Search for top-5 nearest neighbors by **comment+state** similarity

3. **Student Proposes**: Student receives:
   - User state (metrics only, no user ID)
   - Current comment
   - Top-5 similar cases (as examples/demonstrations)
   - Proposes action plan and reasoning (JSON format)

4. **Expert Reviews**: Expert receives:
   - User state
   - Current comment
   - Student's plan and reasoning
   - Decides to "agree" or "disagree" (JSON format)
   - If disagrees, provides own reasoning and plan

5. **Execute**: Use Expert's plan if disagreed, otherwise Student's plan

6. **Store**: If Expert disagreed, store case in memory (keyed by **comment+state** string)

## Configuration

Edit `configs/default.yaml`:

```yaml
student:
  model: "Qwen/Qwen2.5-7B-Instruct-Turbo"  # Fast model
  max_tokens: 256
  temperature: 0.4

expert:
  model: "meta-llama/Llama-3.3-70B-Instruct-Turbo"  # High-fidelity model
  max_tokens: 512
  temperature: 0.2

memory:
  top_k: 5  # Top-5 nearest neighbors
  backend: "tfidf"  # or "sbert" for semantic embeddings

loop:
  max_messages: 50  # Number of comments per phase (total 150)
```

## Understanding the Output

### Experiment Output

The terminal shows:

1. **Phase 1 Table**: Baseline results (Student without help)
2. **Phase 2 Table**: Accumulation results (building memory)
3. **Phase 3 Table**: Evaluation results (Student with help)
4. **Final Summary**:
   - Phase 1 agreement rate
   - Phase 2 memory size
   - Phase 3 agreement rate
   - Comparison between phases

**Key Columns:**
- **User**: Randomly assigned user ID (reused across phases)
- **Comment**: The comment text
- **Student Plan**: What Student decided
- **Expert Decision**: "AGREES" or "DISAGREES"
- **Memory Added**: Whether this case was saved to memory (Phase 2 only)

## Common Commands

```bash
# Test API connection
python scripts/test_api.py

# Test agents
python scripts/test_agents.py

# Run three-phase experiment
python scripts/run_loop.py --config configs/default.yaml

# View user state
python scripts/view_state.py --state data/user_state.json
```

## Troubleshooting

### "TOGETHER_API_KEY not set"
```bash
export TOGETHER_API_KEY="your-key-here"
```
Or create `.env` file with the key.

### "Need at least 150 comments"
Make sure `data/synthetic_comments.json` has at least 150 comments (currently has 450).

### "No module named 'rich'"
```bash
pip install -r requirements.txt
```

### "LLM returned invalid JSON"
The models are configured to return JSON only. If this error occurs, check your API key and model availability.

## Project Structure

```
.
├── configs/              # Configuration files
├── data/                 # Synthetic comments (simple list), state files
├── logs/                 # Log files from runs
├── scripts/              # Executable scripts
│   ├── test_api.py      # Test API connection
│   ├── test_agents.py   # Test agents
│   └── run_loop.py      # Main three-phase experiment
└── src/                  # Source code
    ├── agents/          # Student and Expert agents
    ├── actions/         # Action execution
    ├── memory/          # Memory system (comment+state based)
    ├── state/           # User state tracking
    └── pipeline/        # Main loop
```

## Key Features

- **Three-phase experiment**: Baseline → Accumulation → Evaluation
- **Comment+state memory**: Cases stored by combined comment+state for semantic similarity
- **Random user assignment**: Users randomly assigned to build history
- **JSON-only responses**: Strict JSON formatting enforced
- **Together.ai only**: Pure LLM, no heuristics
- **Example-based learning**: Student sees similar cases as demonstrations

## Interpreting Results

After running the experiment, compare:

1. **Phase 1 vs Phase 3 Agreement Rates**
   - Higher in Phase 3 = architecture is helping
   - Lower in Phase 3 = may need more accumulation or different approach

2. **Memory Size**
   - More entries = more learning opportunities
   - Too few entries (< 10) may not provide enough signal

3. **Cost Efficiency**
   - Student handles most decisions at low cost
   - Expert only reviews (higher cost but only when needed)

For more details, see:
- `README.md` - Full documentation
- `WHAT_IT_DOES.md` - Architecture details
