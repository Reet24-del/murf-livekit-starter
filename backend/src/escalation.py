"""Privacy-safe storage for consented human-help requests."""

import os
import re
import secrets
import sqlite3
from collections.abc import Callable
from datetime import datetime
from zoneinfo import ZoneInfo

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "memory.db")
INDIA_TIMEZONE = ZoneInfo("Asia/Kolkata")

REASONS = frozenset({"serious_crop_problem", "market_data_unavailable"})
URGENCIES = frozenset({"high", "medium"})
LANGUAGES = frozenset({"en", "hi", "hinglish"})
STATUSES = frozenset({"open", "in_progress", "resolved"})

_REFERENCE_PATTERN = re.compile(r"^KS-\d{8}-[A-F0-9]{4}$")
_LABELLED_SECRET_PATTERN = re.compile(
    r"(?P<label>\b(?:password|otp|pin|account(?:\s+number)?|"
    r"card(?:\s+number)?)\b\s*(?:is|:|=)?\s*)"
    r"(?P<value>[A-Za-z0-9][A-Za-z0-9_-]{2,})",
    re.IGNORECASE,
)
_LONG_DIGIT_PATTERN = re.compile(r"\b\d{6,}\b")


class EscalationValidationError(ValueError):
    """Raised when a help request violates the Day 7 contract."""


def _normalized_required(value: str, field: str) -> str:
    normalized = " ".join(value.strip().split())
    if not normalized:
        raise EscalationValidationError(f"{field} is required.")
    return normalized


def sanitize_help_text(value: str) -> str:
    """Collapse whitespace, redact sensitive values, and cap stored text."""
    text = " ".join(value.strip().split())
    text = _LABELLED_SECRET_PATTERN.sub(
        lambda match: f"{match.group('label')}[REDACTED]",
        text,
    )
    text = _LONG_DIGIT_PATTERN.sub("[REDACTED]", text)
    return text[:500]


def _reference_for(value: datetime) -> str:
    return f"KS-{value.strftime('%Y%m%d')}-{secrets.token_hex(2).upper()}"


def _timestamp(value: datetime | None) -> tuple[datetime, str]:
    current = value or datetime.now(INDIA_TIMEZONE)
    if current.tzinfo is None:
        current = current.replace(tzinfo=INDIA_TIMEZONE)
    current = current.astimezone(INDIA_TIMEZONE)
    return current, current.isoformat(timespec="seconds")


def _row_to_dict(row: sqlite3.Row | None) -> dict[str, str] | None:
    if row is None:
        return None
    return dict(row)


