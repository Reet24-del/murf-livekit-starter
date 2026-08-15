import sqlite3
from datetime import UTC, datetime, timedelta
from functools import partial

import pytest

from call_analytics import (
    CallRecord,
    CallTracker,
    get_call_analytics,
    init_call_analytics_table,
    record_call,
)

NOW = datetime(2026, 8, 13, 6, 0, tzinfo=UTC)


def _record(
    db_path: str,
    *,
    call_id: str,
    days_ago: int = 0,
    channel: str = "browser",
    language: str = "en",
    outcome: str = "successful",
    result_category: str | None = "farming_guidance_delivered",
    failure_category: str | None = None,
) -> None:
    ended_at = NOW - timedelta(days=days_ago)
    record_call(
        CallRecord(
            call_id=call_id,
            started_at=ended_at - timedelta(seconds=42),
            ended_at=ended_at,
            duration_seconds=42,
            channel=channel,
            language=language,
            outcome=outcome,
            result_category=result_category,
            failure_category=failure_category,
        ),
        db_path=db_path,
    )


def test_tracker_records_success_once_without_transcript(tmp_path) -> None:
    db_path = str(tmp_path / "analytics.db")
    recorder = partial(record_call, db_path=db_path)
    tracker = CallTracker("browser", started_at=NOW, recorder=recorder)

    tracker.observe_user("What is the weather in Lucknow?")
    tracker.mark_result("live_weather_delivered")
    tracker.observe_assistant("It is 29 degrees with a chance of rain.")
    first = tracker.finalize(ended_at=NOW + timedelta(seconds=18))
    second = tracker.finalize(ended_at=NOW + timedelta(seconds=30))

    assert first == second
    assert first.outcome == "successful"
    assert first.result_category == "live_weather_delivered"

    with sqlite3.connect(db_path) as conn:
        rows = conn.execute("SELECT * FROM call_analytics").fetchall()
        columns = {row[1] for row in conn.execute("PRAGMA table_info(call_analytics)")}
    assert len(rows) == 1
    assert "transcript" not in columns
    assert "caller_id" not in columns
    assert "phone_number" not in columns


def test_tracker_counts_plain_farming_guidance_as_success(tmp_path) -> None:
    """Catch completed farming answers being recorded as failed or omitted."""
    db_path = str(tmp_path / "analytics.db")
    tracker = CallTracker(
        "browser",
        started_at=NOW,
        recorder=partial(record_call, db_path=db_path),
    )

    tracker.observe_user("Which crops can I grow in Lucknow during the rainy season?")
    tracker.observe_assistant("You can grow rice, millet, and urad during the rainy season.")
    record = tracker.finalize(ended_at=NOW + timedelta(seconds=24))

    assert record.outcome == "successful"
    assert record.result_category == "farming_guidance_delivered"
    assert record.failure_category is None


def test_tracker_marks_incomplete_and_tool_failure(tmp_path) -> None:
    db_path = str(tmp_path / "analytics.db")
    recorder = partial(record_call, db_path=db_path)

    incomplete = CallTracker("browser", started_at=NOW, recorder=recorder)
    incomplete.observe_user("How should I protect my tomato crop?")
    incomplete_record = incomplete.finalize(ended_at=NOW + timedelta(seconds=5))

    failed_tool = CallTracker("sip", started_at=NOW, recorder=recorder)
    failed_tool.observe_user("Aaj mausam kaisa hai?")
    failed_tool.mark_failure("tool_failure")
    tool_record = failed_tool.finalize(ended_at=NOW + timedelta(seconds=8))

    assert incomplete_record.outcome == "failed"
    assert incomplete_record.failure_category == "caller_ended_early"
    assert tool_record.outcome == "failed"
    assert tool_record.failure_category == "tool_failure"
    assert tool_record.language == "hinglish"


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("channel", "whatsapp"),
        ("language", "Punjabi transcript here"),
        ("outcome", "mostly successful"),
        ("result_category", "Farmer Ramesh said his OTP is 1234"),
        ("failure_category", "A long arbitrary conversation summary"),
    ],
)
def test_record_rejects_uncontrolled_values(tmp_path, field: str, value: str) -> None:
    values = {
        "call_id": "call-safe",
        "started_at": NOW,
        "ended_at": NOW + timedelta(seconds=3),
        "duration_seconds": 3,
        "channel": "browser",
        "language": "en",
        "outcome": "successful",
        "result_category": "farming_guidance_delivered",
        "failure_category": None,
    }
    values[field] = value

    with pytest.raises(ValueError):
        record_call(CallRecord(**values), db_path=str(tmp_path / "analytics.db"))


def test_analytics_reconciles_filters_trend_and_recent_order(tmp_path) -> None:
    db_path = str(tmp_path / "analytics.db")
    _record(db_path, call_id="latest-browser", language="hinglish")
    _record(
        db_path,
        call_id="failed-sip",
        days_ago=1,
        channel="sip",
        language="hi",
        outcome="failed",
        result_category=None,
        failure_category="no_response",
    )
    _record(db_path, call_id="older-browser", days_ago=2)
    _record(db_path, call_id="outside-window", days_ago=9)

    payload = get_call_analytics(days=7, now=NOW, db_path=db_path)

    assert payload["summary"] == {
        "total_calls": 3,
        "successful_calls": 2,
        "failed_calls": 1,
        "success_rate": 66.7,
    }
    assert sum(point["successful"] for point in payload["trend"]) == 2
    assert sum(point["failed"] for point in payload["trend"]) == 1
    assert payload["breakdowns"]["channels"] == {"browser": 2, "sip": 1}
    assert payload["breakdowns"]["languages"] == {
        "en": 1,
        "hi": 1,
        "hinglish": 1,
        "unknown": 0,
    }
    assert [row["call_id"] for row in payload["recent_calls"]] == [
        "latest-browser",
        "failed-sip",
        "older-browser",
    ]
    assert "transcript" not in str(payload).lower()

    filtered = get_call_analytics(
        days=7,
        channel="sip",
        language="hi",
        outcome="failed",
        now=NOW,
        db_path=db_path,
    )
    assert filtered["summary"]["total_calls"] == 1
    assert filtered["recent_calls"][0]["failure_category"] == "no_response"


def test_init_table_schema_contains_only_approved_fields(tmp_path) -> None:
    db_path = str(tmp_path / "analytics.db")
    init_call_analytics_table(db_path)

    with sqlite3.connect(db_path) as conn:
        columns = [
            row[1] for row in conn.execute("PRAGMA table_info(call_analytics)")
        ]

    assert columns == [
        "call_id",
        "started_at",
        "ended_at",
        "duration_seconds",
        "channel",
        "language",
        "outcome",
        "result_category",
        "failure_category",
    ]
