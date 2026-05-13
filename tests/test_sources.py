from paper_daily_reading_bot.config import AppConfig, DeepSeekConfig, EmailConfig, ResearchConfig, SourceConfig
from paper_daily_reading_bot.sources import build_sources
from paper_daily_reading_bot.sources.semantic_scholar import SemanticScholarSource


def test_build_sources_includes_semantic_scholar():
    config = AppConfig(
        research=ResearchConfig(
            directions=["LLM agents for science"],
            keywords=["large language model"],
        ),
        sources={
            "semantic_scholar": SourceConfig(
                enabled=True,
                max_results=50,
                endpoint="https://api.semanticscholar.org/graph/v1/paper/search",
            )
        },
        deepseek=DeepSeekConfig(),
        email=EmailConfig(enabled=False),
    )

    sources = build_sources(config)

    assert len(sources) == 1
    assert isinstance(sources[0], SemanticScholarSource)
