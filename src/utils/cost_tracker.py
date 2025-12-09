from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict


@dataclass
class APICall:
    """Record of a single API call."""
    model: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    cost: float


class CostTracker:
    """
    Tracks API costs for Together.ai models.
    Pricing (as of 2024, approximate):
    - Qwen/Qwen2.5-7B-Instruct-Turbo: ~$0.0002 per 1K tokens (input + output)
    - meta-llama/Llama-3.3-70B-Instruct-Turbo: ~$0.0007 per 1K tokens (input + output)
    
    Note: These are estimates. Check Together.ai pricing for exact rates.
    """

    # Pricing per 1K tokens (input + output combined)
    PRICING = {
        "Qwen/Qwen2.5-7B-Instruct-Turbo": 0.0002,  # ~$0.20 per 1M tokens
        "meta-llama/Llama-3.3-70B-Instruct-Turbo": 0.0007,  # ~$0.70 per 1M tokens
        # Fallback pricing
        "default_student": 0.0002,
        "default_expert": 0.0007,
    }

    def __init__(self):
        self.calls: list[APICall] = []
        self._model_stats: Dict[str, Dict] = {}

    def record_call(
        self,
        model: str,
        prompt_tokens: int = 0,
        completion_tokens: int = 0,
        total_tokens: int | None = None,
    ) -> float:
        """Record an API call and return the cost."""
        if total_tokens is None:
            total_tokens = prompt_tokens + completion_tokens

        # Get pricing for model
        price_per_1k = self.PRICING.get(model)
        if price_per_1k is None:
            # Try to infer from model name
            if "7b" in model.lower() or "qwen" in model.lower():
                price_per_1k = self.PRICING["default_student"]
            elif "70b" in model.lower() or "llama" in model.lower():
                price_per_1k = self.PRICING["default_expert"]
            else:
                price_per_1k = self.PRICING["default_student"]  # conservative default

        cost = (total_tokens / 1000.0) * price_per_1k

        call = APICall(
            model=model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            cost=cost,
        )
        self.calls.append(call)

        # Update stats
        if model not in self._model_stats:
            self._model_stats[model] = {
                "calls": 0,
                "total_tokens": 0,
                "total_cost": 0.0,
            }
        self._model_stats[model]["calls"] += 1
        self._model_stats[model]["total_tokens"] += total_tokens
        self._model_stats[model]["total_cost"] += cost

        return cost

    def get_total_cost(self) -> float:
        """Get total cost across all calls."""
        return sum(call.cost for call in self.calls)

    def get_model_cost(self, model: str) -> float:
        """Get total cost for a specific model."""
        return sum(call.cost for call in self.calls if call.model == model)

    def get_stats(self) -> Dict:
        """Get summary statistics."""
        total_calls = len(self.calls)
        total_tokens = sum(call.total_tokens for call in self.calls)
        total_cost = self.get_total_cost()

        return {
            "total_calls": total_calls,
            "total_tokens": total_tokens,
            "total_cost": round(total_cost, 4),
            "avg_cost_per_call": round(total_cost / total_calls, 6) if total_calls > 0 else 0.0,
            "by_model": {
                model: {
                    "calls": stats["calls"],
                    "tokens": stats["total_tokens"],
                    "cost": round(stats["total_cost"], 4),
                }
                for model, stats in self._model_stats.items()
            },
        }

    def reset(self) -> None:
        """Reset all tracking."""
        self.calls.clear()
        self._model_stats.clear()

