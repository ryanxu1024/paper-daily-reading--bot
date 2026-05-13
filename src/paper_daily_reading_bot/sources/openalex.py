from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from paper_daily_reading_bot.models import Paper
from paper_daily_reading_bot.sources.base import PaperSource, SourceError
from paper_daily_reading_bot.utils import in_window, parse_datetime


class OpenAlexSource(PaperSource):
    name = "openalex"
    endpoint = "https://api.openalex.org/works"

    def fetch(self, since: datetime, until: datetime) -> List[Paper]:
        search = self.config.query or " ".join(self.research.keywords)
        papers: List[Paper] = []
        seen = set()
        filters = [
            f"from_publication_date:{since.date()},to_publication_date:{until.date()}",
            f"from_updated_date:{since.date()},to_updated_date:{until.date()}",
        ]

        for filter_value in filters:
            params = {
                "search": search,
                "filter": filter_value,
                "per-page": min(self.config.max_results, 200),
                "sort": "updated_date:desc",
            }
            response = self.session().get(
                self.endpoint, params=params, timeout=self.config.timeout_seconds
            )
            if response.status_code >= 400:
                raise SourceError(f"OpenAlex API failed with HTTP {response.status_code}")
            for item in response.json().get("results", []):
                paper = self._parse_work(item)
                if paper.identity_key() in seen:
                    continue
                if not (
                    in_window(paper.published_at, since, until)
                    or in_window(paper.updated_at, since, until)
                ):
                    continue
                seen.add(paper.identity_key())
                papers.append(paper)
                if len(papers) >= self.config.max_results:
                    return papers
        return papers

    def _parse_work(self, item: Dict[str, Any]) -> Paper:
        location = item.get("primary_location") or {}
        source = location.get("source") or {}
        authors = [
            (author.get("author") or {}).get("display_name", "")
            for author in item.get("authorships", [])
        ]
        keywords = [
            keyword.get("display_name") or keyword.get("keyword", "")
            for keyword in item.get("keywords", [])
        ]
        keywords.extend(
            concept.get("display_name", "")
            for concept in item.get("concepts", [])[:8]
            if concept.get("display_name")
        )
        url = (
            location.get("landing_page_url")
            or item.get("doi")
            or item.get("id")
        )
        return Paper(
            title=item.get("display_name") or "",
            authors=[author for author in authors if author],
            source=self.name,
            published_at=parse_datetime(item.get("publication_date")),
            updated_at=parse_datetime(item.get("updated_date")),
            url=url,
            doi=self._clean_doi(item.get("doi")),
            abstract=self._abstract_from_inverted_index(item.get("abstract_inverted_index")),
            journal=source.get("display_name"),
            keywords=[keyword for keyword in keywords if keyword],
            source_id=item.get("id"),
            raw=item,
        )

    @staticmethod
    def _clean_doi(value: Optional[str]) -> Optional[str]:
        if not value:
            return None
        return value.replace("https://doi.org/", "").strip()

    @staticmethod
    def _abstract_from_inverted_index(index: Optional[Dict[str, List[int]]]) -> str:
        if not index:
            return ""
        positions: Dict[int, str] = {}
        for word, indexes in index.items():
            for position in indexes:
                positions[int(position)] = word
        return " ".join(positions[position] for position in sorted(positions))
