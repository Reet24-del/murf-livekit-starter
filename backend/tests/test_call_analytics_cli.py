import json
import subprocess
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

from call_analytics import CallRecord, record_call

SCRIPT = Path(__file__).parents[1] / "src" / "call_analytics_cli.py"


def test_summary_cli_returns_real_filtered_json(tmp_path) -> None:
    db_path = tmp_path / "analytics.db"
    ended_at = datetime.now(UTC) - timedelta(minutes=1)
    record_call(
        CallRecord(
            call_id="cli-call",
            started_at=ended_at - timedelta(seconds=12),
            ended_at=ended_at,
            duration_seconds=12,
            channel="browser",
            language="en",
            outcome="successful",
            result_category="live_weather_delivered",
            failure_category=None,
        ),
        db_path=str(db_path),
    )

    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "summary",
            "--days",
            "7",
            "--channel",
            "browser",
            "--db-path",
            str(db_path),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    payload = json.loads(result.stdout)

    assert payload["summary"]["total_calls"] == 1
    assert payload["recent_calls"][0]["result_category"] == "live_weather_delivered"
    assert "transcript" not in result.stdout.casefold()
