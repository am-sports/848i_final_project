from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Load .env file if it exists
try:
    from dotenv import load_dotenv
    load_dotenv(project_root / ".env")
except ImportError:
    pass

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

