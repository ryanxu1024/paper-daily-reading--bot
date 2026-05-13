from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List
import os

from paper_daily_reading_bot.models import Paper
from paper_daily_reading_bot.sources.base import PaperSource, SourceError
from paper_daily_reading_bot.utils import in_window, parse_datetime


class IEEESource(PaperSource):
    name = "ieee"
    endpoint = "https://ieeexploreapi.ieee.org/api/v1/search/articles"

    def fetch(self, since: datetime, until: datetime) -> List[Paper]:
        api_key = os.getenv(self.config.api_key_env or "IEEE_API_KEY")
        if not api_key:
            self.logger.warning("IEEE source skipped: API key env var is not set")
            return []

        params = {
            "apikey": api_key,
            "format": "json",
            "max_records": min(self.config.max_results, 200),
            "sort_order": "desc",
            "sort_field": "publication_date",
            "querytext": self.config.query or " OR ".join(self.research.keywords),
        }
        response = self.session().get(
            self.endpoint, params=params, timeout=self.config.timeout_seconds
        )
        if response.status_code >= 400:
            raise SourceError(f"IEEE API failed with HTTP {response.status_code}")

        papers: List[Paper] = []
        for item in response.json().get("articles", []):
            paper = self._parse_article(item)
            if in_window(paper.published_at, since, until) or in_window(
                paper.updated_at, since, until
            ):
                papers.append(paper)
        return papers

    def _parse_article(self, item: Dict[str, Any]) -> Paper:
        author_items = (item.get("authors") or {}).get("authors", [])
        authors = [author.get("full_name", "") for author in author_items]
        keywords = []
        for bucket in (item.get("index_terms") or {}).values():
            if isinstance(bucket, dict):
                keywords.extend(bucket.get("terms", []))
            elif isinstance(bucket, list):
                keywords.extend(bucket)
        published_at = parse_datetime(
            item.get("publication_date")
            or item.get("publication_year")
            or item.get("insert_date")
        )
        return Paper(
            title=item.get("title") or item.get("article_title") or "",
            authors=[author for author in authors if author],
            source=self.name,
            published_at=published_at,
            updated_at=parse_datetime(item.get("insert_date")),
            url=item.get("html_url") or item.get("pdf_url"),
            doi=item.get("doi"),
            abstract=item.get("abstract") or "",
            journal=item.get("publication_title"),
            keywords=[keyword for keyword in keywords if keyword],
            source_id=str(item.get("article_number") or item.get("document_identifier") or ""),
            raw=item,
        )
