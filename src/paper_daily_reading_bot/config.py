from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional
import os
import re

import yaml


ENV_PATTERN = re.compile(r"\$\{([A-Z0-9_]+)\}")


class ConfigError(ValueError):
    """Raised when the application configuration is invalid."""


@dataclass
class ResearchConfig:
    directions: List[str]
    keywords: List[str]
    negative_keywords: List[str] = field(default_factory=list)
    max_papers: int = 10
    lookback_hours: int = 24


@dataclass
class SourceConfig:
    enabled: bool = True
    max_results: int = 50
    api_key_env: Optional[str] = None
    query: Optional[str] = None
    endpoint: Optional[str] = None
    categories: List[str] = field(default_factory=list)
    rss_urls: List[str] = field(default_factory=list)
    timeout_seconds: int = 30


@dataclass
class DeepSeekConfig:
    api_key_env: str = "DEEPSEEK_API_KEY"
    base_url: str = "https://api.deepseek.com"
    base_url_env: Optional[str] = "DEEPSEEK_BASE_URL"
    model: str = "deepseek-v4-flash"
    model_env: Optional[str] = "DEEPSEEK_MODEL"
    max_tokens: int = 6000
    temperature: float = 0.2
    thinking_type: Optional[str] = None
    reasoning_effort: Optional[str] = None
    timeout_seconds: int = 120

    def resolved_base_url(self) -> str:
        if self.base_url_env and os.getenv(self.base_url_env):
            return os.environ[self.base_url_env]
        return self.base_url

    def resolved_model(self) -> str:
        if self.model_env and os.getenv(self.model_env):
            return os.environ[self.model_env]
        return self.model


@dataclass
class EmailConfig:
    enabled: bool = True
    smtp_host: str = ""
    smtp_host_env: Optional[str] = "SMTP_HOST"
    smtp_port: int = 587
    use_tls: bool = True
    username_env: Optional[str] = "SMTP_USERNAME"
    password_env: Optional[str] = "SMTP_PASSWORD"
    sender: str = ""
    sender_env: Optional[str] = "SMTP_SENDER"
    recipients: List[str] = field(default_factory=list)
    recipients_env: Optional[str] = "SMTP_RECIPIENTS"
    subject_prefix: str = "每日论文阅读日报"

    def resolved_smtp_host(self) -> str:
        if self.smtp_host_env and os.getenv(self.smtp_host_env):
            return os.environ[self.smtp_host_env]
        return self.smtp_host

    def resolved_sender(self) -> str:
        if self.sender_env and os.getenv(self.sender_env):
            return os.environ[self.sender_env]
        return self.sender

    def resolved_recipients(self) -> List[str]:
        if self.recipients_env and os.getenv(self.recipients_env):
            return [
                item.strip()
                for item in os.environ[self.recipients_env].split(",")
                if item.strip()
            ]
        return self.recipients

    def resolved_username(self) -> Optional[str]:
        if self.username_env:
            return os.getenv(self.username_env)
        return None

    def resolved_password(self) -> Optional[str]:
        if self.password_env:
            return os.getenv(self.password_env)
        return None


@dataclass
class AppConfig:
    research: ResearchConfig
    sources: Dict[str, SourceConfig]
    deepseek: DeepSeekConfig
    email: EmailConfig
    timezone: str = "Asia/Shanghai"
    log_level: str = "INFO"


def _expand_env(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _expand_env(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_expand_env(item) for item in value]
    if isinstance(value, str):
        return ENV_PATTERN.sub(lambda match: os.getenv(match.group(1), ""), value)
    return value


def _as_list(value: Any, field_name: str) -> List[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        return [str(item) for item in value]
    raise ConfigError(f"{field_name} must be a string or a list of strings")


def load_config(path: str) -> AppConfig:
    config_path = Path(path)
    if not config_path.exists():
        raise ConfigError(f"config file not found: {config_path}")

    with config_path.open("r", encoding="utf-8") as fh:
        raw = yaml.safe_load(fh) or {}
    raw = _expand_env(raw)

    research_raw = raw.get("research") or {}
    directions = _as_list(research_raw.get("directions"), "research.directions")
    keywords = _as_list(research_raw.get("keywords"), "research.keywords")
    if not directions:
        raise ConfigError("research.directions must contain at least one direction")
    if not keywords:
        raise ConfigError("research.keywords must contain at least one keyword")

    research = ResearchConfig(
        directions=directions,
        keywords=keywords,
        negative_keywords=_as_list(
            research_raw.get("negative_keywords"), "research.negative_keywords"
        ),
        max_papers=int(research_raw.get("max_papers", 10)),
        lookback_hours=int(research_raw.get("lookback_hours", 24)),
    )

    source_configs: Dict[str, SourceConfig] = {}
    for name, source_raw in (raw.get("sources") or {}).items():
        source_raw = source_raw or {}
        source_configs[name] = SourceConfig(
            enabled=bool(source_raw.get("enabled", True)),
            max_results=int(source_raw.get("max_results", 50)),
            api_key_env=source_raw.get("api_key_env"),
            query=source_raw.get("query"),
            endpoint=source_raw.get("endpoint"),
            categories=_as_list(source_raw.get("categories"), f"sources.{name}.categories"),
            rss_urls=_as_list(source_raw.get("rss_urls"), f"sources.{name}.rss_urls"),
            timeout_seconds=int(source_raw.get("timeout_seconds", 30)),
        )

    deepseek_raw = raw.get("deepseek") or {}
    deepseek_config = DeepSeekConfig(
        api_key_env=deepseek_raw.get("api_key_env", "DEEPSEEK_API_KEY"),
        base_url=deepseek_raw.get("base_url", "https://api.deepseek.com"),
        base_url_env=deepseek_raw.get("base_url_env", "DEEPSEEK_BASE_URL"),
        model=deepseek_raw.get("model", "deepseek-v4-flash"),
        model_env=deepseek_raw.get("model_env", "DEEPSEEK_MODEL"),
        max_tokens=int(deepseek_raw.get("max_tokens", 6000)),
        temperature=float(deepseek_raw.get("temperature", 0.2)),
        thinking_type=deepseek_raw.get("thinking_type"),
        reasoning_effort=deepseek_raw.get("reasoning_effort"),
        timeout_seconds=int(deepseek_raw.get("timeout_seconds", 120)),
    )

    email_raw = raw.get("email") or {}
    email = EmailConfig(
        enabled=bool(email_raw.get("enabled", True)),
        smtp_host=email_raw.get("smtp_host", ""),
        smtp_host_env=email_raw.get("smtp_host_env", "SMTP_HOST"),
        smtp_port=int(email_raw.get("smtp_port", 587)),
        use_tls=bool(email_raw.get("use_tls", True)),
        username_env=email_raw.get("username_env", "SMTP_USERNAME"),
        password_env=email_raw.get("password_env", "SMTP_PASSWORD"),
        sender=email_raw.get("sender", ""),
        sender_env=email_raw.get("sender_env", "SMTP_SENDER"),
        recipients=_as_list(email_raw.get("recipients"), "email.recipients"),
        recipients_env=email_raw.get("recipients_env", "SMTP_RECIPIENTS"),
        subject_prefix=email_raw.get("subject_prefix", "每日论文阅读日报"),
    )

    return AppConfig(
        research=research,
        sources=source_configs,
        deepseek=deepseek_config,
        email=email,
        timezone=raw.get("timezone", "Asia/Shanghai"),
        log_level=raw.get("log_level", "INFO"),
    )
