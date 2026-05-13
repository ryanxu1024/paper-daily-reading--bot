from __future__ import annotations

from datetime import datetime, timezone
from typing import Dict, Iterable, List, Sequence, Tuple
import logging
import math
import re

from paper_daily_reading_bot.config import ResearchConfig
from paper_daily_reading_bot.models import Paper, ScoredPaper, normalize_title


LOGGER = logging.getLogger(__name__)


def paper_text(paper: Paper) -> str:
    return " ".join(
        part
        for part in [
            paper.title,
            paper.abstract,
            " ".join(paper.keywords),
            paper.journal or "",
        ]
        if part
    )


def deduplicate_papers(papers: Iterable[Paper]) -> List[Paper]:
    by_key: Dict[str, Paper] = {}
    title_to_key: Dict[str, str] = {}

    for paper in papers:
        title_key = normalize_title(paper.title)
        primary_key = paper.identity_key()
        existing_key = title_to_key.get(title_key, primary_key)

        if existing_key in by_key:
            by_key[existing_key] = _merge_papers(by_key[existing_key], paper)
            continue

        by_key[primary_key] = paper
        if title_key:
            title_to_key[title_key] = primary_key

    return list(by_key.values())


def _merge_papers(existing: Paper, incoming: Paper) -> Paper:
    preferred = incoming if _completeness(incoming) > _completeness(existing) else existing
    other = existing if preferred is incoming else incoming

    preferred.authors = preferred.authors or other.authors
    preferred.abstract = preferred.abstract or other.abstract
    preferred.url = preferred.url or other.url
    preferred.doi = preferred.doi or other.doi
    preferred.journal = preferred.journal or other.journal
    preferred.published_at = preferred.published_at or other.published_at
    preferred.updated_at = preferred.updated_at or other.updated_at
    preferred.keywords = sorted(set(preferred.keywords + other.keywords))
    return preferred


def _completeness(paper: Paper) -> int:
    return (
        int(bool(paper.doi)) * 3
        + int(bool(paper.abstract)) * 2
        + int(bool(paper.url))
        + min(len(paper.authors), 5)
        + min(len(paper.keywords), 5)
    )


class PaperRanker:
    def __init__(self, research: ResearchConfig) -> None:
        self.research = research

    def rank(self, papers: Sequence[Paper]) -> List[ScoredPaper]:
        if not papers:
            return []

        semantic_scores = self._semantic_scores(papers)
        scored: List[ScoredPaper] = []
        for index, paper in enumerate(papers):
            keyword_score, matched_keywords = self._keyword_score(paper)
            semantic_score = semantic_scores[index]
            total_score = min(1.0, max(0.0, 0.45 * keyword_score + 0.55 * semantic_score))
            scored.append(
                ScoredPaper(
                    paper=paper,
                    keyword_score=keyword_score,
                    semantic_score=semantic_score,
                    total_score=total_score,
                    matched_keywords=matched_keywords,
                )
            )

        return sorted(
            scored,
            key=lambda item: (
                item.total_score,
                item.paper.event_date or datetime.min.replace(tzinfo=timezone.utc),
            ),
            reverse=True,
        )

    def select_top(self, papers: Sequence[Paper]) -> List[ScoredPaper]:
        return self.rank(papers)[: self.research.max_papers]

    def _keyword_score(self, paper: Paper) -> Tuple[float, List[str]]:
        title = paper.title.lower()
        body = paper_text(paper).lower()
        matched: List[str] = []
        score = 0.0
        max_score = max(len(self.research.keywords) * 2.0, 1.0)

        for keyword in self.research.keywords:
            normalized = keyword.lower().strip()
            if not normalized:
                continue
            if normalized in title:
                score += 2.0
                matched.append(keyword)
            elif normalized in body:
                score += 1.0
                matched.append(keyword)
            else:
                overlap = _token_overlap(normalized, body)
                if overlap >= 0.6:
                    score += 0.5 * overlap
                    matched.append(keyword)

        for keyword in self.research.negative_keywords:
            if keyword.lower().strip() and keyword.lower().strip() in body:
                score -= 0.6

        return min(1.0, max(0.0, score / max_score)), sorted(set(matched))

    def _semantic_scores(self, papers: Sequence[Paper]) -> List[float]:
        return self._tfidf_scores(papers)

    def _tfidf_scores(self, papers: Sequence[Paper]) -> List[float]:
        documents = [self._research_text()] + [paper_text(paper) for paper in papers]
        try:
            from sklearn.feature_extraction.text import TfidfVectorizer
            from sklearn.metrics.pairwise import cosine_similarity

            vectorizer = TfidfVectorizer(
                stop_words="english",
                ngram_range=(1, 2),
                max_features=6000,
                min_df=1,
            )
            matrix = vectorizer.fit_transform(documents)
            similarities = cosine_similarity(matrix[0:1], matrix[1:]).flatten()
            return [float(max(0.0, min(1.0, score))) for score in similarities]
        except Exception as exc:  # noqa: BLE001
            LOGGER.warning("TF-IDF semantic scoring failed; using token overlap: %s", exc)
            query = self._research_text()
            return [_token_overlap(query, paper_text(paper)) for paper in papers]

    def _research_text(self) -> str:
        return " ".join(self.research.directions + self.research.keywords)


def _token_overlap(left: str, right: str) -> float:
    left_tokens = set(_tokens(left))
    right_tokens = set(_tokens(right))
    if not left_tokens or not right_tokens:
        return 0.0
    return len(left_tokens & right_tokens) / math.sqrt(len(left_tokens) * len(right_tokens))


def _tokens(value: str) -> List[str]:
    return [token for token in re.findall(r"[a-zA-Z0-9_+\-.]+", value.lower()) if len(token) > 1]

