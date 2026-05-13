from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional
import re


def normalize_title(value: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9]+", " ", value.lower())).strip()


@dataclass
class Paper:
    title: str
    authors: List[str]
    source: str
    published_at: Optional[datetime]
    updated_at: Optional[datetime]
    url: Optional[str]
    doi: Optional[str]
    abstract: str
    journal: Optional[str] = None
    keywords: List[str] = field(default_factory=list)
    source_id: Optional[str] = None
    raw: Dict[str, Any] = field(default_factory=dict)

    @property
    def display_source(self) -> str:
        if self.journal:
            return f"{self.source} / {self.journal}"
        return self.source

    @property
    def event_date(self) -> Optional[datetime]:
        return self.updated_at or self.published_at

    def identity_key(self) -> str:
        if self.doi:
            return "doi:" + self.doi.lower().strip()
        if self.source_id:
            return f"{self.source}:{self.source_id}".lower().strip()
        return "title:" + normalize_title(self.title)

    def to_prompt_dict(self) -> Dict[str, Any]:
        event_date = self.event_date.isoformat() if self.event_date else ""
        return {
            "title": self.title,
            "authors": self.authors,
            "source": self.display_source,
            "published_at": self.published_at.isoformat() if self.published_at else "",
            "updated_at": self.updated_at.isoformat() if self.updated_at else "",
            "event_date": event_date,
            "url": self.url,
            "doi": self.doi,
            "keywords": self.keywords,
            "abstract": self.abstract,
        }


@dataclass
class ScoredPaper:
    paper: Paper
    keyword_score: float
    semantic_score: float
    total_score: float
    matched_keywords: List[str]

    @property
    def priority(self) -> str:
        if self.total_score >= 0.72:
            return "高"
        if self.total_score >= 0.48:
            return "中"
        return "低"

    def to_prompt_dict(self) -> Dict[str, Any]:
        data = self.paper.to_prompt_dict()
        data.update(
            {
                "matched_keywords": self.matched_keywords,
                "keyword_score": round(self.keyword_score, 4),
                "semantic_score": round(self.semantic_score, 4),
                "total_score": round(self.total_score, 4),
                "recommended_priority": self.priority,
            }
        )
        return data
