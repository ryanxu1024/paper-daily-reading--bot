from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List
import os

from paper_daily_reading_bot.models import Paper
from paper_daily_reading_bot.sources.base import PaperSource, SourceError
from paper_daily_reading_bot.utils import in_window, parse_datetime


class ElsevierSource(PaperSource):
    name = "elsevier"
    endpoint = "https://api.elsevier.com/content/search/scopus"

    def fetch(self, since: datetime, until: datetime) -> List[Paper]:
        api_key = os.getenv(self.config.api_key_env or "ELSEVIER_API_KEY")
        if not api_key:
            self.logger.warning("Elsevier source skipped: API key env var is not set")
            return []

        params = {
            "query": self.config.query or self._build_query(),
            "count": min(self.config.max_results, 200),
            "sort": "-coverDate",
            "field": ",".join(
                [
                    "dc:identifier",
                    "dc:title",
                    "dc:creator",
                    "prism:publicationName",
                    "prism:coverDate",
                    "prism:doi",
                    "prism:url",
                    "dc:description",
                    "authkeywords",
                ]
            ),
        }
        response = self.session({"X-ELS-APIKey": api_key, "Accept": "application/json"}).get(
            self.endpoint, params=params, timeout=self.config.timeout_seconds
        )
        if response.status_code >= 400:
            raise SourceError(f"Elsevier API failed with HTTP {response.status_code}")

        papers: List[Paper] = []
        for item in response.json().get("search-results", {}).get("entry", []):
            paper = self._parse_entry(item)
            if in_window(paper.published_at, since, until) or in_window(
                paper.updated_at, since, until
            ):
                papers.append(paper)
        return papers

    def _build_query(self) -> str:
        joined = " OR ".join(f'"{keyword}"' for keyword in self.research.keywords)
        return f"TITLE-ABS-KEY({joined})"

    def _parse_entry(self, item: Dict[str, Any]) -> Paper:
        doi = item.get("prism:doi")
        link = item.get("prism:url")
        authors = []
        creator = item.get("dc:creator")
        if creator:
            authors = [part.strip() for part in str(creator).split(";") if part.strip()]
        keywords = []
        if item.get("authkeywords"):
            keywords = [
                part.strip()
                for part in str(item.get("authkeywords")).replace("|", ";").split(";")
                if part.strip()
            ]
        return Paper(
            title=item.get("dc:title") or "",
            authors=authors,
            source=self.name,
            published_at=parse_datetime(item.get("prism:coverDate")),
            updated_at=None,
            url=link,
            doi=doi,
            abstract=item.get("dc:description") or "",
            journal=item.get("prism:publicationName"),
            keywords=keywords,
            source_id=item.get("dc:identifier"),
            raw=item,
        )
