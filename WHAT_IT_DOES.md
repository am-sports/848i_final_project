# What the Code Does

## Architecture Overview

This is a simple, LLM-based moderation system with two agents:

1. **Student Agent** (fast, low-cost)
   - Receives user state, comment, and top-5 similar cases
   - Proposes action plan and reasoning
   - Uses `Qwen/Qwen2.5-7B-Instruct-Turbo`

2. **Expert Agent** (high-fidelity)
   - Reviews Student's plan (sees only state + comment)
   - Decides to "agree" or "disagree"
   - If disagrees, produces own reasoning and plan
   - Uses `meta-llama/Llama-3.3-70B-Instruct-Turbo`

## Workflow

For each comment:

1. **Update State**: User's state is updated with current metrics (ban count, warnings, follower count, viewer count, current topic, etc.)

2. **Retrieve Similar Cases**: Search memory database for top-5 nearest neighbors by state similarity

3. **Student Proposes**: Student receives state, comment, and similar cases, then proposes action plan

4. **Expert Reviews**: Expert sees only state and comment, decides if Student's plan is correct

5. **Execute Actions**: If Expert agrees, use Student's plan; if disagrees, use Expert's plan

6. **Store Override**: If Expert disagreed, store the case in memory (keyed by state, not comment)

## Key Design Decisions

- **State-based memory**: Cases stored by user state metrics (no user IDs or comments as keys)
- **JSON-only responses**: Strict JSON formatting enforced via `response_format`
- **Together.ai only**: No heuristics, no fallbacks, pure LLM
- **Simple flow**: Expert only sees state + comment when reviewing (not Student's full reasoning)

## User State

State includes (stored WITHOUT user ID):
- Action counts: bans, warnings, timeouts, deleted comments, replies
- Context: follower count, viewer count, current topic
- Last action taken

## Memory Database

- Stores: `(state, reasoning, plan)` triples
- Key: State string (e.g., "bans:2, warnings:1, timeouts:0, ...")
- Retrieval: Top-5 nearest neighbors by state similarity
- Only stores cases where Expert disagreed with Student

## Implementation Details

- **No heuristics**: All decisions made by LLMs
- **Strict JSON**: Both agents use `response_format={"type": "json_object"}`
- **State updates**: Happen before each moderation decision
- **Action execution**: Updates state after actions are taken
