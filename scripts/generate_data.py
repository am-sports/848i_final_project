from __future__ import annotations

import argparse
import json
import random
from pathlib import Path

PERSONAS = {
    "lenient_supportive": {
        "tone": "friendly, supportive, minimal intervention unless abusive",
        "examples": [
            ("yo stream was fire last night!!", {"strikes": 0}),
            ("sorry if that was rude earlier, just hyped", {"strikes": 1}),
        ],
    },
    "firm_professional": {
        "tone": "strict on abuse/spam, professional language",
        "examples": [
            ("go kys lol", {"strikes": 2}),
            ("follow me for free coins!!! http://spam.link", {"strikes": 1}),
            ("why are mods sleeping this chat is wilding", {"strikes": 1}),
        ],
    },
    "nuanced_patient": {
        "tone": "patient, context-aware, prefers gentle nudges first",
        "examples": [
            ("that's sus but maybe they meant it as a joke?", {"strikes": 0}),
            ("your mic is clipping bro, hurts my ears", {"strikes": 0}),
        ],
    },
}


def synthesize(num: int) -> list[dict]:
    out = []
    users = 0
    for _ in range(num):
        persona = random.choice(list(PERSONAS.keys()))
        template = random.choice(PERSONAS[persona]["examples"])
        comment, meta = template
        users += 1
        sample = {
            "comment": comment,
            "meta": {"user": f"user_{users:03d}", "account_age_days": random.randint(10, 900), **meta},
            "persona": persona,
        }
        out.append(sample)
    return out


def main():
    parser = argparse.ArgumentParser(description="Generate synthetic Twitch-like comments.")
    parser.add_argument("--output", type=Path, default=Path("data/synthetic_comments.json"))
    parser.add_argument("--num", type=int, default=50)
    args = parser.parse_args()

    args.output.parent.mkdir(parents=True, exist_ok=True)
    data = synthesize(args.num)
    with args.output.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    print(f"Wrote {len(data)} samples to {args.output}")


if __name__ == "__main__":
    main()

