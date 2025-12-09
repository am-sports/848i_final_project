from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional


@dataclass
class ModerationRequest:
    comment: str
    state: Dict  # User state (without user_id)
    meta: Dict[str, object]
    persona: str
    retrieved: Optional[List[Dict[str, str]]] = None


@dataclass
class ModerationOutput:
    reasoning: str
    plan: str
    actions: List[str]
    safety_level: str


@dataclass
class ExpertDecision:
    """Expert's decision on whether to agree or disagree with Student."""
    agrees: bool
    reasoning: Optional[str] = None  # Only if disagrees
    plan: Optional[str] = None  # Only if disagrees
    actions: Optional[List[str]] = None  # Only if disagrees
    safety_level: Optional[str] = None  # Only if disagrees
