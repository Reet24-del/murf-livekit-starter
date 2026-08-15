from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

from telephony.outbound.call_config import CallSafetyError, OutboundCallMetadata
from telephony.outbound.dial import (
    AGENT_NAME,
    build_parser,
    dispatch_call,
    ensure_destination_not_opted_out,
    main,
    metadata_from_args,
)

IST = ZoneInfo("Asia/Kolkata")
ALLOWED_TIME = datetime(2026, 8, 11, 14, 0, tzinfo=IST)


def test_main_refuses_missing_consent_before_network(capsys) -> None:
    """Catch the CLI dispatching when the operator omitted consent."""
    result = main(
        ["--to", "farmer.demo", "--district", "Lucknow"],
        now=ALLOWED_TIME,
    )

    assert result == 2
    assert "consent" in capsys.readouterr().err.lower()


def test_main_refuses_invalid_destination_before_network(capsys) -> None:
    """Catch malformed input reaching LiveKit instead of failing locally."""
    result = main(
        [
            "--to",
            "sip:farmer@sip.linphone.org",
            "--district",
            "Lucknow",
            "--consent-confirmed",
        ],
        now=ALLOWED_TIME,
    )

    assert result == 2
    assert "destination" in capsys.readouterr().err.lower()


def test_parser_builds_complete_dispatch_metadata() -> None:
    """Catch a CLI option being omitted from dispatch metadata."""
    args = build_parser().parse_args(
        [
            "--to",
            "farmer.demo",
            "--district",
            "Lucknow",
            "--language",
            "hi",
            "--crop",
            "tomato",
            "--consent-confirmed",
            "--override-quiet-hours",
        ]
    )

    assert metadata_from_args(args) == OutboundCallMetadata(
        destination="farmer.demo",
        district="Lucknow",
        language="hi",
        crop="tomato",
        consent_confirmed=True,
        quiet_hours_override=True,
    )


def test_opted_out_destination_is_rejected() -> None:
    """Catch a saved stop request being ignored by the dial workflow."""
    metadata = OutboundCallMetadata(
        destination="farmer.demo",
        district="Lucknow",
        consent_confirmed=True,
    )

    with pytest.raises(CallSafetyError, match="opted out"):
        ensure_destination_not_opted_out(metadata, lookup=lambda _: True)


class RecordingEndpoint:
    def __init__(self) -> None:
        self.requests = []

    async def create_room(self, request) -> None:
        self.requests.append(request)

    async def create_dispatch(self, request) -> None:
        self.requests.append(request)


class RecordingLiveKitAPI:
    def __init__(self) -> None:
        self.room = RecordingEndpoint()
        self.agent_dispatch = RecordingEndpoint()
        self.closed = False

    async def aclose(self) -> None:
        self.closed = True


@pytest.mark.asyncio
async def test_dispatch_call_creates_room_and_exact_agent_metadata() -> None:
    """Catch dispatch targeting the wrong worker or dropping call metadata."""
    client = RecordingLiveKitAPI()
    metadata = OutboundCallMetadata(
        destination="farmer.demo",
        district="Lucknow",
        language="hi",
        crop="tomato",
        consent_confirmed=True,
    )

    room_name = await dispatch_call(
        metadata,
        "outbound-test-room",
        livekit_api=client,
        now=ALLOWED_TIME,
    )

    room_request = client.room.requests[0]
    dispatch_request = client.agent_dispatch.requests[0]
    assert room_name == "outbound-test-room"
    assert room_request.name == "outbound-test-room"
    assert dispatch_request.agent_name == AGENT_NAME
    assert dispatch_request.room == "outbound-test-room"
    assert OutboundCallMetadata.from_json(dispatch_request.metadata) == metadata
    assert client.closed is False
