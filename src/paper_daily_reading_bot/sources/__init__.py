from __future__ import annotations

from typing import List

from paper_daily_reading_bot.config import AppConfig
from paper_daily_reading_bot.sources.arxiv import ArxivSource
from paper_daily_reading_bot.sources.base import PaperSource
from paper_daily_reading_bot.sources.elsevier import ElsevierSource
from paper_daily_reading_bot.sources.ieee import IEEESource
from paper_daily_reading_bot.sources.openalex import OpenAlexSource
from paper_daily_reading_bot.sources.rss import RSSFeedSource
from paper_daily_reading_bot.sources.semantic_scholar import SemanticScholarSource


def build_sources(config: AppConfig) -> List[PaperSource]:
    sources: List[PaperSource] = []
    for name, source_config in config.sources.items():
        if not source_config.enabled:
            continue
        if name == "arxiv":
            sources.append(ArxivSource(source_config, config.research))
        elif name == "openalex":
            sources.append(OpenAlexSource(source_config, config.research))
        elif name == "semantic_scholar":
            sources.append(SemanticScholarSource(source_config, config.research))
        elif name == "elsevier":
            sources.append(ElsevierSource(source_config, config.research))
        elif name == "ieee":
            sources.append(IEEESource(source_config, config.research))
        elif name in {"nature", "science"}:
            sources.append(RSSFeedSource(name, source_config, config.research))
    return sources
