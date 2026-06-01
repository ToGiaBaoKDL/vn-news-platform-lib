from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime


@dataclass(frozen=True)
class StorageLayout:
    buckets: dict[str, str]
    warehouse_prefix: str
    payload_prefix: str

    @classmethod
    def from_config(cls, config: dict) -> StorageLayout:
        storage = config["storage"]
        return cls(
            buckets=storage["buckets"],
            warehouse_prefix=storage["warehouse_prefix"],
            payload_prefix=storage["payload_prefix"],
        )

    def bucket_uri(self, layer: str) -> str:
        return f"s3://{self.buckets[layer]}"

    def warehouse_uri(self, layer: str, table_name: str) -> str:
        return f"{self.bucket_uri(layer)}/{self.warehouse_prefix}/{table_name}/"

    def rss_payload_uri(
        self,
        source_id: str,
        feed_id: str,
        ingest_date: date,
        scrape_run_id: str,
        extension: str = "xml.zst",
    ) -> str:
        return (
            f"{self.bucket_uri('landing')}/{self.payload_prefix}/rss/"
            f"source_id={source_id}/feed_id={feed_id}/"
            f"ingest_date={format_date_partition(ingest_date)}/"
            f"scrape_run_id={scrape_run_id}/feed.{extension}"
        )

    def article_payload_uri(
        self,
        source_id: str,
        ingest_date: date,
        article_id: str,
        source_document_id: str,
        extension: str = "html.zst",
    ) -> str:
        return (
            f"{self.bucket_uri('landing')}/{self.payload_prefix}/article_html/"
            f"source_id={source_id}/ingest_date={format_date_partition(ingest_date)}/"
            f"article_id={article_id}/source_document_id={source_document_id}/"
            f"document.{extension}"
        )

    def rss_checkpoint_uri(self, source_id: str, feed_id: str) -> str:
        return (
            f"{self.bucket_uri('landing')}/_checkpoints/rss/"
            f"source_id={source_id}/feed_id={feed_id}/checkpoint.json"
        )

    def article_fetch_checkpoint_uri(self, article_id: str) -> str:
        return (
            f"{self.bucket_uri('landing')}/_checkpoints/article_fetch/"
            f"article_id={article_id}/checkpoint.json"
        )


def format_date_partition(value: date | datetime) -> str:
    return value.date().isoformat() if isinstance(value, datetime) else value.isoformat()
