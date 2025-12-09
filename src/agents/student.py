from __future__ import annotations

import os
from typing import Dict, List, Optional

from .base import ModerationOutput, ModerationRequest


class StudentAgent:
    """
    Fast, low-cost agent. Defaults to heuristic.
    Supports local Hugging Face models (no API key) via backend="hf".
    Can optionally call OpenAI if backend="openai" and OPENAI_API_KEY is set.
    Supports Together.ai if backend="together" and TOGETHER_API_KEY is set.
    """

    def __init__(self, config: Dict, memory_client: Optional[object] = None, cost_tracker=None):
        self.config = config
        self.memory = memory_client
        self.cost_tracker = cost_tracker
        self._hf_pipeline = None
        self._client = None
        self._backend_type = None

        backend = self.config.get("backend", "heuristic")
        if backend == "together" and os.getenv("TOGETHER_API_KEY"):
            try:
                from openai import OpenAI

                # Together.ai uses OpenAI-compatible API
                self._client = OpenAI(
                    api_key=os.getenv("TOGETHER_API_KEY"),
                    base_url="https://api.together.xyz/v1",
                )
                self._backend_type = "together"
            except Exception:
                self._client = None
                self._backend_type = None
        elif backend == "openai" and os.getenv("OPENAI_API_KEY"):
            try:
                from openai import OpenAI

                self._client = OpenAI()
                self._backend_type = "openai"
            except Exception:
                self._client = None
                self._backend_type = None
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

        system_prompt = (
            "You are a fast moderation assistant for Twitch chat. "
            "Given a comment and any retrieved prior cases, propose a brief reasoning and a concise action plan. "
            "Actions can include warn_user, delete_comment, timeout_user_10m, ban_user, reply(message), "
            "or let_comment_stand. Always respond as valid JSON with keys: reasoning, plan (string), actions (array), safety_level (low|medium|high)."
        )
        
        user_prompt = (
            f"Retrieved cases:\n{retrieved_text}\n\n"
            f"Incoming comment: {req.comment}\n"
            f"Meta: {req.meta}\n"
            "Respond as JSON with keys reasoning, plan (string), actions (array), safety_level (low|medium|high)."
        )

        try:
            # Together.ai and OpenAI use the same chat completion format
            response = self._client.chat.completions.create(
                model=self.config.get("model", "Qwen/Qwen2.5-7B-Instruct-Turbo"),
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                max_tokens=self.config.get("max_tokens", 256),
                temperature=self.config.get("temperature", 0.4),
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
            
            # Try to extract JSON from response
            import json
            import re
            
            # Try to find JSON in the response (handle nested braces)
            def extract_json(text: str) -> dict:
                # First try parsing the whole content
                try:
                    return json.loads(text)
                except:
                    pass
                
                # Find the first { and match braces
                start = text.find('{')
                if start == -1:
                    return {}
                
                brace_count = 0
                for i in range(start, len(text)):
                    if text[i] == '{':
                        brace_count += 1
                    elif text[i] == '}':
                        brace_count -= 1
                        if brace_count == 0:
                            try:
                                return json.loads(text[start:i+1])
                            except:
                                pass
                return {}
            
            data = extract_json(content)
            if not data:
                raise ValueError("Could not extract valid JSON from response")
            
            return ModerationOutput(
                reasoning=data.get("reasoning", ""),
                plan=data.get("plan", ""),
                actions=data.get("actions", []),
                safety_level=data.get("safety_level", "medium"),
            )
        except Exception as e:
            return ModerationOutput(
                reasoning=f"LLM response unparsable: {str(e)}; using fallback.",
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
        if backend in ["together", "openai"] and self._client:
            return self._llm_policy(req)
        if backend == "hf":
            return self._hf_policy(req)
        return self._heuristic_policy(req)

