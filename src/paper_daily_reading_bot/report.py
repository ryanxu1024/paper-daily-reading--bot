from __future__ import annotations

from datetime import datetime
from typing import List
import json
import os
import re

import requests

from paper_daily_reading_bot.config import AppConfig
from paper_daily_reading_bot.models import ScoredPaper


class ReportGenerationError(RuntimeError):
    """Raised when the DeepSeek report generation step fails."""


class DeepSeekReportGenerator:
    def __init__(self, config: AppConfig) -> None:
        self.config = config

    def generate(self, papers: List[ScoredPaper], since: datetime, until: datetime) -> str:
        api_key = os.getenv(self.config.deepseek.api_key_env)
        if not api_key:
            raise ReportGenerationError(
                f"{self.config.deepseek.api_key_env} is required to generate the report"
            )

        try:
            response = requests.post(
                self._endpoint(),
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json=self._request_payload(papers, since, until),
                timeout=self.config.deepseek.timeout_seconds,
            )
            if response.status_code >= 400:
                raise ReportGenerationError(
                    f"DeepSeek API failed with HTTP {response.status_code}: {response.text}"
                )
            data = response.json()
            html = (
                ((data.get("choices") or [{}])[0].get("message") or {}).get("content")
                or ""
            )
            if not html.strip():
                raise ReportGenerationError("DeepSeek returned an empty report")
            if not _looks_complete_html(html):
                raise ReportGenerationError(
                    "DeepSeek response appears truncated. Increase deepseek.max_tokens "
                    "or reduce research.max_papers."
                )
            return html.strip()
        except ReportGenerationError:
            raise
        except Exception as exc:  # noqa: BLE001
            raise ReportGenerationError(f"DeepSeek API request failed: {exc}") from exc

    def _endpoint(self) -> str:
        return self.config.deepseek.resolved_base_url().rstrip("/") + "/chat/completions"

    def _request_payload(self, papers: List[ScoredPaper], since: datetime, until: datetime):
        payload = {
            "research_directions": self.config.research.directions,
            "keywords": self.config.research.keywords,
            "time_window_utc": {
                "since": since.isoformat(),
                "until": until.isoformat(),
            },
            "max_papers": self.config.research.max_papers,
            "papers": [paper.to_prompt_dict() for paper in papers],
        }
        system_prompt = (
            "你是一名严谨的科研论文阅读助理。请根据输入论文生成中文 HTML 邮件日报。"
            "输出必须是完整 HTML 片段，不要使用 Markdown 代码块。"
            "不要编造论文不存在的信息；缺失字段请标注“未提供”。"
        )
        user_prompt = (
            "请生成每日论文自动监测日报，要求：\n"
            "1. 对每篇论文包含：论文题目、作者、来源或期刊名称、发布时间、链接或 DOI、"
            "关键词、英文摘要、中文摘要翻译、与研究方向的相关性分析、推荐阅读优先级。\n"
            "2. 按推荐阅读优先级和综合分排序，最多展示输入中的论文。\n"
            "3. 为避免邮件被截断，每篇论文请严格控制篇幅：英文摘要最多 90 个英文词；"
            "中文摘要翻译最多 120 个汉字；相关性分析最多 90 个汉字。\n"
            "4. 最后基于当日论文总结 3-5 条未来可研究的技术路线，每条最多 80 个汉字。\n"
            "5. 使用适合邮件阅读的 HTML：清晰标题、表格或分节、简洁内联样式。\n"
            "6. 必须输出完整 HTML，末尾必须包含 </html>。\n\n"
            f"输入 JSON：\n{json.dumps(payload, ensure_ascii=False, indent=2)}"
        )
        request_payload = {
            "model": self.config.deepseek.resolved_model(),
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "max_tokens": self.config.deepseek.max_tokens,
            "temperature": self.config.deepseek.temperature,
            "stream": False,
        }
        thinking = self._thinking_payload()
        if thinking:
            request_payload["thinking"] = thinking
        if self.config.deepseek.reasoning_effort:
            request_payload["reasoning_effort"] = self.config.deepseek.reasoning_effort
        return request_payload

    def _thinking_payload(self):
        thinking_type = self.config.deepseek.thinking_type
        if not thinking_type:
            return None
        return {"type": thinking_type}


def _looks_complete_html(html: str) -> bool:
    normalized = html.strip().lower()
    if "</html>" in normalized:
        return True
    if re.search(r"</(body|section|article|div)>\s*$", normalized):
        return True
    return False
