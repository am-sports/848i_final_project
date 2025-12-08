from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional


@dataclass
class ModerationRequest:
    comment: str
    meta: Dict[str, object]
    persona: str
    retrieved: Optional[List[Dict[str, str]]] = None


@dataclass
class ModerationOutput:
    reasoning: str
    plan: str
    actions: List[str]
    safety_level: str

