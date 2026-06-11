from __future__ import annotations

from datetime import date, datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, model_validator

JSON_SCHEMA_DIALECT = "https://json-schema.org/draft/2020-12/schema"


class BaseEvent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    event_id: str
    event_time: datetime


class SourceEvent(BaseEvent):
    run_id: str
    source_id: str
    ingest_date: date


class FeedItemDiscovered(SourceEvent):
    schema_version: Literal["feed_item.discovered.v2"]
    feed_item_id: str
    article_id: str
    feed_id: str
    category: str | None = None
    article_url: HttpUrl
    title: str
    summary: str | None = None
    published_at: datetime | None = None
    discovered_at: datetime
    payload_uri: str | None = None
    record_hash: str


class ArticleFetchRequested(SourceEvent):
    schema_version: Literal["article.fetch_requested.v3"]
    article_id: str
    requested_url: HttpUrl
    request_revision: str
    priority: int = 5


class ArticleFetched(SourceEvent):
    schema_version: Literal["article.fetched.v2"]
    article_id: str
    requested_url: HttpUrl
    source_document_id: str
    fetched_at: datetime
    status_code: int
    content_type: str | None = None
    content_length_bytes: int
    payload_uri: str
    content_hash: str
    fetch_status: Literal["success"]


class ArticleTextBlock(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: Literal["paragraph", "heading", "list_item", "quote", "caption"]
    text: str
    ordinal: int


class ArticleImage(BaseModel):
    model_config = ConfigDict(extra="forbid")

    url: HttpUrl
    alt: str | None = None
    caption: str | None = None
    ordinal: int


class ArticleExtracted(SourceEvent):
    schema_version: Literal["article.extracted.v3"]
    article_id: str
    requested_url: HttpUrl
    canonical_url: HttpUrl
    title: str
    summary: str | None = None
    body_text: str
    content_blocks: list[ArticleTextBlock]
    images: list[ArticleImage] = Field(default_factory=list)
    author: str | None = None
    published_at: datetime | None = None
    language: str = "vi"
    content_hash: str
    source_document_id: str
    source_payload_uri: str
    extracted_payload_uri: str | None = None
    extracted_payload_hash: str | None = None
    extractor_version: str
    extraction_status: Literal["success"]

    @model_validator(mode="after")
    def validate_content_location(self) -> ArticleExtracted:
        if not self.body_text and not self.extracted_payload_uri:
            raise ValueError("ArticleExtracted requires body_text or extracted_payload_uri")
        if self.extracted_payload_uri and not self.extracted_payload_hash:
            raise ValueError("ArticleExtracted requires extracted_payload_hash with URI")
        if self.extracted_payload_hash and not self.extracted_payload_uri:
            raise ValueError("ArticleExtracted requires extracted_payload_uri with hash")
        return self


class NewsDlq(BaseEvent):
    schema_version: Literal["news.dlq.v1"]
    source_topic: str
    source_partition: int | None = None
    source_offset: int | None = None
    error_class: str
    error_message: str
    payload: dict[str, Any]


EventModel = type[BaseEvent]

EVENT_TOPIC_KEYS: dict[str, str] = {
    "feed_item_discovered": "feed_item.discovered.v2",
    "article_fetch_requested": "article.fetch_requested.v3",
    "article_fetched": "article.fetched.v2",
    "article_extracted": "article.extracted.v3",
    "dlq": "news.dlq.v1",
}

EVENT_CONTRACTS: dict[str, EventModel] = {
    "feed_item.discovered.v2": FeedItemDiscovered,
    "article.fetch_requested.v3": ArticleFetchRequested,
    "article.fetched.v2": ArticleFetched,
    "article.extracted.v3": ArticleExtracted,
    "news.dlq.v1": NewsDlq,
}


def event_json_schema(event_name: str) -> dict[str, Any]:
    model = EVENT_CONTRACTS[event_name]
    schema = model.model_json_schema(mode="validation")
    schema["$schema"] = JSON_SCHEMA_DIALECT
    schema["title"] = event_name
    return schema
