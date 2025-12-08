from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Optional

import yaml
from pydantic import BaseModel, Field


class MemoryConfig(BaseModel):
    top_k: int = 3
    min_similarity: float = 0.05
    backend: str = "tfidf"  # tfidf | sbert
    persistence_path: Path | None = None
    embed_model: str = "sentence-transformers/all-MiniLM-L6-v2"


class AgentConfig(BaseModel):
    backend: str = "hf"  # options: heuristic, hf, openai
    use_llm: bool = False  # legacy flag; kept for backward compatibility
    model: str = "gpt2"  # default lightweight HF model
    max_tokens: int = 256
    temperature: float = 0.4


class LoopConfig(BaseModel):
    max_messages: int = 50
    audit_every: int = 1


class AppConfig(BaseModel):
    seed: int = 42
    data_path: Path = Path("data/synthetic_comments.json")
    memory: MemoryConfig = Field(default_factory=MemoryConfig)
    student: AgentConfig = Field(default_factory=AgentConfig)
    expert: AgentConfig = Field(default_factory=AgentConfig)
    loop: LoopConfig = Field(default_factory=LoopConfig)

    @classmethod
    def from_yaml(cls, path: Path) -> "AppConfig":
        with path.open("r", encoding="utf-8") as f:
            payload = yaml.safe_load(f)
        return cls.model_validate(payload)

    def to_json(self) -> str:
        return json.dumps(self.model_dump(), indent=2)


def load_config(path: str | Path) -> AppConfig:
    path = Path(path)
    return AppConfig.from_yaml(path)

