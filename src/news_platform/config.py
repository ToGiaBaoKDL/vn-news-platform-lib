from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml

from news_platform.validation import (
    validate_crawl_config,
    validate_event_bus_config,
    validate_sources,
    validate_storage_config,
)

PACKAGE_REPO_ROOT = Path(__file__).resolve().parents[2]
WORKSPACE_ROOT = PACKAGE_REPO_ROOT.parent
CONFIG_DIR = Path(
    os.environ.get("VN_NEWS_CONFIG_DIR", WORKSPACE_ROOT / "vn-news-config" / "configs")
)

SOURCE_DIR = CONFIG_DIR / "sources"


def load_yaml(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as file:
        data = yaml.safe_load(file) or {}
    if not isinstance(data, dict):
        msg = f"Expected YAML mapping in {path}"
        raise ValueError(msg)
    return data


def deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    merged = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def load_settings(environment: str | None = None) -> dict[str, Any]:
    config = load_yaml(CONFIG_DIR / "settings.yaml")
    env_name = environment or os.environ.get("TGB_ENV") or config["project"]["default_environment"]
    env_path = CONFIG_DIR / "environments" / f"{env_name}.yaml"
    if not env_path.exists():
        msg = f"Unknown environment: {env_name}"
        raise ValueError(msg)
    config = deep_merge(config, load_yaml(env_path))
    validate_crawl_config(config)
    validate_storage_config(config)
    validate_event_bus_config(config)
    return config


def load_sources(
    enabled_only: bool = False,
    settings: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    sources = [load_yaml(path) for path in sorted(SOURCE_DIR.glob("*.yaml"))]
    validate_sources(sources, settings or load_settings())
    if enabled_only:
        return [source for source in sources if source.get("enabled")]
    return sources


def get_topic_name(config: dict[str, Any], topic_key: str) -> str:
    return config["event_bus"]["topics"][topic_key]["name"]
