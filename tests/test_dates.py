from paper_daily_reading_bot.sources.arxiv import ArxivSource
from paper_daily_reading_bot.sources.rss import RSSFeedSource


def test_arxiv_parses_iso_atom_datetime():
    value = ArxivSource._parse_feed_datetime("2026-05-13T08:30:00Z")

    assert value is not None
    assert value.year == 2026
    assert value.tzinfo is not None


def test_rss_parser_accepts_iso_datetime_fallback():
    value = RSSFeedSource._parse_feed_datetime("2026-05-13T08:30:00Z")

    assert value is not None
    assert value.year == 2026
    assert value.tzinfo is not None
