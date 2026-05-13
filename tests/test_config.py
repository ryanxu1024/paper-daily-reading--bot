from pathlib import Path

from paper_daily_reading_bot.config import load_config


def test_load_config_resolves_email_env(tmp_path, monkeypatch):
    monkeypatch.setenv("SMTP_HOST", "smtp.env.example.com")
    monkeypatch.setenv("SMTP_SENDER", "bot@example.com")
    monkeypatch.setenv("SMTP_RECIPIENTS", "a@example.com,b@example.com")
    config_file = tmp_path / "config.yaml"
    config_file.write_text(
        """
research:
  directions: ["LLM for science"]
  keywords: ["language model"]
sources:
  arxiv:
    enabled: true
email:
  smtp_host: smtp.example.com
  sender_env: SMTP_SENDER
  recipients_env: SMTP_RECIPIENTS
deepseek:
  model: deepseek-test
""",
        encoding="utf-8",
    )

    config = load_config(str(config_file))

    assert config.research.lookback_hours == 24
    assert config.sources["arxiv"].enabled is True
    assert config.deepseek.resolved_model() == "deepseek-test"
    assert config.email.resolved_smtp_host() == "smtp.env.example.com"
    assert config.email.resolved_sender() == "bot@example.com"
    assert config.email.resolved_recipients() == ["a@example.com", "b@example.com"]


def test_example_config_is_valid():
    root = Path(__file__).resolve().parents[1]
    config = load_config(str(root / "config.example.yaml"))

    assert config.research.max_papers == 10
    assert "arxiv" in config.sources
    assert "openalex" in config.sources
