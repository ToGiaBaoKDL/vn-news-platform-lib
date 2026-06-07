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
ENV_OVERRIDES = {
    "VN_NEWS_STORAGE_ENDPOINT_URL": ("storage", "endpoint_url"),
    "VN_NEWS_REDPANDA_BOOTSTRAP_SERVERS": ("event_bus", "bootstrap_servers"),
    "VN_NEWS_SCHEMA_REGISTRY_URL": ("event_bus", "schema_registry_url"),
}


def load_yaml(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as file:
        data = yaml.safe_load(file) or {}
    if not isinstance(data, dict):
        msg = f"Expected YAML mapping in {path}"
        raise ValueError(msg)
    return data


def load_settings() -> dict[str, Any]:
    config = load_yaml(CONFIG_DIR / "settings.yaml")
    apply_env_overrides(config)
    validate_crawl_config(config)
    validate_storage_config(config)
    validate_event_bus_config(config)
    return config


def apply_env_overrides(config: dict[str, Any]) -> None:
    for env_name, path in ENV_OVERRIDES.items():
        value = os.environ.get(env_name)
        if not value:
            continue
        target = config
        for key in path[:-1]:
            target = target[key]
        target[path[-1]] = value


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


def get_topic_key(config: dict[str, Any], topic_name: str) -> str:
    for topic_key, topic in config["event_bus"]["topics"].items():
        if topic["name"] == topic_name:
            return topic_key
    raise KeyError(f"Unknown topic name: {topic_name}")
