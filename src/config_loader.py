from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


def load_yaml(path: str | Path) -> dict[str, Any]:
    """Load a YAML config file and return an empty dict for empty files."""
    config_path = Path(path)
    with config_path.open("r", encoding="utf-8") as file:
        loaded = yaml.safe_load(file)
    return loaded or {}


def load_config_dir(config_dir: str | Path) -> dict[str, dict[str, Any]]:
    """Load every YAML file in a directory keyed by file stem."""
    root = Path(config_dir)
    configs: dict[str, dict[str, Any]] = {}
    for path in sorted(root.glob("*.yaml")):
        configs[path.stem] = load_yaml(path)
    return configs
