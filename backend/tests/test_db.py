import sqlite3

import pytest

from db import (
    get_caller,
    init_db,
    is_outbound_opted_out,
    record_outbound_opt_out,
    save_caller,
)


def test_save_caller_preserves_unsupplied_facts(tmp_path) -> None:
    """Catch an update that accidentally overwrites an existing farm fact."""
    db_path = str(tmp_path / "callers.db")
    init_db(db_path)

    save_caller(
        "caller-1",
        name="Ramesh",
        crops_grown="cotton",
        irrigation_type="drip",
        db_path=db_path,
    )
    save_caller("caller-1", district="Wardha", db_path=db_path)

    profile = get_caller("caller-1", db_path=db_path)
    assert profile is not None
    assert profile["name"] == "Ramesh"
    assert profile["crops_grown"] == "cotton"
    assert profile["irrigation_type"] == "drip"
    assert profile["district"] == "Wardha"


def test_save_caller_persists_conversation_memory(tmp_path) -> None:
    db_path = str(tmp_path / "callers.db")
    init_db(db_path)

    save_caller(
        "caller-1",
        conversation_memory="Discussed drip irrigation for the tomato crop.",
        db_path=db_path,
    )

    profile = get_caller("caller-1", db_path=db_path)
    assert profile is not None
    assert profile["conversation_memory"] == (
        "Discussed drip irrigation for the tomato crop."
    )


def test_init_db_migrates_existing_callers_table(tmp_path) -> None:
    db_path = str(tmp_path / "callers.db")
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            """
            CREATE TABLE callers (
                user_id TEXT PRIMARY KEY,
                name TEXT,
                language_preference TEXT,
                crops_grown TEXT,
                land_size TEXT,
                district TEXT,
                irrigation_type TEXT,
                last_interaction TIMESTAMP
            )
            """
        )
        conn.execute(
            "INSERT INTO callers (user_id, name) VALUES (?, ?)",
            ("caller-1", "Ramesh"),
        )

    init_db(db_path)

    profile = get_caller("caller-1", db_path=db_path)
    assert profile is not None
    assert profile["name"] == "Ramesh"
    assert profile["conversation_memory"] is None


def test_save_caller_rejects_missing_identity(tmp_path) -> None:
    """Catch a write that merges anonymous callers into one shared profile."""
    db_path = str(tmp_path / "callers.db")
    init_db(db_path)

    try:
        save_caller("", name="Ramesh", db_path=db_path)
    except ValueError as error:
        assert str(error) == "A caller identity is required to save a profile."
    else:
        raise AssertionError("Expected missing caller identity to be rejected.")


def test_get_caller_rejects_missing_identity(tmp_path) -> None:
    """Catch a lookup that can read the shared anonymous profile."""
    db_path = str(tmp_path / "callers.db")
    init_db(db_path)

    try:
        get_caller("", db_path=db_path)
    except ValueError as error:
        assert str(error) == "A caller identity is required to look up a profile."
    else:
        raise AssertionError("Expected missing caller identity to be rejected.")


def test_outbound_opt_out_blocks_only_normalized_destination(tmp_path) -> None:
    """Catch opt-out writes that fail to block the same trimmed destination."""
    db_path = str(tmp_path / "callers.db")
    init_db(db_path)

    record_outbound_opt_out("  farmer.demo  ", db_path=db_path)

    assert is_outbound_opted_out("farmer.demo", db_path=db_path) is True
    assert is_outbound_opted_out("another.farmer", db_path=db_path) is False


def test_outbound_opt_out_rejects_blank_destination(tmp_path) -> None:
    """Catch anonymous opt-outs that could block an invalid shared key."""
    db_path = str(tmp_path / "callers.db")

    with pytest.raises(ValueError, match="destination"):
        record_outbound_opt_out("   ", db_path=db_path)

    with pytest.raises(ValueError, match="destination"):
        is_outbound_opted_out("", db_path=db_path)


def test_init_db_creates_help_requests_table(tmp_path) -> None:
    """Catch startup paths that omit the Day 7 human-help storage."""
    db_path = tmp_path / "memory.db"

    init_db(str(db_path))

    with sqlite3.connect(db_path) as conn:
        columns = {row[1] for row in conn.execute("PRAGMA table_info(help_requests)")}
    assert {
        "reference_id",
        "caller_id",
        "reason",
        "summary",
        "checks_performed",
        "urgency",
        "language",
        "follow_up_method",
        "status",
        "created_at",
        "updated_at",
    } <= columns
