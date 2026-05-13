from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional
import logging

from dateutil import parser


def setup_logging(level: str) -> None:
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    )


def ensure_utc(value: Optional[datetime]) -> Optional[datetime]:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def parse_datetime(value: object) -> Optional[datetime]:
    if not value:
        return None
    try:
        if isinstance(value, datetime):
            return ensure_utc(value)
        return ensure_utc(parser.parse(str(value)))
    except (TypeError, ValueError, OverflowError):
        return None


def in_window(value: Optional[datetime], since: datetime, until: datetime) -> bool:
    if value is None:
        return False
    value = ensure_utc(value)
    return since <= value <= until


def strip_html(value: str) -> str:
    import re

    text = re.sub(r"<[^>]+>", " ", value or "")
    return re.sub(r"\s+", " ", text).strip()
