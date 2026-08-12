import os
import sqlite3
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "memory.db")


def _validate_user_id(user_id: str, action: str) -> str:
    normalized_user_id = user_id.strip()
    if not normalized_user_id or normalized_user_id == "unknown":
        raise ValueError(f"A caller identity is required to {action} a profile.")
    return normalized_user_id


def _validate_destination(destination: str) -> str:
    normalized_destination = destination.strip().casefold()
    if not normalized_destination:
        raise ValueError("An outbound destination is required.")
    return normalized_destination


def init_db(db_path: str | None = None) -> None:
    """Initialize the caller-memory, opt-out, and human-help tables."""
    database = db_path or DB_PATH
    with sqlite3.connect(database) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS callers (
                user_id TEXT PRIMARY KEY,
                name TEXT,
                language_preference TEXT,
                crops_grown TEXT,
                land_size TEXT,
                district TEXT,
                irrigation_type TEXT,
                conversation_memory TEXT,
                last_interaction TIMESTAMP
            )
            """
        )

        columns = {
            row[1] for row in conn.execute("PRAGMA table_info(callers)").fetchall()
        }
        if "conversation_memory" not in columns:
            conn.execute("ALTER TABLE callers ADD COLUMN conversation_memory TEXT")
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS outbound_opt_outs (
                destination TEXT PRIMARY KEY,
                opted_out_at TEXT NOT NULL
            )
            """
        )

    from escalation import init_help_requests_table

    init_help_requests_table(database)


def get_caller(user_id: str, db_path: str | None = None) -> dict[str, str] | None:
    """Fetch caller details by user_id. Returns dictionary or None."""
    caller_id = _validate_user_id(user_id, "look up")
    with sqlite3.connect(db_path or DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            "SELECT * FROM callers WHERE user_id = ?", (caller_id,)
        ).fetchone()
    if row:
        return dict(row)
    return None


def save_caller(
    user_id: str,
    name: str | None = None,
    language_preference: str | None = None,
    crops_grown: str | None = None,
    land_size: str | None = None,
    district: str | None = None,
    irrigation_type: str | None = None,
    conversation_memory: str | None = None,
    db_path: str | None = None,
) -> None:
    """Upsert caller details into callers table."""
    caller_id = _validate_user_id(user_id, "save")
    now = datetime.now().isoformat()

    with sqlite3.connect(db_path or DB_PATH) as conn:
        exists = conn.execute(
            "SELECT user_id FROM callers WHERE user_id = ?", (caller_id,)
        ).fetchone()

        if exists:
            updates = []
            params = []
            for field, value in [
                ("name", name),
                ("language_preference", language_preference),
                ("crops_grown", crops_grown),
                ("land_size", land_size),
                ("district", district),
                ("irrigation_type", irrigation_type),
                ("conversation_memory", conversation_memory),
            ]:
                if value is not None:
                    updates.append(f"{field} = ?")
                    params.append(value)
            updates.append("last_interaction = ?")
            params.extend([now, caller_id])
            conn.execute(
                f"UPDATE callers SET {', '.join(updates)} WHERE user_id = ?", params
            )
        else:
            conn.execute(
                """
                INSERT INTO callers (
                    user_id, name, language_preference, crops_grown, land_size,
                    district, irrigation_type, conversation_memory, last_interaction
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    caller_id,
                    name or "Unknown",
                    language_preference or "Unknown",
                    crops_grown or "Unknown",
                    land_size or "Unknown",
                    district or "Unknown",
                    irrigation_type or "Unknown",
                    conversation_memory,
                    now,
                ),
            )


def record_outbound_opt_out(
    destination: str,
    db_path: str | None = None,
) -> None:
    """Persist a recipient's request not to receive future outbound calls."""
    normalized_destination = _validate_destination(destination)
    init_db(db_path)
    with sqlite3.connect(db_path or DB_PATH) as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO outbound_opt_outs (destination, opted_out_at)
            VALUES (?, ?)
            """,
            (normalized_destination, datetime.now().isoformat()),
        )


def is_outbound_opted_out(
    destination: str,
    db_path: str | None = None,
) -> bool:
    """Return whether a destination has opted out of outbound calls."""
    normalized_destination = _validate_destination(destination)
    init_db(db_path)
    with sqlite3.connect(db_path or DB_PATH) as conn:
        row = conn.execute(
            "SELECT 1 FROM outbound_opt_outs WHERE destination = ?",
            (normalized_destination,),
        ).fetchone()
    return row is not None
