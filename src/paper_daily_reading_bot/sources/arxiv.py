from __future__ import annotations

from datetime import datetime
from typing import List, Optional
import urllib.parse

import feedparser

from paper_daily_reading_bot.models import Paper
from paper_daily_reading_bot.sources.base import PaperSource, SourceError
from paper_daily_reading_bot.utils import in_window, parse_datetime


class ArxivSource(PaperSource):
    name = "arxiv"
    endpoint = "https://export.arxiv.org/api/query"

    def fetch(self, since: datetime, until: datetime) -> List[Paper]:
        search_query = self._build_query()
        if not search_query:
            self.logger.warning("arXiv source skipped: no query, keywords, or categories")
            return []

        params = {
            "search_query": search_query,
            "start": 0,
            "max_results": self.config.max_results,
            "sortBy": "lastUpdatedDate",
            "sortOrder": "descending",
        }
        url = f"{self.endpoint}?{urllib.parse.urlencode(params)}"
        response = self.session().get(url, timeout=self.config.timeout_seconds)
        if response.status_code >= 400:
            raise SourceError(f"arXiv API failed with HTTP {response.status_code}")

        feed = feedparser.parse(response.text)
        papers: List[Paper] = []
        for entry in feed.entries:
            published_at = self._parse_feed_datetime(getattr(entry, "published", None))
            updated_at = self._parse_feed_datetime(getattr(entry, "updated", None))
            if not (in_window(published_at, since, until) or in_window(updated_at, since, until)):
                continue

            papers.append(
                Paper(
                    title=" ".join(getattr(entry, "title", "").split()),
                    authors=[author.name for author in getattr(entry, "authors", [])],
                    source=self.name,
                    published_at=published_at,
                    updated_at=updated_at,
                    url=getattr(entry, "link", None),
                    doi=getattr(entry, "arxiv_doi", None),
                    abstract=" ".join(getattr(entry, "summary", "").split()),
                    journal="arXiv",
                    keywords=[tag.term for tag in getattr(entry, "tags", []) if hasattr(tag, "term")],
                    source_id=getattr(entry, "id", None),
                    raw=dict(entry),
                )
            )
        return papers

    def _build_query(self) -> str:
        if self.config.query:
            query = self.config.query
        else:
            phrases = [f'all:"{keyword}"' for keyword in self.research.keywords]
            query = " OR ".join(phrases)

        categories = " OR ".join(f"cat:{category}" for category in self.config.categories)
        if query and categories:
            return f"({query}) AND ({categories})"
        return query or categories

    @staticmethod
    def _parse_feed_datetime(value: Optional[str]) -> Optional[datetime]:
        return parse_datetime(value)
