"""Configuration loading with stable hashes for traceability."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG_PATH = PROJECT_ROOT / "config.yaml"


def load_config(path: Path = DEFAULT_CONFIG_PATH) -> dict[str, Any]:
    """Load YAML configuration.

    Args:
        path: Configuration file path.

    Returns:
        Parsed configuration dictionary.
    """
    with path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {}


def config_hash(config: dict[str, Any]) -> str:
    """Return a short deterministic hash used to stamp artifacts."""
    canonical = json.dumps(config, sort_keys=True, default=str).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()[:16]
