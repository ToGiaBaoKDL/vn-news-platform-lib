from __future__ import annotations

import re
from collections import Counter
from typing import Any
from urllib.parse import urlparse

BucketMap = dict[str, str]


def validate_storage_config(config: dict[str, Any]) -> None:
    buckets: BucketMap = config["storage"]["buckets"]
    expected_layers = {"landing", "curated", "analytics"}
    missing_layers = expected_layers - set(buckets)
    if missing_layers:
        msg = f"Missing storage buckets for layers: {sorted(missing_layers)}"
        raise ValueError(msg)

    names = list(buckets.values())
    if len(names) != len(set(names)):
        raise ValueError("Bucket names must be unique across layers")

    suffixes = []
    pattern = re.compile(r"^tgb-prod-(landing|curated|analytics)-([a-z0-9]{6})$")
    for layer, bucket_name in buckets.items():
        match = pattern.match(bucket_name)
        if not match:
            msg = (
                f"Invalid bucket name for {layer}: {bucket_name}. "
                "Use tgb-prod-{layer}-{six lowercase alnum chars}."
            )
            raise ValueError(msg)
        if match.group(1) != layer:
            msg = f"Bucket layer mismatch for {layer}: {bucket_name}"
            raise ValueError(msg)
        suffixes.append(match.group(2))

    if len(suffixes) != len(set(suffixes)):
        raise ValueError("Each storage bucket must use a different random suffix")


def validate_crawl_config(config: dict[str, Any]) -> None:
    for field in ("max_feed_bytes", "max_article_bytes"):
        if not isinstance(config["crawl"][field], int) or config["crawl"][field] <= 0:
            msg = f"crawl.{field} must be a positive integer"
            raise ValueError(msg)
    retry = config["crawl"]["retry"]
    for field in ("attempts", "backoff_seconds"):
        if not isinstance(retry[field], int) or retry[field] <= 0:
            msg = f"crawl.retry.{field} must be a positive integer"
            raise ValueError(msg)


def validate_event_bus_config(config: dict[str, Any]) -> None:
    consumer_retry = config["event_bus"].get("consumer_retry")
    if consumer_retry is not None:
        for field in ("base_delay_seconds", "max_delay_seconds", "jitter_seconds"):
            if field not in consumer_retry:
                msg = f"event_bus.consumer_retry missing field: {field}"
                raise ValueError(msg)
            if not isinstance(consumer_retry[field], int) or consumer_retry[field] < 0:
                msg = f"event_bus.consumer_retry.{field} must be a non-negative integer"
                raise ValueError(msg)
        if consumer_retry["base_delay_seconds"] <= 0:
            raise ValueError("event_bus.consumer_retry.base_delay_seconds must be positive")
        if consumer_retry["max_delay_seconds"] < consumer_retry["base_delay_seconds"]:
            raise ValueError(
                "event_bus.consumer_retry.max_delay_seconds must be >= base_delay_seconds"
            )

    topics = config["event_bus"]["topics"]
    names = []
    required_fields = {"name", "partitions", "retention_ms", "retention_bytes"}
    for topic_key, topic in topics.items():
        missing_fields = required_fields - set(topic)
        if missing_fields:
            msg = f"Topic {topic_key} missing fields: {sorted(missing_fields)}"
            raise ValueError(msg)
        if not isinstance(topic["name"], str) or not topic["name"]:
            msg = f"Topic {topic_key} name must be a non-empty string"
            raise ValueError(msg)
        for field in ("partitions", "retention_ms", "retention_bytes"):
            if not isinstance(topic[field], int) or topic[field] <= 0:
                msg = f"Topic {topic_key} {field} must be a positive integer"
                raise ValueError(msg)
        names.append(topic["name"])
    if len(names) != len(set(names)):
        raise ValueError("Topic names must be unique")


