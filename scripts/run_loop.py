from __future__ import annotations

import argparse
from pathlib import Path

from src.config import load_config
from src.pipeline.moderation_loop import run_moderation_loop


def main():
    parser = argparse.ArgumentParser(description="Run Student/Expert moderation loop.")
    parser.add_argument("--config", type=Path, default=Path("configs/default.yaml"))
    args = parser.parse_args()

    config = load_config(args.config)
    run_moderation_loop(config)


if __name__ == "__main__":
    main()

