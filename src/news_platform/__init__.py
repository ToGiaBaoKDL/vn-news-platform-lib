"""Platform library for VN News Intelligence services."""

from news_platform.config import get_topic_name, load_settings, load_sources
from news_platform.contracts import (
    EVENT_CONTRACTS,
    EVENT_TOPIC_KEYS,
    ArticleExtracted,
    ArticleFetched,
    ArticleFetchRequested,
    FeedItemDiscovered,
    NewsDlq,
    TableSpec,
    event_json_schema,
    load_table_specs,
)
from news_platform.ids import make_run_id, make_stable_id, normalize_article_url
from news_platform.storage import StorageLayout

__all__ = [
    "EVENT_CONTRACTS",
    "EVENT_TOPIC_KEYS",
    "ArticleExtracted",
    "ArticleFetched",
    "ArticleFetchRequested",
    "FeedItemDiscovered",
    "NewsDlq",
    "StorageLayout",
    "TableSpec",
    "event_json_schema",
    "get_topic_name",
    "load_settings",
    "load_sources",
    "load_table_specs",
    "make_run_id",
    "make_stable_id",
    "normalize_article_url",
]