def validate_sources(sources: list[dict[str, Any]], config: dict[str, Any]) -> None:
    required_source_fields = {
        "version",
        "source_id",
        "display_name",
        "domain",
        "enabled",
        "audit_status",
        "crawl",
        "feed_discovery",
        "article",
    }
    required_crawl_fields = {"delay_seconds", "timeout_seconds", "user_agent_policy"}
    required_feed_discovery_fields = {"index_url", "feeds"}
    required_feed_fields = {"feed_id", "category", "url"}
    required_article_fields = {"extractor", "attribution_policy"}

    user_agent_policies = set(config["crawl"]["user_agents"])
    slug_pattern = re.compile(r"^[a-z0-9]+(_[a-z0-9]+)*$")
    source_ids = []

    for source in sources:
        missing = required_source_fields - set(source)
        if missing:
            msg = f"Source config missing fields: {sorted(missing)}"
            raise ValueError(msg)

        source_id = source["source_id"]
        if not slug_pattern.match(source_id):
            msg = f"Invalid source_id: {source_id}"
            raise ValueError(msg)
        domain = source["domain"]
        validate_domain_name(source_id, "domain", domain)
        source_ids.append(source_id)
        crawl = source["crawl"]
        feed_discovery = source["feed_discovery"]
        article = source["article"]

        missing_crawl = required_crawl_fields - set(crawl)
        if missing_crawl:
            msg = f"Source {source_id} crawl missing fields: {sorted(missing_crawl)}"
            raise ValueError(msg)

        missing_fd = required_feed_discovery_fields - set(feed_discovery)
        if missing_fd:
            msg = f"Source {source_id} feed_discovery missing fields: {sorted(missing_fd)}"
            raise ValueError(msg)
        if "strategy" in feed_discovery:
            msg = f"Source {source_id} must not define feed_discovery.strategy; project is RSS-only"
            raise ValueError(msg)
        validate_source_url_domain(source_id, domain, feed_discovery["index_url"])

        missing_article = required_article_fields - set(article)
        if missing_article:
            msg = f"Source {source_id} article missing fields: {sorted(missing_article)}"
            raise ValueError(msg)
        blocked_status_codes = article.get("blocked_status_codes", [])
        if not isinstance(blocked_status_codes, list) or any(
            not isinstance(status_code, int) or status_code < 400 or status_code > 599
            for status_code in blocked_status_codes
        ):
            msg = f"Source {source_id} article.blocked_status_codes must be 4xx/5xx integers"
            raise ValueError(msg)
        approved_redirect_domains = article.get("approved_redirect_domains", [])
        if not isinstance(approved_redirect_domains, list):
            msg = f"Source {source_id} article.approved_redirect_domains must be a list"
            raise ValueError(msg)
        for redirect_domain in approved_redirect_domains:
            validate_domain_name(source_id, "article.approved_redirect_domains", redirect_domain)
        if len(approved_redirect_domains) != len(set(approved_redirect_domains)):
            msg = f"Source {source_id} article.approved_redirect_domains must be unique"
            raise ValueError(msg)
        invalid_document_markers = article.get("invalid_document_markers", [])
        if not isinstance(invalid_document_markers, list) or any(
            not isinstance(marker, str) or not marker.strip() or len(marker) > 200
            for marker in invalid_document_markers
        ):
            msg = (
                f"Source {source_id} article.invalid_document_markers must be "
                "non-empty strings of at most 200 characters"
            )
            raise ValueError(msg)
        extraction = article.get("extraction", {})
        if not isinstance(extraction, dict):
            msg = f"Source {source_id} article.extraction must be a mapping"
            raise ValueError(msg)
        for field in ("content_selectors", "exclude_selectors", "boilerplate_markers"):
            selectors = extraction.get(field, [])
            if not isinstance(selectors, list) or any(
                not isinstance(selector, str) or not selector.strip() or len(selector) > 200
                for selector in selectors
            ):
                msg = (
                    f"Source {source_id} article.extraction.{field} must be "
                    "non-empty strings of at most 200 characters"
                )
                raise ValueError(msg)
        for field in ("min_text_chars", "min_blocks"):
            if field in extraction and (
                not isinstance(extraction[field], int) or extraction[field] <= 0
            ):
                msg = f"Source {source_id} article.extraction.{field} must be positive"
                raise ValueError(msg)

        if crawl["user_agent_policy"] not in user_agent_policies:
            msg = f"Unknown user_agent_policy for {source_id}: {crawl['user_agent_policy']}"
            raise ValueError(msg)
        for field in ("delay_seconds", "timeout_seconds"):
            if not isinstance(crawl[field], int) or crawl[field] <= 0:
                msg = f"Source {source_id} crawl.{field} must be a positive integer"
                raise ValueError(msg)

        feeds = feed_discovery.get("feeds", [])
        if source.get("enabled") and not feeds:
            msg = f"Enabled source has no configured feeds: {source_id}"
            raise ValueError(msg)

        for feed in feeds:
            missing_feed = required_feed_fields - set(feed)
            if missing_feed:
                feed_id = feed.get("feed_id", "?")
                msg = f"Source {source_id} feed {feed_id} missing: {sorted(missing_feed)}"
                raise ValueError(msg)

        feed_ids = [feed["feed_id"] for feed in feeds]
        invalid_ids = [feed_id for feed_id in feed_ids if not slug_pattern.match(feed_id)]
        if invalid_ids:
            msg = f"Invalid feed IDs for {source_id}: {invalid_ids}"
            raise ValueError(msg)

        invalid_categories = [
            feed["category"] for feed in feeds if not slug_pattern.match(feed["category"])
        ]
        if invalid_categories:
            msg = f"Invalid feed categories for {source_id}: {invalid_categories}"
            raise ValueError(msg)

        duplicate_ids = sorted(feed_id for feed_id, count in Counter(feed_ids).items() if count > 1)
        if duplicate_ids:
            msg = f"Duplicate feed IDs for {source_id}: {duplicate_ids}"
            raise ValueError(msg)

        feed_urls = [feed["url"] for feed in feeds]
        for url in feed_urls:
            validate_source_url_domain(source_id, domain, url)
        duplicate_urls = sorted(url for url, count in Counter(feed_urls).items() if count > 1)
        if duplicate_urls:
            msg = f"Duplicate feed URLs for {source_id}: {duplicate_urls}"
            raise ValueError(msg)

    if len(source_ids) != len(set(source_ids)):
        raise ValueError("Source IDs must be unique")


def validate_source_url_domain(source_id: str, domain: str, url: str) -> None:
    host = urlparse(url).hostname
    if not host or (host != domain and not host.endswith(f".{domain}")):
        msg = f"Source {source_id} URL host must match domain {domain}: {url}"
        raise ValueError(msg)


def validate_domain_name(source_id: str, field: str, value: Any) -> None:
    if not isinstance(value, str):
        msg = f"Source {source_id} {field} must be a domain string"
        raise ValueError(msg)
    domain = value.strip().rstrip(".").lower()
    if domain != value or "://" in value or "/" in value or ":" in value:
        msg = f"Source {source_id} {field} must be a normalized domain: {value}"
        raise ValueError(msg)
    labels = domain.split(".")
    label_pattern = re.compile(r"^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$")
    if len(labels) < 2 or any(not label_pattern.match(label) for label in labels):
        msg = f"Source {source_id} {field} is not a valid domain: {value}"
        raise ValueError(msg)
