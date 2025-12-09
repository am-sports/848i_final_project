from __future__ import annotations

import json
import os
from typing import Dict, List, Optional

from .base import ModerationOutput, ModerationRequest


class StudentAgent:
    """
    Fast, low-cost agent using Together.ai LLM.
    Receives user state and top-5 nearest neighbors, proposes action plan.
    """

    def __init__(self, config: Dict, memory_client: Optional[object] = None, cost_tracker=None):
        self.config = config
        self.memory = memory_client
        self.cost_tracker = cost_tracker

        # Initialize Together.ai client
        api_key = os.getenv("TOGETHER_API_KEY")
        if not api_key:
            raise ValueError("TOGETHER_API_KEY environment variable is required")

        try:
            from openai import OpenAI
            self._client = OpenAI(
                api_key=api_key,
                base_url="https://api.together.xyz/v1",
            )
        except Exception as e:
            raise RuntimeError(f"Failed to initialize Together.ai client: {e}")

    def moderate(self, req: ModerationRequest, use_state: bool = True, use_retrieval: bool = True) -> ModerationOutput:
        """Moderate a comment using the LLM with state and retrieved cases."""
        # Format retrieved cases as demonstrations/examples
        examples_text = ""
        if use_retrieval and req.retrieved:
            examples = []
            for r in req.retrieved[:5]:  # Top-5
                example = (
                    f"Example Case:\n"
                    f"  Comment: {r.get('comment', 'N/A')}\n"
                    f"  User State: {r.get('state_metrics', 'N/A')}\n"
                    f"  Reasoning: {r.get('reasoning', 'N/A')}\n"
                    f"  Action Plan: {r.get('plan', 'N/A')}\n"
                )
                examples.append(example)
            examples_text = "\n".join(examples)
        else:
            examples_text = "No similar cases found."

        # Format state for prompt
        state_text = json.dumps(req.state, indent=2) if use_state else "{}"

        system_prompt = (
            "You are a fast moderation assistant for Twitch chat. "
            "You will be given a user's state (their history: ban count, warning count, etc.), "
            "the current comment, and similar past cases as examples. "
            "Study the examples to understand how similar situations were handled. "
            "Propose a brief reasoning and a concise action plan. "
            "Actions can include: warn_user, delete_comment, timeout_user_5m, timeout_user_10m, ban_user, "
            "reply(message), log_incident, let_comment_stand. "
            "You MUST respond with valid JSON only, with these exact keys: reasoning, plan, actions, safety_level. "
            "The 'plan' should be a string describing the action plan. "
            "The 'actions' should be an array of action strings. "
            "The 'safety_level' should be one of: low, medium, high."
        )

        if use_state and use_retrieval:
            user_prompt = (
                f"User State (history and context):\n{state_text}\n\n"
                f"Current Comment: {req.comment}\n\n"
                f"Similar Past Cases (examples to learn from):\n{examples_text}\n\n"
                "Respond with JSON only (no other text):\n"
                "{\n"
                '  "reasoning": "your reasoning here",\n'
                '  "plan": "your action plan description",\n'
                '  "actions": ["action1", "action2"],\n'
                '  "safety_level": "low|medium|high"\n'
                "}"
            )
        elif use_state:
            user_prompt = (
                f"User State (history and context):\n{state_text}\n\n"
                f"Current Comment: {req.comment}\n\n"
                "Respond with JSON only (no other text):\n"
                "{\n"
                '  "reasoning": "your reasoning here",\n'
                '  "plan": "your action plan description",\n'
                '  "actions": ["action1", "action2"],\n'
                '  "safety_level": "low|medium|high"\n'
                "}"
            )
        else:
            # Baseline mode - no state, no retrieval
            user_prompt = (
                f"Current Comment: {req.comment}\n\n"
                "Respond with JSON only (no other text):\n"
                "{\n"
                '  "reasoning": "your reasoning here",\n'
                '  "plan": "your action plan description",\n'
                '  "actions": ["action1", "action2"],\n'
                '  "safety_level": "low|medium|high"\n'
                "}"
            )

        try:
            response = self._client.chat.completions.create(
                model=self.config.get("model", "Qwen/Qwen2.5-7B-Instruct-Turbo"),
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                max_tokens=self.config.get("max_tokens", 256),
                temperature=self.config.get("temperature", 0.4),
                response_format={"type": "json_object"},  # Force JSON response
            )
            content = response.choices[0].message.content

            # Track costs if tracker is available
            if self.cost_tracker and hasattr(response, 'usage'):
                usage = response.usage
                self.cost_tracker.record_call(
                    model=self.config.get("model", "Qwen/Qwen2.5-7B-Instruct-Turbo"),
                    prompt_tokens=usage.prompt_tokens if hasattr(usage, 'prompt_tokens') else 0,
                    completion_tokens=usage.completion_tokens if hasattr(usage, 'completion_tokens') else 0,
                    total_tokens=usage.total_tokens if hasattr(usage, 'total_tokens') else 0,
                )

            # Parse JSON response
            data = json.loads(content)

            return ModerationOutput(
                reasoning=data.get("reasoning", ""),
                plan=data.get("plan", ""),
                actions=data.get("actions", []),
                safety_level=data.get("safety_level", "medium"),
            )
        except json.JSONDecodeError as e:
            raise RuntimeError(f"LLM returned invalid JSON: {str(e)}")
        except Exception as e:
            raise RuntimeError(f"LLM moderation failed: {str(e)}")
