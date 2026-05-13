from datetime import datetime, timezone

from paper_daily_reading_bot.config import AppConfig, DeepSeekConfig, EmailConfig, ResearchConfig
from paper_daily_reading_bot.report import DeepSeekReportGenerator, _looks_complete_html


def test_report_request_uses_deepseek_chat_completions_shape():
    config = AppConfig(
        research=ResearchConfig(
            directions=["LLM paper reading"],
            keywords=["large language model"],
        ),
        sources={},
        deepseek=DeepSeekConfig(
            model="deepseek-test",
            max_tokens=1234,
            temperature=0.1,
        ),
        email=EmailConfig(enabled=False),
    )
    generator = DeepSeekReportGenerator(config)
    payload = generator._request_payload(
        [],
        datetime(2026, 5, 12, tzinfo=timezone.utc),
        datetime(2026, 5, 13, tzinfo=timezone.utc),
    )

    assert payload["model"] == "deepseek-test"
    assert payload["max_tokens"] == 1234
    assert payload["temperature"] == 0.1
    assert payload["messages"][0]["role"] == "system"
    assert "thinking" not in payload


def test_html_completion_check_rejects_truncated_content():
    assert _looks_complete_html("<html><body>ok</body></html>") is True
    assert _looks_complete_html("<div>half") is False
