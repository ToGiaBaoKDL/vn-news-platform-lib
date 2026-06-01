from __future__ import annotations

import hashlib
from datetime import datetime
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

TRACKING_QUERY_KEYS = {"fbclid", "gclid"}


def make_run_id(source_id: str, work_id: str, timestamp: datetime) -> str:
    return f"{source_id}_{work_id}_{timestamp.strftime('%Y%m%dT%H%M%S')}"


def make_stable_id(prefix: str, *parts: str) -> str:
    value = "\x1f".join(parts).encode()
    return f"{prefix}_{hashlib.sha256(value).hexdigest()[:24]}"


def normalize_article_url(url: str) -> str:
    parsed = urlsplit(url.strip())
    query = urlencode(
        sorted(
            (key, value)
            for key, value in parse_qsl(parsed.query, keep_blank_values=True)
            if key.lower() not in TRACKING_QUERY_KEYS and not key.lower().startswith("utm_")
        )
    )
    return urlunsplit(
        (
            parsed.scheme.lower(),
            parsed.netloc.lower(),
            parsed.path or "/",
            query,
            "",
        )
    )
