"""Platform library for VN News Intelligence services."""

from news_platform.config import get_topic_key, get_topic_name, load_settings, load_sources
from news_platform.contracts import (
    EVENT_CONTRACTS,
    EVENT_TOPIC_KEYS,
    ArticleExtracted,
    ArticleFetched,
    ArticleFetchRequested,
    ArticleImage,
    ArticleTextBlock,
    FeedItemDiscovered,
    NewsDlq,
    event_json_schema,
)
from news_platform.ids import make_run_id, make_stable_id, normalize_article_url
from news_platform.storage import StorageLayout

__all__ = [
    "EVENT_CONTRACTS",
    "EVENT_TOPIC_KEYS",
    "ArticleExtracted",
    "ArticleFetched",
    "ArticleFetchRequested",
    "ArticleImage",
    "ArticleTextBlock",
    "FeedItemDiscovered",
    "NewsDlq",
    "StorageLayout",
    "event_json_schema",
    "get_topic_key",
    "get_topic_name",
    "load_settings",
    "load_sources",
    "make_run_id",
    "make_stable_id",
    "normalize_article_url",
]
