from datetime import datetime, timezone

from paper_daily_reading_bot.config import ResearchConfig
from paper_daily_reading_bot.models import Paper
from paper_daily_reading_bot.scoring import PaperRanker, deduplicate_papers


def make_paper(title, abstract, doi=None):
    return Paper(
        title=title,
        authors=["Ada Lovelace"],
        source="test",
        published_at=datetime(2026, 5, 13, tzinfo=timezone.utc),
        updated_at=None,
        url="https://example.com",
        doi=doi,
        abstract=abstract,
        journal="Example Journal",
    )


def test_deduplicate_prefers_same_doi():
    first = make_paper("A paper about LLM agents", "", doi="10.1234/example")
    second = make_paper(
        "A paper about LLM agents",
        "Longer abstract about large language model agents.",
        doi="10.1234/example",
    )

    deduped = deduplicate_papers([first, second])

    assert len(deduped) == 1
    assert deduped[0].abstract


def test_ranker_promotes_keyword_and_semantic_match():
    research = ResearchConfig(
        directions=["large language model agents for scientific discovery"],
        keywords=["large language model", "scientific discovery"],
        max_papers=1,
    )
    ranker = PaperRanker(research)
    relevant = make_paper(
        "Large language model agents accelerate scientific discovery",
        "We study retrieval augmented workflows for autonomous paper reading.",
    )
    irrelevant = make_paper(
        "New battery electrolyte additives",
        "This chemistry paper focuses on electrochemical stability.",
    )

    selected = ranker.select_top([irrelevant, relevant])

    assert len(selected) == 1
    assert selected[0].paper is relevant
    assert selected[0].matched_keywords
