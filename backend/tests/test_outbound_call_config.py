from dataclasses import replace
from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

from telephony.outbound.call_config import (
    CallSafetyError,
    OutboundCallMetadata,
    opening_greeting,
    turn_language,
    turn_language_instruction,
    validate_call_request,
)

IST = ZoneInfo("Asia/Kolkata")


def valid_metadata(**changes) -> OutboundCallMetadata:
    metadata = OutboundCallMetadata(
        destination="farmer.demo",
        district="Lucknow",
        language="hi",
        crop="tomato",
        consent_confirmed=True,
        quiet_hours_override=False,
    )
    return replace(metadata, **changes)


def test_metadata_round_trip_preserves_dispatch_contract() -> None:
    """Catch dispatch JSON that loses a safety or advisory field."""
    metadata = valid_metadata()

    assert OutboundCallMetadata.from_json(metadata.to_json()) == metadata


@pytest.mark.parametrize("destination", ["farmer.demo", "+919876543210"])
def test_valid_linphone_and_e164_destinations_are_accepted(destination: str) -> None:
    """Catch validation that breaks either supported SIP trunk style."""
    validate_call_request(
        valid_metadata(destination=destination),
        now=datetime(2026, 8, 11, 14, 0, tzinfo=IST),
    )


@pytest.mark.parametrize(
    "destination",
    ["", "ab", "sip:farmer@sip.linphone.org", "farmer demo", "+0123456789"],
)
def test_malformed_destination_is_rejected(destination: str) -> None:
    """Catch malformed SIP targets reaching LiveKit dispatch."""
    with pytest.raises(CallSafetyError, match="destination"):
        validate_call_request(
            valid_metadata(destination=destination),
            now=datetime(2026, 8, 11, 14, 0, tzinfo=IST),
        )


def test_missing_consent_is_rejected_before_dispatch() -> None:
    """Catch calls being placed without explicit operator confirmation."""
    with pytest.raises(CallSafetyError, match="consent"):
        validate_call_request(
            valid_metadata(consent_confirmed=False),
            now=datetime(2026, 8, 11, 14, 0, tzinfo=IST),
        )


def test_quiet_hours_are_blocked_unless_deliberately_overridden() -> None:
    """Catch accidental night calls while preserving controlled demo override."""
    late = datetime(2026, 8, 11, 21, 0, tzinfo=IST)

    with pytest.raises(CallSafetyError, match="08:00 and 20:00"):
        validate_call_request(valid_metadata(), now=late)

    validate_call_request(
        valid_metadata(quiet_hours_override=True),
        now=late,
    )


def test_quiet_hours_boundary_allows_0800_and_blocks_2000() -> None:
    """Catch an off-by-one error at the configured calling window boundary."""
    validate_call_request(
        valid_metadata(),
        now=datetime(2026, 8, 11, 8, 0, tzinfo=IST),
    )

    with pytest.raises(CallSafetyError, match="08:00 and 20:00"):
        validate_call_request(
            valid_metadata(),
            now=datetime(2026, 8, 11, 20, 0, tzinfo=IST),
        )


def test_openings_disclose_identity_reason_and_opt_out_in_two_sentences() -> None:
    """Catch a recipient hearing an unexplained or non-compliant cold open."""
    english = opening_greeting("en")
    hindi = opening_greeting("hi")

    assert english.count(".") == 2
    assert "Kisan Sahayak" in english
    assert "rain and crop-safety advisory" in english
    assert "stop calls" in english.lower()
    assert hindi.count("।") == 2
    assert "किसान सहायक" in hindi
    assert "बारिश तथा फसल-सुरक्षा" in hindi
    assert "कॉल बंद करें" in hindi


def test_turn_language_uses_native_script_for_roman_hindi() -> None:
    """Catch the outbound agent speaking romanized Hindi against Day 6 rules."""
    instruction = turn_language_instruction("Aaj baarish hogi kya")

    assert "Devanagari" in instruction
    assert "never use romanized Hindi" in instruction


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("Will it rain today?", "en"),
        ("आज बारिश होगी क्या?", "hi"),
        ("Aaj baarish hogi kya", "hi"),
    ],
)
def test_turn_language_code_tracks_english_and_native_hindi(
    text: str,
    expected: str,
) -> None:
    """Catch tool confirmations using a stale opening language."""
    assert turn_language(text) == expected


def test_turn_language_keeps_clear_english_in_english() -> None:
    """Catch an English caller being forced into Hindi by the opening language."""
    instruction = turn_language_instruction("Will it rain today?")

    assert "Reply only in English" in instruction


def test_invalid_metadata_json_is_rejected() -> None:
    """Catch a direct dispatch bypassing the typed metadata contract."""
    with pytest.raises(CallSafetyError, match="metadata"):
        OutboundCallMetadata.from_json('{"destination": "farmer.demo"}')

    with pytest.raises(CallSafetyError, match="metadata"):
        OutboundCallMetadata.from_json("not-json")
