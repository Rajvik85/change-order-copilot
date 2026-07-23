"""Command-line verification and Streamlit launcher."""

from __future__ import annotations

import argparse
import logging
import subprocess
import sys
from pathlib import Path

from co_copilot.config import load_config
from co_copilot.evaluation import evaluate, to_markdown
from co_copilot.logging_config import configure_logging
from co_copilot.pipeline import load_project_metadata, run_pipeline

LOGGER = logging.getLogger(__name__)


def main() -> int:
    """Run the offline pipeline, report evaluation, and optionally launch UI."""
    configure_logging()
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--launch", action="store_true", help="Launch Streamlit after checks."
    )
    parser.add_argument(
        "--split", choices=("all", "development", "held_out"), default="all"
    )
    args = parser.parse_args()
    root = Path(__file__).resolve().parent
    result = run_pipeline(
        list((root / "data" / "change_orders").glob("*")),
        root / "data" / "contract" / "clauses",
        load_project_metadata(root / "data" / "project_meta.yaml"),
        load_config(root / "config.yaml"),
    )
    report = evaluate(
        result.extractions, root / "data" / "gold_standard.json", args.split
    )
    LOGGER.info("\n%s", to_markdown(report))
    if args.launch:
        return subprocess.call(
            [sys.executable, "-m", "streamlit", "run", str(root / "app" / "Home.py")]
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
