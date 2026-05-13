from __future__ import annotations

import argparse
import sys

from paper_daily_reading_bot.config import ConfigError, load_config
from paper_daily_reading_bot.pipeline import run_pipeline
from paper_daily_reading_bot.utils import setup_logging


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Monitor recent papers and send a Chinese daily reading report."
    )
    parser.add_argument("--config", default="config.yaml", help="Path to config.yaml")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Generate the report but do not send email",
    )
    parser.add_argument("--output", help="Write generated HTML to this path")
    parser.add_argument("--log-level", help="Override log level")
    return parser


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    try:
        config = load_config(args.config)
        if args.log_level:
            config.log_level = args.log_level
        setup_logging(config.log_level)
        result = run_pipeline(
            config,
            send_email=not args.dry_run,
            output_path=args.output,
        )
        print(
            "Done: "
            f"collected={result.collected_count}, "
            f"deduplicated={result.deduplicated_count}, "
            f"selected={len(result.selected_papers)}, "
            f"email_sent={result.email_sent}"
        )
        return 0
    except ConfigError as exc:
        print(f"Configuration error: {exc}", file=sys.stderr)
        return 2
    except Exception as exc:  # noqa: BLE001
        print(f"Run failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
