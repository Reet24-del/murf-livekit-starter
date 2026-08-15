"""JSON bridge between the Next.js analytics API and SQLite."""

from __future__ import annotations

import argparse
import json

from call_analytics import CHANNELS, LANGUAGES, OUTCOMES, get_call_analytics


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Kisan Sahayak call analytics")
    subparsers = parser.add_subparsers(dest="command", required=True)
    summary = subparsers.add_parser("summary")
    summary.add_argument("--days", type=int, choices=(1, 7, 30, 90), default=7)
    summary.add_argument("--channel", choices=("all", *sorted(CHANNELS)), default="all")
    summary.add_argument(
        "--language", choices=("all", *sorted(LANGUAGES)), default="all"
    )
    summary.add_argument("--outcome", choices=("all", *sorted(OUTCOMES)), default="all")
    summary.add_argument("--db-path")
    return parser


def main() -> None:
    arguments = build_parser().parse_args()
    payload = get_call_analytics(
        days=arguments.days,
        channel=arguments.channel,
        language=arguments.language,
        outcome=arguments.outcome,
        db_path=arguments.db_path,
    )
    print(json.dumps(payload, separators=(",", ":")))


if __name__ == "__main__":
    main()