def init_help_requests_table(db_path: str | None = None) -> None:
    """Create the Day 7 help-request table and lookup index."""
    with sqlite3.connect(db_path or DB_PATH) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS help_requests (
                reference_id TEXT PRIMARY KEY,
                caller_id TEXT NOT NULL,
                caller_name TEXT,
                reason TEXT NOT NULL,
                summary TEXT NOT NULL,
                checks_performed TEXT NOT NULL,
                urgency TEXT NOT NULL,
                language TEXT NOT NULL,
                follow_up_method TEXT NOT NULL,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_help_requests_active
            ON help_requests (caller_id, reason, status)
            """
        )


def _validate_create_values(
    *,
    caller_id: str,
    reason: str,
    urgency: str,
    language: str,
    follow_up_method: str,
    consent_confirmed: bool,
) -> str:
    if not consent_confirmed:
        raise EscalationValidationError("Explicit caller consent is required.")

    normalized_caller_id = caller_id.strip()
    if not normalized_caller_id or normalized_caller_id.casefold() == "unknown":
        raise EscalationValidationError("A caller identity is required.")
    if reason not in REASONS:
        raise EscalationValidationError("Unsupported escalation reason.")
    if reason == "serious_crop_problem" and urgency != "high":
        raise EscalationValidationError("Serious crop problems must use high urgency.")
    if reason == "market_data_unavailable" and urgency != "medium":
        raise EscalationValidationError(
            "Unavailable market data must use medium urgency."
        )
    if urgency not in URGENCIES:
        raise EscalationValidationError("Unsupported urgency.")
    if language not in LANGUAGES:
        raise EscalationValidationError("Unsupported language.")
    if follow_up_method != "in_app":
        raise EscalationValidationError("Follow-up method must be in_app.")
    return normalized_caller_id


def create_or_update_help_request(
    *,
    caller_id: str,
    caller_name: str | None,
    reason: str,
    summary: str,
    checks_performed: str,
    urgency: str,
    language: str,
    follow_up_method: str = "in_app",
    consent_confirmed: bool,
    db_path: str | None = None,
    now: datetime | None = None,
    reference_factory: Callable[[datetime], str] | None = None,
) -> dict[str, str]:
    """Create a request or update the caller's matching active request."""
    normalized_caller_id = _validate_create_values(
        caller_id=caller_id,
        reason=reason,
        urgency=urgency,
        language=language,
        follow_up_method=follow_up_method,
        consent_confirmed=consent_confirmed,
    )
    safe_summary = sanitize_help_text(_normalized_required(summary, "Summary"))
    safe_checks = sanitize_help_text(
        _normalized_required(checks_performed, "Checks performed")
    )
    safe_name = sanitize_help_text(caller_name) if caller_name else None
    current, timestamp = _timestamp(now)
    database = db_path or DB_PATH
    init_help_requests_table(database)

    with sqlite3.connect(database) as conn:
        conn.row_factory = sqlite3.Row
        active = conn.execute(
            """
            SELECT reference_id
            FROM help_requests
            WHERE caller_id = ? AND reason = ?
              AND status IN ('open', 'in_progress')
            ORDER BY created_at ASC
            LIMIT 1
            """,
            (normalized_caller_id, reason),
        ).fetchone()

        if active is not None:
            reference_id = active["reference_id"]
            conn.execute(
                """
                UPDATE help_requests
                SET caller_name = ?, summary = ?, checks_performed = ?,
                    urgency = ?, language = ?, follow_up_method = ?, updated_at = ?
                WHERE reference_id = ?
                """,
                (
                    safe_name,
                    safe_summary,
                    safe_checks,
                    urgency,
                    language,
                    follow_up_method,
                    timestamp,
                    reference_id,
                ),
            )
        else:
            reference_id = (reference_factory or _reference_for)(current)
            if not _REFERENCE_PATTERN.fullmatch(reference_id):
                raise EscalationValidationError("Invalid help-request reference ID.")
            conn.execute(
                """
                INSERT INTO help_requests (
                    reference_id, caller_id, caller_name, reason, summary,
                    checks_performed, urgency, language, follow_up_method,
                    status, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'open', ?, ?)
                """,
                (
                    reference_id,
                    normalized_caller_id,
                    safe_name,
                    reason,
                    safe_summary,
                    safe_checks,
                    urgency,
                    language,
                    follow_up_method,
                    timestamp,
                    timestamp,
                ),
            )

        row = conn.execute(
            "SELECT * FROM help_requests WHERE reference_id = ?",
            (reference_id,),
        ).fetchone()

    request = _row_to_dict(row)
    if request is None:  # pragma: no cover - defensive database invariant
        raise RuntimeError("The saved help request could not be read back.")
    return request


def list_help_requests(
    *,
    status: str | None = None,
    urgency: str | None = None,
    db_path: str | None = None,
) -> list[dict[str, str]]:
    """List requests with optional exact status and urgency filters."""
    if status is not None and status not in STATUSES:
        raise EscalationValidationError("Unsupported status.")
    if urgency is not None and urgency not in URGENCIES:
        raise EscalationValidationError("Unsupported urgency.")

    database = db_path or DB_PATH
    init_help_requests_table(database)
    clauses: list[str] = []
    parameters: list[str] = []
    if status is not None:
        clauses.append("status = ?")
        parameters.append(status)
    if urgency is not None:
        clauses.append("urgency = ?")
        parameters.append(urgency)

    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    with sqlite3.connect(database) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            f"""
            SELECT * FROM help_requests
            {where}
            ORDER BY CASE urgency WHEN 'high' THEN 0 ELSE 1 END,
                     updated_at DESC
            """,
            parameters,
        ).fetchall()
    return [dict(row) for row in rows]


def update_help_request_status(
    reference_id: str,
    status: str,
    *,
    db_path: str | None = None,
    now: datetime | None = None,
) -> dict[str, str] | None:
    """Move a request to one of the supported human-workflow states."""
    if status not in STATUSES:
        raise EscalationValidationError("Unsupported status.")
    normalized_reference = reference_id.strip().upper()
    if not _REFERENCE_PATTERN.fullmatch(normalized_reference):
        raise EscalationValidationError("Invalid help-request reference ID.")

    _, timestamp = _timestamp(now)
    database = db_path or DB_PATH
    init_help_requests_table(database)
    with sqlite3.connect(database) as conn:
        conn.row_factory = sqlite3.Row
        result = conn.execute(
            """
            UPDATE help_requests
            SET status = ?, updated_at = ?
            WHERE reference_id = ?
            """,
            (status, timestamp, normalized_reference),
        )
        if result.rowcount == 0:
            return None
        row = conn.execute(
            "SELECT * FROM help_requests WHERE reference_id = ?",
            (normalized_reference,),
        ).fetchone()
    return _row_to_dict(row)
