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

2) No API key needed by default. The config uses local Hugging Face models (`gpt2`) for both Student and Expert. Heuristic fallbacks are used if the model cannot load.

3) (Optional) If you want OpenAI later, set `backend: openai` in `configs/default.yaml` and add your key:
```
cp .env.example .env
echo "OPENAI_API_KEY=sk-..." >> .env
```

4) Run the moderation loop with default config and synthetic data:
```
python scripts/run_loop.py --config configs/default.yaml

Mac - python3 -m scripts.run_loop --config configs/default.yaml
```
The script prints per-message reasoning, Student vs. Expert decisions, and updates the in-memory vector store on disagreements.

4) Regenerate synthetic comments/personas:
```
python scripts/generate_data.py --output data/synthetic_comments.json
```

Model Backends
--------------
- Default: local Hugging Face text-generation pipeline with `gpt2` (small, keyless).
- Optional embeddings: set `memory.backend: sbert` to use `sentence-transformers/all-MiniLM-L6-v2` locally (downloads the model); otherwise TF-IDF.
- Fallback: heuristic policy if the HF model cannot be loaded.
- Optional: OpenAI (`backend: openai`, requires `OPENAI_API_KEY`).

Project Layout
--------------
- `configs/` — YAML configs for models, memory, and loop parameters.
- `data/` — Synthetic comments and personas.
- `scripts/` — Entry points for data generation and running the loop.
- `src/`
  - `config.py` — Pydantic settings and config loading.
  - `memory/vector_store.py` — TF-IDF or SBERT kNN memory with optional persistence.
  - `agents/` — Student and Expert agents with interchangeable policy backends.
  - `pipeline/moderation_loop.py` — Implements the iterative Student→Expert→Memory workflow.

What’s Implemented
------------------
- Retrieval-augmented Student agent that pulls top-k memories before proposing a plan.
- Expert audit that can run either a heuristic policy or an LLM call; disagreements are stored as new memories.
- Vector-store memory (TF-IDF or SBERT) with semantic retrieval over state text; optional persistence.
- Synthetic personas and comments to simulate diverse moderation styles.
- Rich terminal logging for traceability; JSONL log output.

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
- Compare regimes (Student-only vs Student+Memory vs Expert-only agreement rate):
```
python scripts/eval_compare.py --config configs/default.yaml
```

Next Steps (if you want to extend)
----------------------------------
- Swap TF-IDF memory for a neural embedding DB (Chroma/FAISS + sentence-transformers).
- Add persistence for memory snapshots to disk and loading across runs.
- Implement real Twitch chat ingestion and action execution hooks.
- Add evaluation harness comparing Student-only vs. Student+Memory vs. Expert-only.

License
-------
MIT (adjust as needed).

