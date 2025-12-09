from __future__ import annotations

import json
import os
from typing import Dict

from .base import ExpertDecision, ModerationOutput, ModerationRequest


class ExpertAgent:
    """
    High-fidelity moderator using Together.ai LLM.
    First decides if Student's plan is correct, then produces own plan if disagreeing.
    """

    def __init__(self, config: Dict, cost_tracker=None):
        self.config = config
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

    def review_student_plan(self, req: ModerationRequest, student_plan: str, student_reasoning: str) -> ExpertDecision:
        """
        First step: Review Student's plan and decide if it's correct.
        Only sees state and comment, NOT the student's plan details.
        """
        # Format state for prompt
        state_text = json.dumps(req.state, indent=2)

        system_prompt = (
            "You are the authoritative expert moderator for a Twitch streamer. "
            "You will review a Student agent's proposed action plan. "
            "You will be given the user's state (their history) and the current comment. "
            "You must decide if the Student's plan is appropriate. "
            "You MUST respond with valid JSON only, with these exact keys: agrees, reasoning, plan, actions, safety_level. "
            "If you agree (agrees=true), set reasoning, plan, actions, and safety_level to null. "
            "If you disagree (agrees=false), you must provide your own reasoning, plan, actions, and safety_level. "
            "Actions can include: warn_user, delete_comment, timeout_user_5m, timeout_user_10m, ban_user, "
            "reply(message), log_incident, let_comment_stand. "
            "The 'plan' should be a string describing the action plan. "
            "The 'actions' should be an array of action strings. "
            "The 'safety_level' should be one of: low, medium, high."
        )

        user_prompt = (
            f"User State (history and context):\n{state_text}\n\n"
            f"Current Comment: {req.comment}\n\n"
            f"Student's Proposed Plan: {student_plan}\n"
            f"Student's Reasoning: {student_reasoning}\n\n"
            "Do you agree with the Student's plan? Respond with JSON only (no other text):\n"
            "If you AGREE:\n"
            "{\n"
            '  "agrees": true,\n'
            '  "reasoning": null,\n'
            '  "plan": null,\n'
            '  "actions": null,\n'
            '  "safety_level": null\n'
            "}\n\n"
            "If you DISAGREE:\n"
            "{\n"
            '  "agrees": false,\n'
            '  "reasoning": "your reasoning here",\n'
            '  "plan": "your action plan description",\n'
            '  "actions": ["action1", "action2"],\n'
            '  "safety_level": "low|medium|high"\n'
            "}"
        )

        try:
            response = self._client.chat.completions.create(
                model=self.config.get("model", "meta-llama/Llama-3.3-70B-Instruct-Turbo"),
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                max_tokens=self.config.get("max_tokens", 512),
                temperature=self.config.get("temperature", 0.2),
                response_format={"type": "json_object"},  # Force JSON response
            )
            content = response.choices[0].message.content

            # Track costs if tracker is available
            if self.cost_tracker and hasattr(response, 'usage'):
                usage = response.usage
                self.cost_tracker.record_call(
                    model=self.config.get("model", "meta-llama/Llama-3.3-70B-Instruct-Turbo"),
                    prompt_tokens=usage.prompt_tokens if hasattr(usage, 'prompt_tokens') else 0,
                    completion_tokens=usage.completion_tokens if hasattr(usage, 'completion_tokens') else 0,
                    total_tokens=usage.total_tokens if hasattr(usage, 'total_tokens') else 0,
                )

            # Parse JSON response
            data = json.loads(content)

            return ExpertDecision(
                agrees=data.get("agrees", False),
                reasoning=data.get("reasoning"),
                plan=data.get("plan"),
                actions=data.get("actions"),
                safety_level=data.get("safety_level"),
            )
        except json.JSONDecodeError as e:
            raise RuntimeError(f"LLM returned invalid JSON: {str(e)}")
        except Exception as e:
            raise RuntimeError(f"Expert review failed: {str(e)}")
