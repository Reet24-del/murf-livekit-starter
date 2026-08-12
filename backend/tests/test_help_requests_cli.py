import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from escalation import create_or_update_help_request

BACKEND_DIR = Path(__file__).resolve().parents[1]
NOW = datetime(2026, 8, 12, 10, 30, tzinfo=ZoneInfo("Asia/Kolkata"))


def _seed_request(db_path: Path, reference_id: str = "KS-20260812-A4F2") -> None:
    create_or_update_help_request(
        caller_id=f"caller-{reference_id}",
        caller_name="Ramesh",
        reason="serious_crop_problem",
        summary="Half the tomato field is dying quickly.",
        checks_performed="Confirmed rapid spread and severe damage.",
        urgency="high",
        language="en",
        consent_confirmed=True,
        db_path=str(db_path),
        now=NOW,
        reference_factory=lambda _: reference_id,
    )


def _run_cli(*arguments: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "src/help_requests_cli.py", *arguments],
        cwd=BACKEND_DIR,
        capture_output=True,
        text=True,
        check=False,
    )


def test_list_command_returns_filtered_json(tmp_path) -> None:
    """Catch bridge output that is not parseable or ignores its filters."""
    db_path = tmp_path / "memory.db"
    _seed_request(db_path)

    result = _run_cli(
        "list",
        "--status",
        "open",
        "--urgency",
        "high",
        "--db-path",
        str(db_path),
    )

    assert result.returncode == 0
    assert result.stderr == ""
    payload = json.loads(result.stdout)
    assert [request["reference_id"] for request in payload["requests"]] == [
        "KS-20260812-A4F2"
    ]


def test_update_command_returns_changed_request(tmp_path) -> None:
    """Catch dashboard status changes that do not persist through the bridge."""
    db_path = tmp_path / "memory.db"
    _seed_request(db_path)

    result = _run_cli(
        "update",
        "--reference-id",
        "KS-20260812-A4F2",
        "--status",
        "in_progress",
        "--db-path",
        str(db_path),
    )

    assert result.returncode == 0
    assert json.loads(result.stdout)["request"]["status"] == "in_progress"


def test_invalid_status_returns_usage_error_without_json(tmp_path) -> None:
    """Catch invalid dashboard input reaching the database layer."""
    result = _run_cli(
        "list",
        "--status",
        "closed",
        "--db-path",
        str(tmp_path / "memory.db"),
    )

    assert result.returncode == 2
    assert result.stdout == ""
    assert "invalid choice" in result.stderr


def test_update_missing_reference_returns_not_found_exit_code(tmp_path) -> None:
    """Catch a missing ticket being reported as a successful update."""
    result = _run_cli(
        "update",
        "--reference-id",
        "KS-20260812-FFFF",
        "--status",
        "resolved",
        "--db-path",
        str(tmp_path / "memory.db"),
    )

    assert result.returncode == 1
    assert result.stdout == ""
    assert result.stderr == "Help request was not found.\n"
