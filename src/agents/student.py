from __future__ import annotations

import os
from typing import Dict, List, Optional

from .base import ModerationOutput, ModerationRequest


class StudentAgent:
    """
    Fast, low-cost agent. Defaults to heuristic.
    Supports local Hugging Face models (no API key) via backend="hf".
    Can optionally call OpenAI if backend="openai" and OPENAI_API_KEY is set.
    """

    def __init__(self, config: Dict, memory_client: Optional[object] = None):
        self.config = config
        self.memory = memory_client
        self._hf_pipeline = None
        self._client = None

        backend = self.config.get("backend", "heuristic")
        if backend == "openai" and os.getenv("OPENAI_API_KEY"):
            try:
                from openai import OpenAI

                self._client = OpenAI()
            except Exception:
                self._client = None
        elif backend == "hf":
            try:
                from transformers import pipeline

                model_name = self.config.get("model", "gpt2")
                self._hf_pipeline = pipeline(
                    "text-generation",
                    model=model_name,
                    device_map="auto" if self.config.get("device_map_auto", True) else None,
                )
            except Exception:
                self._hf_pipeline = None

    def _heuristic_policy(self, req: ModerationRequest) -> ModerationOutput:
        comment = req.comment.lower()
        strikes = int(req.meta.get("strikes", 0))

        if any(token in comment for token in ["kys", "kill yourself", "hate"]) or strikes >= 3:
            plan = "timeout_user_10m + warn_user + delete_comment"
            safety = "high"
        elif any(token in comment for token in ["spam", "http://", "https://", "follow me", "free coins"]):
            plan = "delete_comment + warn_user"
            safety = "medium"
        elif any(token in comment for token in ["suck", "trash", "you all", "mods sleeping"]):
            plan = "warn_user + let_comment_stand"
            safety = "medium"
        else:
            plan = "let_comment_stand + maybe_reply_supportively"
            safety = "low"

        reasoning = "Heuristic student policy based on toxicity/spam keywords and strike count."
        actions = plan.split(" + ")
        return ModerationOutput(reasoning=reasoning, plan=plan, actions=actions, safety_level=safety)

    def _llm_policy(self, req: ModerationRequest) -> ModerationOutput:
        retrieved_text = ""
        if req.retrieved:
            snippets = [
                f"State: {r.get('state')}\nReasoning: {r.get('reasoning')}\nPlan: {r.get('plan')}"
                for r in req.retrieved
            ]
            retrieved_text = "\n\n".join(snippets[: self.config.get("max_context_memories", 4)])

        prompt = (
            "You are a fast moderation assistant for Twitch chat. "
            "Given a comment and any retrieved prior cases, propose a brief reasoning and a concise action plan. "
            "Actions can include warn_user, delete_comment, timeout_user_10m, ban_user, reply(message), "
            "or let_comment_stand.\n\n"
            f"Retrieved cases:\n{retrieved_text}\n\n"
            f"Incoming comment: {req.comment}\n"
            f"Meta: {req.meta}\n"
            "Respond as JSON with keys reasoning, plan (string), actions (array), safety_level (low|medium|high)."
        )
        resp = self._client.responses.create(
            model=self.config.get("model", "gpt-3.5-turbo"),
            input=prompt,
            max_output_tokens=self.config.get("max_tokens", 256),
            temperature=self.config.get("temperature", 0.4),
        )
        content = resp.output[0].content[0].text  # type: ignore
        # Fallback parsing
        try:
            import json

            data = json.loads(content)
            return ModerationOutput(
                reasoning=data.get("reasoning", ""),
                plan=data.get("plan", ""),
                actions=data.get("actions", []),
                safety_level=data.get("safety_level", "medium"),
            )
        except Exception:
            return ModerationOutput(
                reasoning="LLM response unparsable; using fallback.",
                plan="warn_user",
                actions=["warn_user"],
                safety_level="medium",
            )

    def _hf_policy(self, req: ModerationRequest) -> ModerationOutput:
        if not self._hf_pipeline:
            return self._heuristic_policy(req)

        retrieved_text = ""
        if req.retrieved:
            snippets = [
                f"State: {r.get('state')}\nReasoning: {r.get('reasoning')}\nPlan: {r.get('plan')}"
                for r in req.retrieved
            ]
            retrieved_text = "\n\n".join(snippets[: self.config.get("max_context_memories", 4)])

        prompt = (
            "You are a fast moderation assistant for Twitch chat. "
            "Given the comment and retrieved cases, propose brief reasoning and a concise action plan. "
            "Actions can include warn_user, delete_comment, timeout_user_10m, ban_user, reply(message), "
            "let_comment_stand. Respond in JSON with keys reasoning, plan, actions (array), safety_level.\n\n"
            f"Retrieved cases:\n{retrieved_text}\n\n"
            f"Incoming comment: {req.comment}\n"
            f"Meta: {req.meta}\n"
        )
        try:
            outputs = self._hf_pipeline(
                prompt,
                max_new_tokens=self.config.get("max_tokens", 128),
                do_sample=True,
                temperature=self.config.get("temperature", 0.7),
                num_return_sequences=1,
            )
            text = outputs[0]["generated_text"]
        except Exception:
            return self._heuristic_policy(req)

        # Simple parse: find braces and attempt JSON load
        import json

        def extract_json(s: str) -> Dict:
            start = s.find("{")
            end = s.rfind("}")
            if start != -1 and end != -1 and end > start:
                try:
                    return json.loads(s[start : end + 1])
                except Exception:
                    return {}
            return {}

        data = extract_json(text)
        if not data:
            return ModerationOutput(
                reasoning="HF response unparsable; using fallback.",
                plan="warn_user",
                actions=["warn_user"],
                safety_level="medium",
            )

        return ModerationOutput(
            reasoning=data.get("reasoning", "No reasoning"),
            plan=data.get("plan", "warn_user"),
            actions=data.get("actions", ["warn_user"]),
            safety_level=data.get("safety_level", "medium"),
        )

    def moderate(self, req: ModerationRequest) -> ModerationOutput:
        backend = self.config.get("backend", "heuristic")
        if backend == "openai" and self._client:
            return self._llm_policy(req)
        if backend == "hf":
            return self._hf_policy(req)
        return self._heuristic_policy(req)

