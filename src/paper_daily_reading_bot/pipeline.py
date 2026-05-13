from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import List, Optional
import logging

from paper_daily_reading_bot.config import AppConfig
from paper_daily_reading_bot.emailer import send_html_email
from paper_daily_reading_bot.models import Paper, ScoredPaper
from paper_daily_reading_bot.report import DeepSeekReportGenerator
from paper_daily_reading_bot.scoring import PaperRanker, deduplicate_papers
from paper_daily_reading_bot.sources import build_sources
from paper_daily_reading_bot.sources.base import SourceError
from paper_daily_reading_bot.utils import ensure_utc


LOGGER = logging.getLogger(__name__)


@dataclass
class PipelineResult:
    html: str
    collected_count: int
    deduplicated_count: int
    selected_papers: List[ScoredPaper]
    since: datetime
    until: datetime
    email_sent: bool


def run_pipeline(
    config: AppConfig,
    send_email: bool = True,
    output_path: Optional[str] = None,
    now: Optional[datetime] = None,
) -> PipelineResult:
    until = ensure_utc(now) if now else datetime.now(timezone.utc)
    since = until - timedelta(hours=config.research.lookback_hours)

    papers = collect_papers(config, since, until)
    deduped = deduplicate_papers(papers)
    selected = PaperRanker(config.research).select_top(deduped)

    LOGGER.info(
        "Collected %d papers, %d after deduplication, selected %d",
        len(papers),
        len(deduped),
        len(selected),
    )

    html = DeepSeekReportGenerator(config).generate(selected, since, until)
    if output_path:
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        output_file.write_text(html, encoding="utf-8")
        LOGGER.info("Wrote report HTML to %s", output_file)

    email_sent = False
    if send_email and config.email.enabled:
        subject = build_subject(config, until)
        send_html_email(config.email, subject, html)
        email_sent = True
        LOGGER.info("Sent report email to %s", ", ".join(config.email.resolved_recipients()))
    else:
        LOGGER.info("Email sending skipped")

    return PipelineResult(
        html=html,
        collected_count=len(papers),
        deduplicated_count=len(deduped),
        selected_papers=selected,
        since=since,
        until=until,
        email_sent=email_sent,
    )


def collect_papers(config: AppConfig, since: datetime, until: datetime) -> List[Paper]:
    all_papers: List[Paper] = []
    for source in build_sources(config):
        try:
            LOGGER.info("Fetching papers from %s", source.name)
            source_papers = source.fetch(since, until)
            LOGGER.info("%s returned %d papers", source.name, len(source_papers))
            all_papers.extend(source_papers)
        except SourceError as exc:
            LOGGER.warning("Source %s skipped: %s", source.name, exc)
        except Exception as exc:  # noqa: BLE001
            LOGGER.exception("Source %s failed and will be skipped: %s", source.name, exc)
    return all_papers


def build_subject(config: AppConfig, until: datetime) -> str:
    local_until = until.astimezone(_timezone(config.timezone))
    return f"{config.email.subject_prefix} - {local_until:%Y-%m-%d}"


def _timezone(name: str):
    try:
        from zoneinfo import ZoneInfo

        return ZoneInfo(name)
    except Exception:  # noqa: BLE001
        return timezone(timedelta(hours=8))
