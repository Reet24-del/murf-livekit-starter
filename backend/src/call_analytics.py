"""Privacy-safe call outcome tracking for browser and SIP conversations."""

from __future__ import annotations

import sqlite3
import uuid
from collections.abc import Callable
from dataclasses import asdict, dataclass
from datetime import datetime, time, timedelta, timezone
from pathlib import Path
from typing import Any

from db import DB_PATH
from language import ResponseLanguage, detect_response_language

CHANNELS = frozenset({"browser", "sip"})
LANGUAGES = frozenset({"en", "hi", "hinglish", "unknown"})
OUTCOMES = frozenset({"successful", "failed"})
RESULT_CATEGORIES = frozenset(
    {
        "farming_guidance_delivered",
        "live_weather_delivered",
        "expert_request_created",
        "rain_advisory_delivered",
    }
)
FAILURE_CATEGORIES = frozenset(
    {
        "no_question",
        "caller_ended_early",
        "no_response",
        "tool_failure",
        "dial_failed",
        "not_answered",
        "recipient_opted_out",
        "agent_error",
    }
)

_GREETING_ONLY = frozenset(
    {
        "hello",
        "hi",
        "hey",
        "namaste",
        "namaskar",
        "नमस्ते",
        "नमस्कार",
        "yes",
        "no",
        "haan",
        "han",
        "nahi",
        "हाँ",
        "नहीं",
    }
)
_QUESTION_MARKERS = frozenset(
    {
        "what",
        "when",
        "where",
        "why",
        "how",
        "can",
        "should",
        "weather",
        "rain",
        "temperature",
        "crop",
        "farm",
        "soil",
        "pest",
        "fertilizer",
        "irrigation",
        "mausam",
        "baarish",
        "fasal",
        "kheti",
        "paani",
        "kaise",
        "kaisa",
        "kya",
        "कब",
        "कहाँ",
        "क्यों",
        "कैसे",
        "कैसा",
        "क्या",
        "मौसम",
        "बारिश",
        "फसल",
        "खेती",
        "मिट्टी",
        "सिंचाई",
    }
)


@dataclass(frozen=True)
class CallRecord:
    call_id: str
    started_at: datetime
    ended_at: datetime
    duration_seconds: int
    channel: str
    language: str
    outcome: str
    result_category: str | None
    failure_category: str | None


def _database_path(db_path: str | None) -> str:
    return str(Path(db_path or DB_PATH))


def _require_enum(name: str, value: str, allowed: frozenset[str]) -> str:
    if value not in allowed:
        raise ValueError(f"Unsupported {name}: {value!r}.")
    return value


def _aware_utc(value: datetime, field_name: str) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{field_name} must include a timezone.")
    return value.astimezone(timezone.utc)


def _validate_record(record: CallRecord) -> CallRecord:
    if not record.call_id or len(record.call_id) > 80:
        raise ValueError("call_id must be a non-empty random identifier.")
    started_at = _aware_utc(record.started_at, "started_at")
    ended_at = _aware_utc(record.ended_at, "ended_at")
    if ended_at < started_at:
        raise ValueError("ended_at cannot be before started_at.")
    if record.duration_seconds < 0:
        raise ValueError("duration_seconds cannot be negative.")

    channel = _require_enum("channel", record.channel, CHANNELS)
    language = _require_enum("language", record.language, LANGUAGES)
    outcome = _require_enum("outcome", record.outcome, OUTCOMES)

    if record.result_category is not None:
        _require_enum("result category", record.result_category, RESULT_CATEGORIES)
    if record.failure_category is not None:
        _require_enum("failure category", record.failure_category, FAILURE_CATEGORIES)

    if outcome == "successful":
        if record.result_category is None or record.failure_category is not None:
            raise ValueError("Successful calls require one result and no failure.")
    elif record.failure_category is None or record.result_category is not None:
        raise ValueError("Failed calls require one failure and no result.")

    return CallRecord(
        call_id=record.call_id,
        started_at=started_at,
        ended_at=ended_at,
        duration_seconds=record.duration_seconds,
        channel=channel,
        language=language,
        outcome=outcome,
        result_category=record.result_category,
        failure_category=record.failure_category,
    )


def init_call_analytics_table(db_path: str | None = None) -> None:
    """Create the Day 8 table without any caller identity or transcript fields."""
    with sqlite3.connect(_database_path(db_path)) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS call_analytics (
                call_id TEXT PRIMARY KEY,
                started_at TEXT NOT NULL,
                ended_at TEXT NOT NULL,
                duration_seconds INTEGER NOT NULL CHECK (duration_seconds >= 0),
                channel TEXT NOT NULL CHECK (channel IN ('browser', 'sip')),
                language TEXT NOT NULL
                    CHECK (language IN ('en', 'hi', 'hinglish', 'unknown')),
                outcome TEXT NOT NULL
                    CHECK (outcome IN ('successful', 'failed')),
                result_category TEXT,
                failure_category TEXT
            )
            """
        )
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_call_analytics_ended_at
            ON call_analytics(ended_at DESC)
            """
        )


