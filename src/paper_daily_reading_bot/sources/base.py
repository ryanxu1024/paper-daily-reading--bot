from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Dict, List, Optional
import logging

import requests

from paper_daily_reading_bot.config import ResearchConfig, SourceConfig
from paper_daily_reading_bot.models import Paper


class SourceError(RuntimeError):
    """Raised when a paper source cannot be queried."""


class SourceRateLimitError(SourceError):
    """Raised when a paper source rate-limits the request."""


class PaperSource(ABC):
    name = "base"

    def __init__(self, config: SourceConfig, research: ResearchConfig) -> None:
        self.config = config
        self.research = research
        self.logger = logging.getLogger(f"paper_daily_reading_bot.sources.{self.name}")

    @abstractmethod
    def fetch(self, since: datetime, until: datetime) -> List[Paper]:
        """Fetch papers published or updated in the requested time window."""

    def session(self, headers: Optional[Dict[str, str]] = None) -> requests.Session:
        session = requests.Session()
        session.headers.update(
            {
                "User-Agent": (
                    "paper-daily-reading-bot/0.1 "
                    "(mailto:configure-your-email@example.com)"
                )
            }
        )
        if headers:
            session.headers.update(headers)
        return session
