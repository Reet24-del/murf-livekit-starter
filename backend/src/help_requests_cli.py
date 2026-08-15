"""JSON command bridge for the local Help Requests dashboard."""

import argparse
import json
import sys

from escalation import (
    EscalationValidationError,
    list_help_requests,
    update_help_request_status,
)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="help_requests_cli")
    commands = parser.add_subparsers(dest="command", required=True)

    list_parser = commands.add_parser("list")
    list_parser.add_argument("--status", choices=("open", "in_progress", "resolved"))
    list_parser.add_argument("--urgency", choices=("high", "medium"))
    list_parser.add_argument("--db-path")

    update_parser = commands.add_parser("update")
    update_parser.add_argument("--reference-id", required=True)
    update_parser.add_argument(
        "--status",
        required=True,
        choices=("open", "in_progress", "resolved"),
    )
    update_parser.add_argument("--db-path")
    return parser


def main(arguments: list[str] | None = None) -> int:
    args = _parser().parse_args(arguments)
    try:
        if args.command == "list":
            requests = list_help_requests(
                status=args.status,
                urgency=args.urgency,
                db_path=args.db_path,
            )
            print(json.dumps({"requests": requests}, ensure_ascii=False))
            return 0

        request = update_help_request_status(
            args.reference_id,
            args.status,
            db_path=args.db_path,
        )
        if request is None:
            print("Help request was not found.", file=sys.stderr)
            return 1
        print(json.dumps({"request": request}, ensure_ascii=False))
        return 0
    except EscalationValidationError as error:
        print(str(error), file=sys.stderr)
        return 2
    except (OSError, ValueError):
        print("Help requests are unavailable right now.", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
