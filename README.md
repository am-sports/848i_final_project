AI Agents for Twitch Chat Moderation
====================================

A simple, LLM-based moderation system using two agents: a Student agent (fast, low-cost) and an Expert agent (high-fidelity). The system learns from disagreements by storing Expert overrides in a memory database.

Architecture
-----------

**Simple Flow:**
1. For each comment, the system updates the user's state (ban count, warning count, follower count, viewer count, current topic, etc.)
2. Student agent receives:
   - User state (history metrics, NO user ID)
   - Current comment
   - Top-5 nearest neighbors from memory database
3. Student proposes an action plan and reasoning
4. Expert agent reviews Student's plan:
   - Sees only the state and comment (not Student's full reasoning)
   - Decides to "agree" or "disagree"
   - If disagrees, produces independent reasoning and action plan
5. If Expert disagrees, the case is stored in memory (keyed by state, not comment)
6. Actions are executed and user state is updated

**Key Features:**
- State-based memory: Cases are stored and retrieved by user state metrics (not user IDs or comments)
- JSON-only responses: Both agents use strict JSON formatting
- Together.ai only: Uses Together.ai LLM models exclusively
- No heuristics: Pure LLM-based decisions

Quickstart
----------

1) Install dependencies (Python 3.10+ recommended):
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

2) Set up Together.ai API key (required):
```bash
export TOGETHER_API_KEY="your-together-api-key-here"
```

3) Run the moderation loop:
```bash
python scripts/run_loop.py --config configs/default.yaml
```

The script processes comments, shows Student vs Expert decisions, executes actions, and stores Expert overrides in memory.

Project Layout
--------------

- `configs/` — YAML configs for models, memory, and loop parameters
- `data/` — Synthetic comments and saved state files
- `scripts/` — Entry points for running the loop and viewing state
- `src/`
  - `config.py` — Configuration loading
  - `memory/vector_store.py` — TF-IDF or SBERT vector store for state-based retrieval
  - `agents/` — Student and Expert LLM agents
  - `actions/executor.py` — Executes moderation actions and updates user state
  - `state/user_state.py` — Tracks user state (metrics only, no user IDs in memory)
  - `pipeline/moderation_loop.py` — Main moderation loop

Configuration
------------

Edit `configs/default.yaml`:

```yaml
student:
  model: "Qwen/Qwen2.5-7B-Instruct-Turbo"  # Fast, low-cost model
  max_tokens: 256
  temperature: 0.4

expert:
  model: "meta-llama/Llama-3.3-70B-Instruct-Turbo"  # High-fidelity model
  max_tokens: 512
  temperature: 0.2

memory:
  top_k: 5  # Top-5 nearest neighbors retrieved for Student
  backend: "tfidf"  # or "sbert" for semantic embeddings
```

User State
----------

User state includes (stored WITHOUT user ID):
- `ban_count`: Number of times user has been banned
- `warning_count`: Number of warnings issued
- `timeout_count`: Number of timeouts
- `deleted_comments`: Number of comments deleted
- `replies_sent`: Number of replies sent to user
- `follower_count`: User's follower count
- `viewer_count`: Current viewer count
- `current_topic`: Current stream topic/context
- `last_action`: Last action taken for this user

Memory Database
---------------

The memory database stores cases where Expert disagreed with Student:
- **Key**: User state (string representation of metrics)
- **Value**: Expert's reasoning and action plan
- **Retrieval**: Top-5 nearest neighbors by state similarity

Actions
-------

Available moderation actions:
- `warn_user`: Issue a warning
- `delete_comment`: Delete the comment
- `timeout_user_5m`: Timeout for 5 minutes
- `timeout_user_10m`: Timeout for 10 minutes
- `ban_user`: Ban the user
- `reply(message)`: Send a reply message
- `log_incident`: Log the incident
- `let_comment_stand`: Take no action

License
-------
MIT