def record_call(record: CallRecord, db_path: str | None = None) -> CallRecord:
    """Persist one validated, controlled call record exactly once."""
    safe = _validate_record(record)
    init_call_analytics_table(db_path)
    with sqlite3.connect(_database_path(db_path)) as conn:
        conn.execute(
            """
            INSERT OR IGNORE INTO call_analytics (
                call_id, started_at, ended_at, duration_seconds, channel,
                language, outcome, result_category, failure_category
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                safe.call_id,
                safe.started_at.isoformat(),
                safe.ended_at.isoformat(),
                safe.duration_seconds,
                safe.channel,
                safe.language,
                safe.outcome,
                safe.result_category,
                safe.failure_category,
            ),
        )
    return safe


def _language_code(text: str) -> str:
    detected = detect_response_language(text)
    return {
        ResponseLanguage.ENGLISH: "en",
        ResponseLanguage.HINDI: "hi",
        ResponseLanguage.HINGLISH: "hinglish",
        ResponseLanguage.MIRROR: "unknown",
    }[detected]


def _looks_like_farmer_question(text: str) -> bool:
    normalized = " ".join(text.casefold().strip().split())
    if not normalized or normalized in _GREETING_ONLY:
        return False
    tokens = set(normalized.replace("?", " ").split())
    return "?" in normalized or bool(tokens & _QUESTION_MARKERS)


class CallTracker:
    """Classify a call in memory, then persist only its controlled outcome."""

    def __init__(
        self,
        channel: str,
        *,
        started_at: datetime | None = None,
        recorder: Callable[[CallRecord], CallRecord] = record_call,
        call_id: str | None = None,
    ) -> None:
        self.channel = _require_enum("channel", channel, CHANNELS)
        self.started_at = _aware_utc(
            started_at or datetime.now(timezone.utc), "started_at"
        )
        self.call_id = call_id or f"call_{uuid.uuid4().hex}"
        self._recorder = recorder
        self._language = "unknown"
        self._user_turns = 0
        self._has_farmer_question = False
        self._result_category: str | None = None
        self._failure_category: str | None = None
        self._final_record: CallRecord | None = None

    @property
    def finalized(self) -> bool:
        return self._final_record is not None

    def observe_user(self, text: str) -> None:
        if self.finalized or not text.strip():
            return
        self._user_turns += 1
        self._language = _language_code(text)
        self._has_farmer_question = self._has_farmer_question or (
            _looks_like_farmer_question(text)
        )

    def observe_assistant(self, text: str) -> None:
        if self.finalized or not text.strip() or self._failure_category is not None:
            return
        # A complete response to a recognized farming question satisfies the
        # browser-agent success condition. Explicit weather/escalation results
        # remain more specific and can replace this category later in the call.
        if self._has_farmer_question and self._result_category is None:
            self._result_category = "farming_guidance_delivered"

    def mark_result(self, category: str) -> None:
        _require_enum("result category", category, RESULT_CATEGORIES)
        if self.finalized:
            return
        self._result_category = category
        self._failure_category = None

    def mark_failure(self, category: str) -> None:
        _require_enum("failure category", category, FAILURE_CATEGORIES)
        if self.finalized or self._result_category is not None:
            return
        self._failure_category = category

    def finalize(self, ended_at: datetime | None = None) -> CallRecord:
        if self._final_record is not None:
            return self._final_record

        finished_at = _aware_utc(
            ended_at or datetime.now(timezone.utc), "ended_at"
        )
        if self._result_category is not None and self._has_farmer_question:
            outcome = "successful"
            result_category = self._result_category
            failure_category = None
        else:
            outcome = "failed"
            result_category = None
            failure_category = self._failure_category
            if failure_category is None:
                if self._user_turns == 0:
                    failure_category = "no_response"
                elif self._has_farmer_question:
                    failure_category = "caller_ended_early"
                else:
                    failure_category = "no_question"

        record = CallRecord(
            call_id=self.call_id,
            started_at=self.started_at,
            ended_at=finished_at,
            duration_seconds=max(
                0, round((finished_at - self.started_at).total_seconds())
            ),
            channel=self.channel,
            language=self._language,
            outcome=outcome,
            result_category=result_category,
            failure_category=failure_category,
        )
        self._final_record = self._recorder(record)
        return self._final_record


def _row_to_payload(row: sqlite3.Row) -> dict[str, Any]:
    payload = dict(row)
    payload["duration_seconds"] = int(payload["duration_seconds"])
    return payload


def _safe_count(mapping: dict[str, int], key: str, unknown_key: str = "unknown") -> None:
    """Increment a counter only when the key is known; keep unknown values private-safe."""
    if key in mapping:
        mapping[key] += 1
        return
    mapping[unknown_key] = mapping.get(unknown_key, 0) + 1


def _coerce_enum(value: str, allowed: frozenset[str], fallback: str) -> str:
    return value if value in allowed else fallback


def get_call_analytics(
    *,
    days: int = 7,
    channel: str = "all",
    language: str = "all",
    outcome: str = "all",
    now: datetime | None = None,
    db_path: str | None = None,
) -> dict[str, Any]:
    """Aggregate one filtered snapshot for every dashboard region."""
    if days not in {1, 7, 30, 90}:
        raise ValueError("days must be one of 1, 7, 30, or 90.")
    if channel != "all":
        _require_enum("channel", channel, CHANNELS)
    if language != "all":
        _require_enum("language", language, LANGUAGES)
    if outcome != "all":
        _require_enum("outcome", outcome, OUTCOMES)

    generated_at = _aware_utc(now or datetime.now(timezone.utc), "now")
    start_date = generated_at.date() - timedelta(days=days - 1)
    start_at = datetime.combine(start_date, time.min, tzinfo=timezone.utc)

    init_call_analytics_table(db_path)
    clauses = ["ended_at >= ?", "ended_at <= ?"]
    parameters: list[str] = [start_at.isoformat(), generated_at.isoformat()]
    for column, value in (
        ("channel", channel),
        ("language", language),
        ("outcome", outcome),
    ):
        if value != "all":
            clauses.append(f"{column} = ?")
            parameters.append(value)

    with sqlite3.connect(_database_path(db_path)) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            f"""
            SELECT call_id, started_at, ended_at, duration_seconds, channel,
                   language, outcome, result_category, failure_category
            FROM call_analytics
            WHERE {' AND '.join(clauses)}
            ORDER BY ended_at DESC
            """,
            parameters,
        ).fetchall()

    calls = [_row_to_payload(row) for row in rows]

    trend_by_date = {
        (start_date + timedelta(days=offset)).isoformat(): {
            "successful": 0,
            "failed": 0,
        }
        for offset in range(days)
    }
    channel_counts = dict.fromkeys(sorted(CHANNELS), 0)
    language_counts = dict.fromkeys(("en", "hi", "hinglish", "unknown"), 0)
    failure_counts = dict.fromkeys(sorted(FAILURE_CATEGORIES), 0)

    for call in calls:
        channel = _coerce_enum(call["channel"], CHANNELS, "browser")
        language = _coerce_enum(call["language"], LANGUAGES | frozenset({"unknown"}), "unknown")
        outcome = _coerce_enum(call["outcome"], OUTCOMES, "failed")
        result_category = (
            call["result_category"]
            if call["result_category"] in RESULT_CATEGORIES
            else None
        )
        failure_category = (
            call["failure_category"]
            if call["failure_category"] in FAILURE_CATEGORIES
            else None
        )
        normalized = {
            "channel": channel,
            "language": language,
            "outcome": outcome,
            "result_category": result_category,
            "failure_category": failure_category,
        }
        call.update(normalized)

        ended_date = datetime.fromisoformat(call["ended_at"]).date().isoformat()
        if ended_date in trend_by_date:
            trend_by_date[ended_date][call["outcome"]] += 1
        _safe_count(channel_counts, call["channel"])
        _safe_count(language_counts, call["language"])
        if call["failure_category"]:
            _safe_count(failure_counts, call["failure_category"], unknown_key="agent_error")

    successful = sum(call["outcome"] == "successful" for call in calls)
    failed = len(calls) - successful

    trend = [
        {"date": date, **counts} for date, counts in trend_by_date.items()
    ]
    failures = [
        {"category": category, "count": count}
        for category, count in sorted(
            failure_counts.items(), key=lambda item: (-item[1], item[0])
        )
        if count
    ]

    return {
        "summary": {
            "total_calls": len(calls),
            "successful_calls": successful,
            "failed_calls": failed,
            "success_rate": round(successful / len(calls) * 100, 1) if calls else 0,
        },
        "trend": trend,
        "breakdowns": {
            "channels": channel_counts,
            "languages": language_counts,
            "failures": failures,
        },
        "recent_calls": calls[:50],
        "generated_at": generated_at.isoformat(),
    }


def record_as_dict(record: CallRecord) -> dict[str, Any]:
    """Return a JSON-ready record for tests and controlled integrations."""
    payload = asdict(record)
    payload["started_at"] = record.started_at.isoformat()
    payload["ended_at"] = record.ended_at.isoformat()
    return payload
