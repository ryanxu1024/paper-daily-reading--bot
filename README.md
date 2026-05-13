# paper-daily-reading--bot

每日论文自动监测与中文 HTML 邮件日报机器人。

## 功能

- 从 `config.yaml` 读取研究方向、关键词、论文源、邮箱配置。
- 检索最近 24 小时内发布或更新的论文。
- 支持 arXiv API、OpenAlex API、Elsevier API、IEEE Xplore Metadata API，以及 Nature / Science RSS。
- 按关键词匹配和语义相关性打分，去重后最多保留 10 篇。
- 使用 DeepSeek API 生成中文日报，并通过 SMTP 发送 HTML 邮件。
- 提供 GitHub Actions，每天北京时间 08:30 自动运行。

## 快速开始

```bash
cd paper-daily-reading--bot
python -m pip install -e .[test]
cp config.example.yaml config.yaml
```

编辑 `config.yaml` 中的 `research.directions`、`research.keywords` 和论文源配置。所有密钥均从环境变量读取，不要写进配置文件或代码。

必需环境变量：

```bash
export DEEPSEEK_API_KEY="..."
export SMTP_HOST="smtp.gmail.com"
export SMTP_USERNAME="..."
export SMTP_PASSWORD="..."
export SMTP_SENDER="bot@example.com"
export SMTP_RECIPIENTS="you@example.com,team@example.com"
```

可选环境变量：

```bash
export DEEPSEEK_MODEL="deepseek-v4-flash"
export DEEPSEEK_BASE_URL="https://api.deepseek.com"
export SEMANTIC_SCHOLAR_API_KEY="..."
export ELSEVIER_API_KEY="..."
export IEEE_API_KEY="..."
```

运行：

```bash
paper-daily-reading-bot --config config.yaml
```

只生成 HTML、不发送邮件：

```bash
paper-daily-reading-bot --config config.yaml --dry-run --output reports/latest.html
```

## 配置说明

`research.lookback_hours` 默认是 `24`。`sources` 中每个源都可以单独启停：

- `arxiv`: 使用 arXiv API，支持 `categories` 和自定义 `query`。
- `openalex`: 使用 OpenAlex Works API，无需密钥。
- `elsevier`: 使用 Scopus Search API，需要 `ELSEVIER_API_KEY`。
- `ieee`: 使用 IEEE Xplore Metadata API，需要 `IEEE_API_KEY`。
- `nature` / `science`: 使用 RSS，`rss_urls` 可替换为具体子刊或频道。

语义相关性使用本地 TF-IDF 相似度，不需要额外 embedding API。

Semantic Scholar 公共接口容易限流。如果日志出现 HTTP 429，请设置 `SEMANTIC_SCHOLAR_API_KEY`，或把 `sources.semantic_scholar.enabled` 改成 `false`。只保留 10 篇日报时，`sources.semantic_scholar.max_results` 建议先设为 `50`。

## GitHub Actions

项目已包含 `.github/workflows/daily.yml`，计划任务为：

```yaml
cron: "30 0 * * *"
```

这对应北京时间每天上午 8 点半。请在仓库中配置以下 Secrets：

- `DEEPSEEK_API_KEY`
- `SMTP_HOST`
- `SMTP_USERNAME`
- `SMTP_PASSWORD`
- `SMTP_SENDER`
- `SMTP_RECIPIENTS`
- `SEMANTIC_SCHOLAR_API_KEY`
- `ELSEVIER_API_KEY`，如果启用 Elsevier
- `IEEE_API_KEY`，如果启用 IEEE

如果仓库根目录存在 `config.yaml`，Actions 会使用它；否则使用 `config.example.yaml`。

## 测试

```bash
python -m pytest
```

## 安全注意

不要把 API Key、SMTP 密码或个人邮箱密码写入代码、提交到 Git，或放入公开配置文件。建议使用 GitHub Secrets、系统环境变量或本地 `.env` 管理工具注入运行环境。
