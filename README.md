AI Agents for Twitch Chat Moderation
====================================

This repo is a runnable Python prototype for the proposal “AI Agents for Twitch Chat Moderation.” It includes:
- A Student agent (small, fast) and an Expert agent (slow, higher fidelity) with an agreement/disagreement loop.
- A retrieval-backed long-term memory storing `(state, reasoning, plan)` triples.
- Synthetic Twitch-like comments and personas for quick experiments.
- CLI scripts to generate data and run the moderation loop with memory expansion.

Quickstart
----------
1) Install dependencies (Python 3.10+ recommended):
```
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

2) Set up Together.ai API key (required for default config):
```
export TOGETHER_API_KEY="your-together-api-key-here"
```
Or create a `.env` file:
```
echo "TOGETHER_API_KEY=your-together-api-key-here" > .env
```

The default config uses Together.ai models:
- Student: `Qwen/Qwen2.5-7B-Instruct-Turbo` (32768 context window)
- Expert: `meta-llama/Llama-3.3-70B-Instruct-Turbo` (131072 context window)

3) Test your API key (recommended):
```
# Quick API test (2 calls)
python scripts/test_api.py

# Full agent test (uses actual moderation logic)
python scripts/test_agents.py
```

4) (Optional) For local testing without API keys, set `backend: hf` in `configs/default.yaml` to use local Hugging Face models. Heuristic fallbacks are used if the model cannot load.

5) (Optional) If you want OpenAI instead, set `backend: openai` in `configs/default.yaml` and add your key:
```
export OPENAI_API_KEY="sk-..."
```

6) Run the moderation loop with default config and synthetic data:
```
python scripts/run_loop.py --config configs/default.yaml

Mac - python3 -m scripts.run_loop --config configs/default.yaml
```
The script prints per-message reasoning, Student vs. Expert decisions, **executes actions** (warns, bans, timeouts), and updates the in-memory vector store on disagreements. User state (ban counts, etc.) is tracked and saved.

7) View user state statistics:
```
python scripts/view_state.py --state data/user_state.json
```
Shows ban counts, warnings, timeouts, and other action statistics for all users.

8) Regenerate synthetic comments/personas:
```
python scripts/generate_data.py --output data/synthetic_comments.json
```

Model Backends
--------------
- Default: Together.ai API (`backend: together`, requires `TOGETHER_API_KEY`):
  - Student: `Qwen/Qwen2.5-7B-Instruct-Turbo` (32768 context window)
  - Expert: `meta-llama/Llama-3.3-70B-Instruct-Turbo` (131072 context window)
- Optional: local Hugging Face text-generation pipeline (`backend: hf`, keyless, uses `gpt2` by default).
- Optional embeddings: set `memory.backend: sbert` to use `sentence-transformers/all-MiniLM-L6-v2` locally (downloads the model); otherwise TF-IDF.
- Fallback: heuristic policy if the model cannot be loaded or API key is missing.
- Optional: OpenAI (`backend: openai`, requires `OPENAI_API_KEY`).

Project Layout
--------------
- `configs/` — YAML configs for models, memory, and loop parameters.
- `data/` — Synthetic comments, personas, and saved state files.
- `scripts/` — Entry points for data generation, running the loop, and viewing state.
- `src/`
  - `config.py` — Pydantic settings and config loading.
  - `memory/vector_store.py` — TF-IDF or SBERT kNN memory with optional persistence.
  - `agents/` — Student and Expert agents with interchangeable policy backends.
  - `actions/executor.py` — Executes moderation actions and updates user state.
  - `state/user_state.py` — Tracks user state (ban counts, warnings, timeouts, etc.).
  - `pipeline/moderation_loop.py` — Implements the iterative Student→Expert→Memory→Action workflow.

What's Implemented
------------------
- Retrieval-augmented Student agent that pulls top-k memories before proposing a plan.
- Expert audit that can run either a heuristic policy or an LLM call; disagreements are stored as new memories.
- **Action execution system** that executes moderation actions (warn, ban, timeout, delete, reply) and tracks user state.
- **User state tracking** with ban counts, warning counts, timeout counts, etc. Persists to JSON file.
- **Cost tracking** for API calls with Together.ai pricing calculations.
- **Results analysis** script that computes metrics (agreement rates, memory growth, costs).
- **Visualization** scripts that generate plots (memory growth, agreement rates, cost comparison, action distribution).
- **Report generation** that creates comprehensive markdown reports.
- Vector-store memory (TF-IDF or SBERT) with semantic retrieval over state text; optional persistence.
- Synthetic personas and comments to simulate diverse moderation styles.
- Rich terminal logging for traceability; JSONL log output with action results and costs.

Testing and Evaluation
----------------------
- Run moderation loop (default HF + TF-IDF):
```
python scripts/run_loop.py --config configs/default.yaml
```
- Enable SBERT retrieval (local, downloads model):
```
memory:
  backend: "sbert"
  embed_model: "sentence-transformers/all-MiniLM-L6-v2"
```
- Persist memory across runs (no external DB needed):
```
memory:
  persistence_path: "data/memory_snapshot.json"
```
- Compare regimes (Student-only vs Student+Memory vs Expert-only agreement rate + costs):
```
python scripts/eval_compare.py --config configs/default.yaml > eval_results.json
```

- Analyze results and generate metrics:
```
python scripts/analyze_results.py --log logs/run_log.jsonl --output results/analysis.json
```

- Generate visualizations (plots):
```
python scripts/plot_results.py --log logs/run_log.jsonl --eval eval_results.json --output results/plots
```

- Generate comprehensive report:
```
python scripts/generate_report.py --analysis results/analysis.json --eval eval_results.json --output results/report.md
```

Analysis and Visualization
--------------------------
The project includes comprehensive analysis tools:

1. **Cost Tracking**: Automatically tracks API calls and calculates costs based on Together.ai pricing
2. **Results Analysis**: Computes agreement rates, memory growth, action distributions, and more
3. **Visualizations**: Generates plots for:
   - Memory growth over time
   - Agreement rate improvement
   - Cumulative cost tracking
   - Action distribution
   - Cost comparison (Student-only vs Hybrid vs Expert-only)
4. **Report Generation**: Creates markdown reports summarizing all findings

All analysis scripts save results to the `results/` directory.

License
-------
MIT (adjust as needed).

