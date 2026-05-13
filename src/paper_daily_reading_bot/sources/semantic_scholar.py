from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional
import os
import time

from paper_daily_reading_bot.models import Paper
from paper_daily_reading_bot.sources.base import PaperSource, SourceError, SourceRateLimitError
from paper_daily_reading_bot.utils import in_window, parse_datetime


class SemanticScholarSource(PaperSource):
    name = "semantic_scholar"
    endpoint = "https://api.semanticscholar.org/graph/v1/paper/search"
    fields = ",".join(
        [
            "paperId",
            "externalIds",
            "title",
            "authors",
            "venue",
            "year",
            "publicationDate",
            "url",
            "abstract",
            "fieldsOfStudy",
            "s2FieldsOfStudy",
            "publicationTypes",
            "openAccessPdf",
        ]
    )

    def fetch(self, since: datetime, until: datetime) -> List[Paper]:
        query = self.config.query or " ".join(self.research.keywords)
        if not query:
            self.logger.warning("Semantic Scholar source skipped: no query or keywords")
            return []

        endpoint = self._endpoint()
        headers = {}
        api_key = os.getenv(self.config.api_key_env or "SEMANTIC_SCHOLAR_API_KEY")
        if api_key:
            headers["x-api-key"] = api_key

        papers: List[Paper] = []
        offset = 0
        while len(papers) < self.config.max_results:
            limit = min(100, self.config.max_results - len(papers))
            params = {
                "query": query,
                "fields": self.fields,
                "limit": limit,
                "offset": offset,
                "publicationDateOrYear": f"{since.date()}:{until.date()}",
            }
            if self.config.categories:
                params["fieldsOfStudy"] = ",".join(self.config.categories)

            response = self._request_with_retry(endpoint, params, headers, bool(api_key))

            data = response.json().get("data", [])
            if not data:
                break

            for item in data:
                paper = self._parse_paper(item)
                if in_window(paper.published_at, since, until) or paper.published_at is None:
                    papers.append(paper)
                    if len(papers) >= self.config.max_results:
                        break

            if len(data) < limit:
                break
            offset += len(data)

        return papers

    def _request_with_retry(self, endpoint, params, headers, has_api_key):
        attempts = 3 if has_api_key else 1
        for attempt in range(attempts):
            response = self.session(headers).get(
                endpoint, params=params, timeout=self.config.timeout_seconds
            )
            if response.status_code == 429:
                if attempt < attempts - 1:
                    wait_seconds = self._retry_after_seconds(response, attempt)
                    self.logger.warning(
                        "Semantic Scholar rate-limited the request; retrying in %.1f seconds",
                        wait_seconds,
                    )
                    time.sleep(wait_seconds)
                    continue
                raise SourceRateLimitError(
                    "Semantic Scholar API rate limit reached. "
                    "Set SEMANTIC_SCHOLAR_API_KEY for a higher limit, reduce "
                    "sources.semantic_scholar.max_results, or disable this source."
                )
            if response.status_code >= 400:
                raise SourceError(
                    "Semantic Scholar API failed with "
                    f"HTTP {response.status_code}: {response.text}"
                )
            return response
        raise SourceRateLimitError("Semantic Scholar API rate limit reached")

    @staticmethod
    def _retry_after_seconds(response, attempt: int) -> float:
        raw_value = response.headers.get("Retry-After")
        if raw_value:
            try:
                return max(1.0, min(float(raw_value), 30.0))
            except ValueError:
                pass
        return min(5.0 * (attempt + 1), 30.0)

    def _endpoint(self) -> str:
        if self.config.endpoint:
            return self.config.endpoint.rstrip("/")
        if self.config.rss_urls:
            return self.config.rss_urls[0].rstrip("/")
        return self.endpoint

    def _parse_paper(self, item: Dict[str, Any]) -> Paper:
        external_ids = item.get("externalIds") or {}
        authors = [
            author.get("name", "")
            for author in item.get("authors", [])
            if isinstance(author, dict)
        ]
        keywords = list(item.get("fieldsOfStudy") or [])
        keywords.extend(
            field.get("category", "")
            for field in item.get("s2FieldsOfStudy", [])
            if isinstance(field, dict)
        )
        return Paper(
            title=item.get("title") or "",
            authors=[author for author in authors if author],
            source=self.name,
            published_at=parse_datetime(item.get("publicationDate") or item.get("year")),
            updated_at=None,
            url=item.get("url") or self._open_access_url(item),
            doi=external_ids.get("DOI"),
            abstract=item.get("abstract") or "",
            journal=item.get("venue"),
            keywords=sorted(set(keyword for keyword in keywords if keyword)),
            source_id=item.get("paperId"),
            raw=item,
        )

    @staticmethod
    def _open_access_url(item: Dict[str, Any]) -> Optional[str]:
        pdf = item.get("openAccessPdf") or {}
        if isinstance(pdf, dict):
            return pdf.get("url")
        return None
