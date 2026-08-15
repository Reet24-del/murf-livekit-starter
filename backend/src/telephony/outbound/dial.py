"""Validate and dispatch a consented outbound Farm & Field call."""

import argparse
import asyncio
import sys
import uuid
from collections.abc import Callable, Sequence
from datetime import datetime

from dotenv import load_dotenv
from livekit import api

from db import is_outbound_opted_out
from telephony.outbound.call_config import (
    CallSafetyError,
    OutboundCallMetadata,
    validate_call_request,
)

load_dotenv(".env.local")

AGENT_NAME = "outbound-agent"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Place a consented Kisan Sahayak rain-advisory call."
    )
    parser.add_argument(
        "--to",
        required=True,
        help="Linphone username or E.164 number controlled by a consenting user.",
    )
    parser.add_argument(
        "--district",
        required=True,
        help="Indian district used for the live weather advisory.",
    )
    parser.add_argument(
        "--language",
        choices=("en", "hi"),
        default="en",
        help="Opening language: en for English or hi for Devanagari Hindi.",
    )
    parser.add_argument(
        "--crop",
        default=None,
        help="Optional crop name used to personalize the advisory.",
    )
    parser.add_argument(
        "--room",
        default=None,
        help="LiveKit room name. Defaults to a generated outbound room.",
    )
    parser.add_argument(
        "--consent-confirmed",
        action="store_true",
        help="Confirm the destination is yours or its recipient agreed to this call.",
    )
    parser.add_argument(
        "--override-quiet-hours",
        action="store_true",
        help="Allow a controlled demo outside 08:00-20:00 IST.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate the request without contacting LiveKit or placing a call.",
    )
    return parser


def metadata_from_args(args: argparse.Namespace) -> OutboundCallMetadata:
    return OutboundCallMetadata(
        destination=args.to.strip(),
        district=args.district.strip(),
        language=args.language,
        crop=args.crop.strip() if args.crop else None,
        consent_confirmed=args.consent_confirmed,
        quiet_hours_override=args.override_quiet_hours,
    )


def ensure_destination_not_opted_out(
    metadata: OutboundCallMetadata,
    lookup: Callable[[str], bool] = is_outbound_opted_out,
) -> None:
    if lookup(metadata.destination):
        raise CallSafetyError(
            "This outbound destination has opted out of future calls."
        )


async def dispatch_call(
    metadata: OutboundCallMetadata,
    room_name: str,
    *,
    livekit_api: api.LiveKitAPI | None = None,
    now: datetime | None = None,
) -> str:
    """Create a LiveKit room and dispatch the outbound voice worker."""
    validate_call_request(metadata, now=now)
    owns_client = livekit_api is None
    client = livekit_api or api.LiveKitAPI()
    try:
        await client.room.create_room(api.CreateRoomRequest(name=room_name))
        await client.agent_dispatch.create_dispatch(
            api.CreateAgentDispatchRequest(
                agent_name=AGENT_NAME,
                room=room_name,
                metadata=metadata.to_json(),
            )
        )
    finally:
        if owns_client:
            await client.aclose()
    return room_name


def main(
    argv: Sequence[str] | None = None,
    *,
    now: datetime | None = None,
) -> int:
    args = build_parser().parse_args(argv)
    metadata = metadata_from_args(args)
    try:
        validate_call_request(metadata, now=now)
        ensure_destination_not_opted_out(metadata)
    except CallSafetyError as error:
        print(f"Call blocked: {error}", file=sys.stderr)
        return 2

    room_name = args.room or f"outbound-{uuid.uuid4().hex[:8]}"
    if args.dry_run:
        print(
            f"Dry run passed for {metadata.destination}; no call was placed. "
            f"Worker={AGENT_NAME}, room={room_name}."
        )
        return 0

    try:
        asyncio.run(dispatch_call(metadata, room_name, now=now))
    except Exception as error:
        print(f"LiveKit dispatch failed: {error}", file=sys.stderr)
        return 1

    print(
        f"Dispatched {AGENT_NAME} to room '{room_name}' to call {metadata.destination}."
    )
    print("Watch the outbound worker terminal for call progress.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
