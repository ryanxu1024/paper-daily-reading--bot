from __future__ import annotations

from datetime import datetime
from email.utils import parsedate_to_datetime
from typing import List, Optional
import re

import feedparser

from paper_daily_reading_bot.models import Paper
from paper_daily_reading_bot.sources.base import PaperSource, SourceError
from paper_daily_reading_bot.utils import ensure_utc, in_window, parse_datetime, strip_html


DOI_PATTERN = re.compile(r"\b10\.\d{4,9}/[-._;()/:A-Z0-9]+\b", re.IGNORECASE)


class RSSFeedSource(PaperSource):
    def __init__(self, name: str, config, research) -> None:
        self.name = name
        super().__init__(config, research)

    def fetch(self, since: datetime, until: datetime) -> List[Paper]:
        if not self.config.rss_urls:
            self.logger.warning("%s source skipped: no rss_urls configured", self.name)
            return []

        papers: List[Paper] = []
        for url in self.config.rss_urls:
            response = self.session().get(url, timeout=self.config.timeout_seconds)
            if response.status_code >= 400:
                raise SourceError(f"{self.name} RSS failed with HTTP {response.status_code}: {url}")
            feed = feedparser.parse(response.text)
            journal = getattr(feed.feed, "title", self.name)
            for entry in feed.entries:
                paper = self._parse_entry(entry, journal)
                if in_window(paper.published_at, since, until) or in_window(
                    paper.updated_at, since, until
                ):
                    papers.append(paper)
                    if len(papers) >= self.config.max_results:
                        return papers
        return papers

    def _parse_entry(self, entry, journal: str) -> Paper:
        summary = strip_html(getattr(entry, "summary", "") or getattr(entry, "description", ""))
        doi = self._extract_doi(entry, summary)
        tags = [
            tag.term
            for tag in getattr(entry, "tags", [])
            if hasattr(tag, "term") and tag.term
        ]
        authors = []
        if getattr(entry, "authors", None):
            authors = [author.get("name", "") for author in entry.authors]
        elif getattr(entry, "author", None):
            authors = [getattr(entry, "author")]
        return Paper(
            title=" ".join(getattr(entry, "title", "").split()),
            authors=[author for author in authors if author],
            source=self.name,
            published_at=self._parse_feed_datetime(getattr(entry, "published", None)),
            updated_at=self._parse_feed_datetime(getattr(entry, "updated", None)),
            url=getattr(entry, "link", None),
            doi=doi,
            abstract=summary,
            journal=journal,
            keywords=tags,
            source_id=getattr(entry, "id", None) or getattr(entry, "link", None),
            raw=dict(entry),
        )

    @staticmethod
    def _parse_feed_datetime(value: Optional[str]) -> Optional[datetime]:
        if not value:
            return None
        try:
            return ensure_utc(parsedate_to_datetime(value))
        except (TypeError, ValueError, IndexError):
            return parse_datetime(value)

    @staticmethod
    def _extract_doi(entry, summary: str) -> Optional[str]:
        candidates = [
            getattr(entry, "prism_doi", None),
            getattr(entry, "dc_identifier", None),
            getattr(entry, "id", None),
            getattr(entry, "link", None),
            summary,
        ]
        for candidate in candidates:
            if not candidate:
                continue
            match = DOI_PATTERN.search(str(candidate))
            if match:
                return match.group(0).rstrip(".")
        return None
