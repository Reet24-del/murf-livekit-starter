from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

from escalation import (
    EscalationValidationError,
    create_or_update_help_request,
    list_help_requests,
    update_help_request_status,
)

IST = ZoneInfo("Asia/Kolkata")
NOW = datetime(2026, 8, 12, 10, 30, tzinfo=IST)


def fixed_reference(_: datetime) -> str:
    return "KS-20260812-A4F2"


def test_create_help_request_returns_open_reference(tmp_path) -> None:
    """Catch a create path that omits persistence or the caller reference."""
    db_path = str(tmp_path / "memory.db")
    request = create_or_update_help_request(
        caller_id="farmer-1",
        caller_name="Ramesh",
        reason="serious_crop_problem",
        summary="Half the tomato field is turning black.",
        checks_performed="Asked about spread and visible leaf damage.",
        urgency="high",
        language="en",
        consent_confirmed=True,
        db_path=db_path,
        now=NOW,
        reference_factory=fixed_reference,
    )

    assert request["reference_id"] == "KS-20260812-A4F2"
    assert request["status"] == "open"
    assert list_help_requests(db_path=db_path) == [request]


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        ({"consent_confirmed": False}, "Explicit caller consent is required"),
        ({"caller_id": "unknown"}, "A caller identity is required"),
        ({"urgency": "medium"}, "Serious crop problems must use high urgency"),
        ({"follow_up_method": "phone"}, "Follow-up method must be in_app"),
    ],
)
def test_invalid_help_request_is_rejected(tmp_path, kwargs, message) -> None:
    """Catch writes that bypass consent, identity, urgency, or channel rules."""
    values = {
        "caller_id": "farmer-1",
        "caller_name": None,
        "reason": "serious_crop_problem",
        "summary": "Crop damage is spreading quickly.",
        "checks_performed": "Checked symptoms with the farmer.",
        "urgency": "high",
        "language": "en",
        "follow_up_method": "in_app",
        "consent_confirmed": True,
    }
    values.update(kwargs)

    with pytest.raises(EscalationValidationError, match=message):
        create_or_update_help_request(db_path=str(tmp_path / "db.sqlite"), **values)


def test_sensitive_values_are_redacted_before_storage(tmp_path) -> None:
    """Catch summaries that persist credentials or long private numbers."""
    db_path = str(tmp_path / "memory.db")
    create_or_update_help_request(
        caller_id="farmer-1",
        caller_name=None,
        reason="market_data_unavailable",
        summary="My OTP is 829144 and account number is 123456789012.",
        checks_performed=("Password: Secret123 and exact mandi rate was unavailable."),
        urgency="medium",
        language="hinglish",
        consent_confirmed=True,
        db_path=db_path,
        now=NOW,
        reference_factory=fixed_reference,
    )

    stored = list_help_requests(db_path=db_path)[0]
    combined = stored["summary"] + stored["checks_performed"]
    assert "829144" not in combined
    assert "123456789012" not in combined
    assert "Secret123" not in combined
    assert combined.count("[REDACTED]") >= 3
    assert "transcript" not in stored


def test_long_sensitive_value_is_redacted_before_text_is_truncated(tmp_path) -> None:
    """Catch truncation that exposes the beginning of a credential."""
    db_path = str(tmp_path / "memory.db")
    request = create_or_update_help_request(
        caller_id="farmer-1",
        caller_name=None,
        reason="market_data_unavailable",
        summary=("Observed unavailable rate. " * 24) + " OTP 829144",
        checks_performed="Checked the local data source.",
        urgency="medium",
        language="en",
        consent_confirmed=True,
        db_path=db_path,
        now=NOW,
        reference_factory=fixed_reference,
    )

    assert len(request["summary"]) <= 500
    assert "829144" not in request["summary"]


def test_duplicate_open_request_updates_existing_reference(tmp_path) -> None:
    """Catch duplicate active tickets for the same caller and reason."""
    db_path = str(tmp_path / "memory.db")
    first = create_or_update_help_request(
        caller_id="farmer-1",
        caller_name="Ramesh",
        reason="serious_crop_problem",
        summary="Tomato leaves are black.",
        checks_performed="Checked how quickly it spread.",
        urgency="high",
        language="en",
        consent_confirmed=True,
        db_path=db_path,
        now=NOW,
        reference_factory=fixed_reference,
    )
    second = create_or_update_help_request(
        caller_id="farmer-1",
        caller_name="Ramesh",
        reason="serious_crop_problem",
        summary="Now half the field is affected.",
        checks_performed="Confirmed rapid spread and severe damage.",
        urgency="high",
        language="en",
        consent_confirmed=True,
        db_path=db_path,
        now=NOW.replace(minute=45),
        reference_factory=lambda _: "KS-20260812-BBBB",
    )

    assert second["reference_id"] == first["reference_id"]
    assert second["summary"] == "Now half the field is affected."
    assert len(list_help_requests(db_path=db_path)) == 1


def test_filter_and_status_transition(tmp_path) -> None:
    """Catch wrong urgency filtering or unsupported ticket state changes."""
    db_path = str(tmp_path / "memory.db")
    crop = create_or_update_help_request(
        caller_id="farmer-crop",
        caller_name="Ramesh",
        reason="serious_crop_problem",
        summary="The tomato crop is dying quickly.",
        checks_performed="Confirmed rapid spread across half the field.",
        urgency="high",
        language="en",
        consent_confirmed=True,
        db_path=db_path,
        now=NOW,
        reference_factory=lambda _: "KS-20260812-C001",
    )
    create_or_update_help_request(
        caller_id="farmer-market",
        caller_name="Sita",
        reason="market_data_unavailable",
        summary="The current tomato mandi rate is unavailable.",
        checks_performed="Checked the available local market source.",
        urgency="medium",
        language="hi",
        consent_confirmed=True,
        db_path=db_path,
        now=NOW,
        reference_factory=lambda _: "KS-20260812-D001",
    )

    high_requests = list_help_requests(urgency="high", db_path=db_path)
    assert [request["reference_id"] for request in high_requests] == [
        crop["reference_id"]
    ]

    in_progress = update_help_request_status(
        crop["reference_id"],
        "in_progress",
        db_path=db_path,
        now=NOW.replace(hour=11),
    )
    assert in_progress is not None
    assert in_progress["status"] == "in_progress"

    resolved = update_help_request_status(
        crop["reference_id"],
        "resolved",
        db_path=db_path,
        now=NOW.replace(hour=12),
    )
    assert resolved is not None
    assert resolved["status"] == "resolved"

    with pytest.raises(EscalationValidationError, match="Unsupported status"):
        update_help_request_status(crop["reference_id"], "closed", db_path=db_path)
