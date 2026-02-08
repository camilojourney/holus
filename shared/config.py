"""Configuration loader for HOLUS."""
from pathlib import Path
from typing import Any, Optional

import yaml


def load_config(path: str | Path) -> dict[str, Any]:
    """Load YAML configuration file."""
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {path}")
    
    with open(path) as f:
        return yaml.safe_load(f) or {}


def load_domain_config(domain: str, base_path: str = "agents") -> dict[str, Any]:
    """Load configuration for a specific domain."""
    config_path = Path(base_path) / domain / "config.yaml"
    if config_path.exists():
        return load_config(config_path)
    return {}


def merge_configs(*configs: dict) -> dict[str, Any]:
    """Deep merge multiple configs, later ones override earlier."""
    result = {}
    for config in configs:
        for key, value in config.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = merge_configs(result[key], value)
            else:
                result[key] = value
    return result
