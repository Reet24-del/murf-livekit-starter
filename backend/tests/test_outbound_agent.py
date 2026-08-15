from datetime import datetime
from functools import partial
from types import SimpleNamespace
from zoneinfo import ZoneInfo

import pytest

from call_analytics import CallTracker
from db import is_outbound_opted_out, record_outbound_opt_out
from telephony.outbound.agent import (
    OutboundFarmAgent,
    create_outbound_participant,
    metadata_from_job,
)
from telephony.outbound.call_config import (
    CallSafetyError,
    OutboundCallMetadata,
)
from weather import WeatherLookupError, WeatherReport

IST = ZoneInfo("Asia/Kolkata")
ALLOWED_TIME = datetime(2026, 8, 11, 14, 0, tzinfo=IST)


def call_metadata(**changes) -> OutboundCallMetadata:
    values = {
        "destination": "farmer.demo",
        "district": "Lucknow",
        "language": "en",
        "crop": "tomato",
        "consent_confirmed": True,
        "quiet_hours_override": False,
    }
    values.update(changes)
    return OutboundCallMetadata(**values)


def fake_job_context(metadata: OutboundCallMetadata):
    return SimpleNamespace(
        job=SimpleNamespace(metadata=metadata.to_json()),
        room=SimpleNamespace(name="outbound-test"),
    )


def test_job_metadata_is_revalidated_before_dialing() -> None:
    """Catch a direct LiveKit dispatch bypassing the consent check."""
    context = fake_job_context(call_metadata(consent_confirmed=False))

    with pytest.raises(CallSafetyError, match="consent"):
        metadata_from_job(context, now=ALLOWED_TIME, opted_out_lookup=lambda _: False)


def test_job_metadata_rejects_saved_opt_out() -> None:
    """Catch a direct dispatch bypassing a persisted stop request."""
    context = fake_job_context(call_metadata())

    with pytest.raises(CallSafetyError, match="opted out"):
        metadata_from_job(context, now=ALLOWED_TIME, opted_out_lookup=lambda _: True)


@pytest.mark.asyncio
async def test_live_weather_response_preserves_source_timestamp() -> None:
    """Catch the outbound advisory dropping when its live data is from."""

    async def weather_fetcher(district: str) -> WeatherReport:
        assert district == "Lucknow"
        return WeatherReport(
            location_name="Lucknow, Uttar Pradesh",
            observed_at="2026-08-11T14:00",
            forecast_date="2026-08-11",
            temperature_c=29.0,
            weather_description="light rain",
            wind_speed_kmh=8.0,
            minimum_temperature_c=25.0,
            maximum_temperature_c=31.0,
            precipitation_probability_percent=75,
        )

    agent = OutboundFarmAgent(
        fake_job_context(call_metadata()),
        call_metadata(),
        weather_fetcher=weather_fetcher,
    )

    response = await agent._live_weather_response()

    assert "Open-Meteo data timestamp: 2026-08-11T14:00 local time" in response
    assert "75% maximum chance of rain" in response


@pytest.mark.asyncio
async def test_live_weather_marks_outbound_advisory_success() -> None:
    async def weather_fetcher(district: str) -> WeatherReport:
        return WeatherReport(
            location_name=district,
            observed_at="2026-08-13T10:00",
            forecast_date="2026-08-13",
            temperature_c=29,
            weather_description="rain",
            wind_speed_kmh=8,
            minimum_temperature_c=25,
            maximum_temperature_c=31,
            precipitation_probability_percent=75,
        )

    tracker = CallTracker("sip", recorder=lambda record: record)
    tracker.observe_user("Will it rain today?")
    agent = OutboundFarmAgent(
        fake_job_context(call_metadata()),
        call_metadata(),
        weather_fetcher=weather_fetcher,
        analytics=tracker,
    )

    await agent._live_weather_response()
    outcome = tracker.finalize()

    assert outcome.outcome == "successful"
    assert outcome.result_category == "rain_advisory_delivered"


@pytest.mark.asyncio
async def test_live_weather_failure_is_spoken_without_guessing() -> None:
    """Catch a failed live lookup producing fabricated advisory values."""

    async def failing_fetcher(district: str) -> WeatherReport:
        raise WeatherLookupError("timeout")

    agent = OutboundFarmAgent(
        fake_job_context(call_metadata()),
        call_metadata(),
        weather_fetcher=failing_fetcher,
    )

    response = await agent._live_weather_response()

    assert response == (
        "Live weather data is unavailable right now, so I will not guess. "
        "Please check your local weather service before making a farm decision."
    )


@pytest.mark.asyncio
async def test_latest_roman_hindi_turn_requires_devanagari_reply() -> None:
    """Catch the phone agent violating the compulsory native-script rule."""
    agent = OutboundFarmAgent(fake_job_context(call_metadata()), call_metadata())
    added_messages = []
    turn_context = SimpleNamespace(
        add_message=lambda **message: added_messages.append(message)
    )
    message = SimpleNamespace(text_content="Aaj baarish hogi kya")

    await agent.on_user_turn_completed(turn_context, message)

    assert agent.response_language == "hi"
    assert "Devanagari" in added_messages[0]["content"]


def test_opt_out_records_destination_and_confirms_in_current_language(
    tmp_path,
) -> None:
    """Catch the stop tool claiming success without persistent suppression."""
    db_path = str(tmp_path / "callers.db")
    recorder = partial(record_outbound_opt_out, db_path=db_path)
    agent = OutboundFarmAgent(
        fake_job_context(call_metadata(language="hi")),
        call_metadata(language="hi"),
        opt_out_recorder=recorder,
    )

    confirmation = agent._record_opt_out()

    assert is_outbound_opted_out("farmer.demo", db_path=db_path) is True
    assert confirmation == "भविष्य की कॉल बंद कर दी गई हैं।"


class RecordingSIP:
    def __init__(self) -> None:
        self.request = None

    async def create_sip_participant(self, request) -> None:
        self.request = request


@pytest.mark.asyncio
async def test_create_outbound_participant_uses_trunk_and_controlled_target() -> None:
    """Catch the SIP leg dialing a wrong target or not waiting for answer."""
    sip = RecordingSIP()
    context = SimpleNamespace(
        room=SimpleNamespace(name="outbound-test"),
        api=SimpleNamespace(sip=sip),
    )

    await create_outbound_participant(context, call_metadata(), "ST_test_trunk")

    assert sip.request.room_name == "outbound-test"
    assert sip.request.sip_trunk_id == "ST_test_trunk"
    assert sip.request.sip_call_to == "farmer.demo"
    assert sip.request.participant_identity == "phone-user"
    assert sip.request.wait_until_answered is True


@pytest.mark.asyncio
async def test_create_outbound_participant_requires_trunk_configuration() -> None:
    """Catch a call attempt with no configured SIP route."""
    context = SimpleNamespace(room=SimpleNamespace(name="outbound-test"))

    with pytest.raises(CallSafetyError, match="TRUNK_ID"):
        await create_outbound_participant(context, call_metadata(), "")
