# Day 7 Human-Help Escalation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add consent-gated human-help escalation for serious crop problems and unavailable market data, persist privacy-safe requests in SQLite, and expose a responsive in-app Help Requests dashboard.

**Architecture:** A focused Python escalation module owns validation, redaction, reference IDs, duplicate handling, persistence, filtering, and status updates. The LiveKit agent exposes one consent-gated tool that delegates to that module. A small JSON CLI bridges the existing Next.js server routes to the same Python module, while a client dashboard polls those routes and updates request status.

**Tech Stack:** Python 3.10–3.14, SQLite, pytest/pytest-asyncio, LiveKit Agents `@function_tool`, Next.js 15, React 19, TypeScript, CSS modules, Lucide React, Node's built-in test runner, Browser/IAB.

## Global Constraints

- Escalate only `serious_crop_problem` and `market_data_unavailable` for Day 7.
- Serious crop problems use `high` urgency; unavailable or stale market data uses `medium` urgency.
- `create_escalation` may run only after explicit consent in the current consent exchange.
- Refusal, ambiguous consent, or missing caller identity creates no database row.
- Save only caller identity/name, short summary, checks performed, urgency, language, `in_app` follow-up, status, and timestamps; never save the full transcript.
- Redact passwords, OTPs, PINs, account/card numbers, and long digit sequences before persistence.
- Reuse one open or in-progress request for the same caller and reason instead of creating a duplicate.
- Reference IDs use `KS-YYYYMMDD-XXXX` and remain stable when a duplicate is updated.
- Status values are exactly `open`, `in_progress`, and `resolved`.
- Never promise an immediate human reply or an SLA.
- Keep the existing Kisan Sahayak voice portal layout intact except for one restrained Human help link.
- The `/help-requests` dashboard must match the existing dark neon-green product system and work without horizontal overflow on mobile.
- Do not add Discord, Slack, email delivery, authentication, callbacks, transcript storage, or a market-price integration.
- Follow TDD for backend and server-bridge behavior: write each test, verify the expected failure, implement minimally, and verify green before continuing.

---

## File Structure

- Create `backend/src/escalation.py`: escalation domain, validation, redaction, SQLite operations, duplicate handling, and status transitions.
- Create `backend/tests/test_escalation.py`: unit/integration tests against temporary SQLite databases.
- Modify `backend/src/db.py`: initialize the `help_requests` table during normal startup.
- Modify `backend/tests/test_db.py`: prove shared database initialization includes the new table.
- Modify `backend/src/agent.py`: prompt policy, injected escalation dependency, and `create_escalation` tool.
- Modify `backend/tests/test_agent.py`: tool exposure, consent/prompt contract, success, duplicate, privacy, and failure responses.
- Create `backend/src/help_requests_cli.py`: JSON list/update bridge used by Next.js.
- Create `backend/tests/test_help_requests_cli.py`: subprocess tests for CLI JSON behavior and exit codes.
- Create `frontend/lib/help-request-values.mjs`: dependency-free runtime status/urgency constants, labels, and validators shared by Node tests and Next.js.
- Create `frontend/lib/help-request-values.d.ts`: strict TypeScript declarations for the runtime helper.
- Create `frontend/lib/help-requests.ts`: dashboard/API interfaces plus typed re-exports of the runtime helpers.
- Create `frontend/tests/help-requests.test.mjs`: Node tests for runtime status/urgency validation helpers.
- Create `frontend/lib/help-requests-server.ts`: server-only Python bridge execution and JSON parsing.
- Create `frontend/app/api/help-requests/route.ts`: filtered request listing.
- Create `frontend/app/api/help-requests/[referenceId]/route.ts`: status updates.
- Create `frontend/app/help-requests/page.tsx`: dashboard route shell and metadata.
- Create `frontend/components/app/help-requests-dashboard.tsx`: polling, filters, details, retry, and status actions.
- Create `frontend/components/app/help-requests-dashboard.module.css`: responsive dashboard visual system.
- Modify `frontend/components/app/kisan-sahayak-view.tsx`: Human help navigation link.
- Modify `frontend/components/app/voice-portal/voice-portal.module.css`: style the restrained header link.
- Modify `README.md` and `backend/README.md`: Day 7 data source, behavior, run/test/demo instructions.

---

### Task 1: Privacy-Safe Escalation Store

**Files:**
- Create: `backend/src/escalation.py`
- Create: `backend/tests/test_escalation.py`

**Interfaces:**
- Produces: `init_help_requests_table(db_path: str | None = None) -> None`
- Produces: `sanitize_help_text(value: str) -> str`
- Produces: `create_or_update_help_request(*, caller_id: str, caller_name: str | None, reason: str, summary: str, checks_performed: str, urgency: str, language: str, follow_up_method: str = "in_app", consent_confirmed: bool, db_path: str | None = None, now: datetime | None = None, reference_factory: Callable[[datetime], str] | None = None) -> dict[str, str]`
- Produces: `list_help_requests(*, status: str | None = None, urgency: str | None = None, db_path: str | None = None) -> list[dict[str, str]]`
- Produces: `update_help_request_status(reference_id: str, status: str, *, db_path: str | None = None, now: datetime | None = None) -> dict[str, str] | None`
- Produces: `EscalationValidationError(ValueError)` for rejected inputs.

- [ ] **Step 1: Write failing validation, persistence, and reference tests**

Create `backend/tests/test_escalation.py` with temporary database tests shaped like:

```python
from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

from escalation import (
    EscalationValidationError,
    create_or_update_help_request,
    list_help_requests,
    sanitize_help_text,
    update_help_request_status,
)

IST = ZoneInfo("Asia/Kolkata")
NOW = datetime(2026, 8, 12, 10, 30, tzinfo=IST)


def fixed_reference(_: datetime) -> str:
    return "KS-20260812-A4F2"


def test_create_help_request_returns_open_reference(tmp_path) -> None:
    db_path = tmp_path / "memory.db"
    request = create_or_update_help_request(
        caller_id="farmer-1",
        caller_name="Ramesh",
        reason="serious_crop_problem",
        summary="Half the tomato field is turning black.",
        checks_performed="Asked about spread and visible leaf damage.",
        urgency="high",
        language="en",
        consent_confirmed=True,
        db_path=str(db_path),
        now=NOW,
        reference_factory=fixed_reference,
    )
    assert request["reference_id"] == "KS-20260812-A4F2"
    assert request["status"] == "open"
    assert list_help_requests(db_path=str(db_path)) == [request]


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
```

- [ ] **Step 2: Run tests and verify RED**

Run:

```bash
cd backend
.venv/bin/python -m pytest tests/test_escalation.py -q
```

Expected: collection fails with `ModuleNotFoundError: No module named 'escalation'`.

- [ ] **Step 3: Add failing privacy, duplicate, filter, and status tests**

Add tests asserting:

```python
def test_sensitive_values_are_redacted_before_storage(tmp_path) -> None:
    db_path = str(tmp_path / "memory.db")
    request = create_or_update_help_request(
        caller_id="farmer-1",
        caller_name=None,
        reason="market_data_unavailable",
        summary="My OTP is 829144 and account number is 123456789012.",
        checks_performed="Password: Secret123 and exact mandi rate was unavailable.",
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


def test_duplicate_open_request_updates_existing_reference(tmp_path) -> None:
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
        reference_factory=lambda _: "KS-20260812-M001",
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
```

- [ ] **Step 4: Implement the minimal escalation module**

Implement:

```python
class EscalationValidationError(ValueError):
    pass


def sanitize_help_text(value: str) -> str:
    text = " ".join(value.strip().split())
    for pattern in SENSITIVE_PATTERNS:
        text = pattern.sub(lambda match: f"{match.groupdict().get('label') or ''}[REDACTED]", text)
    return text[:500]


def _reference_for(value: datetime) -> str:
    return f"KS-{value.strftime('%Y%m%d')}-{secrets.token_hex(2).upper()}"
```

Define case-insensitive patterns for labelled `password`, `OTP`, `PIN`, `account number`, and `card number` values plus an unlabelled fallback for digit sequences of six or more characters. Apply labelled patterns before the fallback so labels remain readable while values become `[REDACTED]`. Redact before the 500-character limit so truncation can never expose part of a sensitive value.

Use parameterized SQL only. The table includes the exact columns from the design. Before insert, query:

```sql
SELECT reference_id FROM help_requests
WHERE caller_id = ? AND reason = ? AND status IN ('open', 'in_progress')
ORDER BY created_at ASC LIMIT 1
```

When found, update the row and return it. Otherwise insert a new open row. Return dictionaries via `sqlite3.Row` and order listings by `CASE urgency WHEN 'high' THEN 0 ELSE 1 END, updated_at DESC`.

- [ ] **Step 5: Run focused and full backend tests**

Run:

```bash
cd backend
.venv/bin/python -m pytest tests/test_escalation.py -q
.venv/bin/python -m pytest -q
.venv/bin/ruff check src/escalation.py tests/test_escalation.py
```

Expected: all tests pass; Ruff prints no violations.

- [ ] **Step 6: Commit Task 1**

```bash
git add backend/src/escalation.py backend/tests/test_escalation.py
git commit -m "feat: add privacy-safe help request store"
```

---

### Task 2: Shared Database Initialization

**Files:**
- Modify: `backend/src/db.py`
- Modify: `backend/tests/test_db.py`

**Interfaces:**
- Consumes: `init_help_requests_table(db_path: str | None = None) -> None` from Task 1.
- Produces: `init_db()` that guarantees callers, outbound opt-outs, and help requests all exist.

- [ ] **Step 1: Write the failing initialization test**

Append:

```python
def test_init_db_creates_help_requests_table(tmp_path) -> None:
    db_path = tmp_path / "memory.db"
    init_db(str(db_path))
    with sqlite3.connect(db_path) as conn:
        columns = {
            row[1] for row in conn.execute("PRAGMA table_info(help_requests)")
        }
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
```

- [ ] **Step 2: Verify RED**

Run `cd backend && .venv/bin/python -m pytest tests/test_db.py::test_init_db_creates_help_requests_table -q`.

Expected: FAIL because `help_requests` has no columns.

- [ ] **Step 3: Wire initialization without a circular import**

At the end of `init_db`, after the caller/opt-out transaction closes, use a local import:

```python
from escalation import init_help_requests_table

init_help_requests_table(db_path or DB_PATH)
```

- [ ] **Step 4: Verify GREEN and commit**

```bash
cd backend
.venv/bin/python -m pytest tests/test_db.py -q
.venv/bin/ruff check src/db.py tests/test_db.py
cd ..
git add backend/src/db.py backend/tests/test_db.py
git commit -m "feat: initialize help requests with memory database"
```

---

### Task 3: Consent-Gated LiveKit Tool

**Files:**
- Modify: `backend/src/agent.py`
- Modify: `backend/tests/test_agent.py`

**Interfaces:**
- Consumes: `create_or_update_help_request(...) -> dict[str, str]` from Task 1.
- Produces: `Assistant.create_escalation(context, reason, summary, checks_performed, urgency, language, consent_confirmed, follow_up_method="in_app") -> str`.

- [ ] **Step 1: Read the test-quality rules before adding tests**

Read `/Users/reetsingh/.codex/plugins/cache/openai-curated-remote/superpowers/6.2.0/skills/test-driven-development/writing-good-tests.md` completely and apply its real-behavior and failure-reason checks.

- [ ] **Step 2: Write failing prompt and tool-contract tests**

Add assertions such as:

```python
def test_human_help_tool_is_exposed() -> None:
    assert hasattr(Assistant, "create_escalation")


def test_prompt_requires_two_triggers_and_explicit_consent() -> None:
    prompt = SYSTEM_PROMPT.lower()
    assert "serious crop" in prompt
    assert "missing or stale market data" in prompt
    assert "ask for explicit permission" in prompt
    assert "if the caller says no" in prompt
    assert "do not call `create_escalation`" in prompt
    assert "never promise" in prompt


def test_escalation_tool_description_is_consent_gated() -> None:
    description = Assistant.create_escalation.info.description.lower()
    assert "only after" in description
    assert "explicitly agrees" in description
    assert "never" in description
    assert "full conversation" in description
```

- [ ] **Step 3: Verify RED**

Run `cd backend && .venv/bin/python -m pytest tests/test_agent.py -q`.

Expected: FAIL because the method and prompt rules are absent.

- [ ] **Step 4: Add injected-tool behavior tests**

Use a fake room participant identity and an injected creator that records keyword arguments. Assert:

- false consent returns `No human-help request was created because explicit consent was not confirmed.` and does not call the creator;
- a `consent_confirmed=True` argument still creates nothing when the latest caller turn is not an explicit affirmative;
- an explicit latest turn such as `Yes, create the request` permits the creator, while `No, do not share it` blocks it;
- success passes the derived caller identity and saved name;
- success includes the returned reference ID, `open`, dashboard next step, and no immediate-reply promise;
- creator failure returns the Kisan Call Center fallback and no invented `KS-` value.

Construct the assistant with:

```python
captured: dict[str, object] = {}

def creator(**kwargs):
    captured.update(kwargs)
    return {"reference_id": "KS-20260812-A4F2", "status": "open"}

assistant = Assistant(
    profile_lookup=lambda user_id: {"name": "Ramesh"},
    escalation_creator=creator,
)
```

- [ ] **Step 5: Implement prompt policy and tool**

Add a `HUMAN HELP` prompt section that explicitly states the trigger, consent, structured summary, refusal, privacy, reference, and honest-next-step rules in English while relying on the existing turn-language instruction for output language.

Extend `Assistant.__init__`:

```python
escalation_creator: Callable[..., dict[str, str]] = create_or_update_help_request,
```

Store it as `self._escalation_creator`, initialize `self._latest_user_text = ""`, and update that field inside `on_user_turn_completed`. Add a small affirmative-consent helper that checks the latest complete caller turn, rejects explicit negatives first (`no`, `do not`, `don't`, `nahi`, `नहीं`), and accepts explicit English, Hindi, or Hinglish affirmatives (`yes`, `yes please`, `yes create the request`, `haan`, `haan bana do`, `हाँ`, `हां`, `हाँ बनाइए`). The tool must require both `consent_confirmed=True` and that latest-turn check before any lookup/write, derive identity with `_caller_identity`, use `_profile_lookup` for an optional saved name, delegate to the creator, and return concise natural tool output.

- [ ] **Step 6: Verify GREEN and commit**

```bash
cd backend
.venv/bin/python -m pytest tests/test_agent.py tests/test_escalation.py -q
.venv/bin/ruff check src/agent.py tests/test_agent.py
cd ..
git add backend/src/agent.py backend/tests/test_agent.py
git commit -m "feat: add consent-gated human escalation tool"
```

---

### Task 4: JSON Bridge and Next.js API

**Files:**
- Create: `backend/src/help_requests_cli.py`
- Create: `backend/tests/test_help_requests_cli.py`
- Create: `frontend/lib/help-request-values.mjs`
- Create: `frontend/lib/help-request-values.d.ts`
- Create: `frontend/lib/help-requests.ts`
- Create: `frontend/tests/help-requests.test.mjs`
- Create: `frontend/lib/help-requests-server.ts`
- Create: `frontend/app/api/help-requests/route.ts`
- Create: `frontend/app/api/help-requests/[referenceId]/route.ts`
- Modify: `frontend/package.json`

**Interfaces:**
- Produces CLI: `python src/help_requests_cli.py list --status open --urgency high --db-path /tmp/help-requests-demo.db` returning a JSON object with a `requests` array.
- Produces CLI: `python src/help_requests_cli.py update --reference-id KS-20260812-A4F2 --status in_progress --db-path /tmp/help-requests-demo.db` returning a JSON object with one `request`.
- Produces API: `GET /api/help-requests?status=open&urgency=high`.
- Produces API: `PATCH /api/help-requests/KS-20260812-A4F2` with `{"status":"in_progress"}`.

- [ ] **Step 1: Write failing CLI subprocess tests**

Create tests that seed a temporary DB through `create_or_update_help_request`, then call the CLI with `sys.executable` and assert JSON, filtering, updates, invalid status exit code `2`, and missing reference exit code `1`.

Example:

```python
result = subprocess.run(
    [
        sys.executable,
        "src/help_requests_cli.py",
        "list",
        "--status",
        "open",
        "--db-path",
        str(db_path),
    ],
    cwd=BACKEND_DIR,
    capture_output=True,
    text=True,
    check=False,
)
assert result.returncode == 0
assert json.loads(result.stdout)["requests"][0]["reference_id"].startswith("KS-")
```

- [ ] **Step 2: Verify CLI RED, implement, and verify GREEN**

Run:

```bash
cd backend
.venv/bin/python -m pytest tests/test_help_requests_cli.py -q
```

Expected RED: CLI file missing. Implement `argparse` subcommands, use only the escalation module, print one JSON object to stdout, print safe errors to stderr, and return the specified exit codes. Re-run until green.

- [ ] **Step 3: Write failing frontend helper tests**

Create `frontend/tests/help-requests.test.mjs` with `node:test` and `node:assert/strict`. Import `isHelpRequestStatus`, `isHelpRequestUrgency`, `HELP_REQUEST_STATUS_LABELS`, and `HELP_REQUEST_URGENCY_LABELS` from `../lib/help-request-values.mjs`. Assert all three supported statuses and both supported urgency values pass, unknown values fail, and labels equal `Open`, `In progress`, `Resolved`, `High`, and `Medium`. Add:

```json
"test:unit": "node --test tests/*.test.mjs"
```

Run `cd frontend && pnpm test:unit` and verify RED because the helper module is missing.

- [ ] **Step 4: Implement shared types/helpers and server bridge**

Implement `help-request-values.mjs` as plain ESM with frozen value arrays, label objects, and string-membership validators. Declare those exact exports and the `HelpRequestStatus`/`HelpRequestUrgency` unions in `help-request-values.d.ts`. Define the `HelpRequest` interface in `help-requests.ts`, import the union types, and re-export the runtime values and types so the rest of the TypeScript app has one public module. In `help-requests-server.ts`, resolve:

```typescript
const backendDir = path.join(process.cwd(), '../backend');
const python = process.env.HELP_REQUESTS_PYTHON ?? path.join(backendDir, '.venv/bin/python');
const script = path.join(backendDir, 'src/help_requests_cli.py');
const database = process.env.HELP_REQUESTS_DB_PATH ?? path.join(backendDir, 'memory.db');
```

Execute with `execFile`, never a shell string, and parse one JSON object.

- [ ] **Step 5: Implement route validation**

`GET` rejects unknown status/urgency with `400`. `PATCH` validates `/^KS-\d{8}-[A-F0-9]{4}$/`, parses JSON, accepts only supported status, returns `404` for a missing reference, and returns a generic `500` without leaking commands or paths.

- [ ] **Step 6: Verify API code and commit**

```bash
cd backend
.venv/bin/python -m pytest tests/test_help_requests_cli.py -q
.venv/bin/ruff check src/help_requests_cli.py tests/test_help_requests_cli.py
cd ../frontend
pnpm test:unit
pnpm exec tsc --noEmit
cd ..
git add backend/src/help_requests_cli.py backend/tests/test_help_requests_cli.py frontend/lib/help-request-values.mjs frontend/lib/help-request-values.d.ts frontend/lib/help-requests.ts frontend/tests/help-requests.test.mjs frontend/lib/help-requests-server.ts frontend/app/api/help-requests frontend/package.json
git commit -m "feat: expose help requests through local API"
```

---

### Task 5: Kisan Sahayak Help Requests Dashboard

**Files:**
- Create: `frontend/app/help-requests/page.tsx`
- Create: `frontend/components/app/help-requests-dashboard.tsx`
- Create: `frontend/components/app/help-requests-dashboard.module.css`
- Modify: `frontend/components/app/kisan-sahayak-view.tsx`
- Modify: `frontend/components/app/voice-portal/voice-portal.module.css`

**Interfaces:**
- Consumes: API and `HelpRequest` types from Task 4.
- Produces: responsive `/help-requests` operational dashboard with polling and status controls.

- [ ] **Step 1: Generate and inspect one matching dashboard concept before coding**

Use the existing Kisan Sahayak concept image as visual reference and generate a single desktop dashboard concept with the exact current palette, typography character, borders, restrained glow, and table/list density. The concept must show the allowed copy only: `Kisan Sahayak`, `Human help requests`, `Back to voice assistant`, counts, filters, request fields, and status actions. Inspect both the existing concept and generated dashboard concept with `view_image`, then record tokens and layout inventory in working notes.

- [ ] **Step 2: Add a failing route smoke check**

Before creating the page, run `cd frontend && pnpm build` and record that `/help-requests` is absent from the generated route list. This is the RED gate for the route deliverable.

- [ ] **Step 3: Implement page shell and dashboard state**

Create a client component with:

```typescript
const [statusFilter, setStatusFilter] = useState<'all' | HelpRequestStatus>('all');
const [urgencyFilter, setUrgencyFilter] = useState<'all' | HelpRequestUrgency>('all');
const [requests, setRequests] = useState<HelpRequest[]>([]);
const [selectedReference, setSelectedReference] = useState<string | null>(null);
const [loading, setLoading] = useState(true);
const [error, setError] = useState<string | null>(null);
```

Fetch immediately and every 3 seconds while `document.visibilityState === 'visible'`. Preserve the last successful list on fetch errors. Status buttons call PATCH, replace the returned row in local state, and then refresh.

- [ ] **Step 4: Implement faithful responsive styling**

Use the existing portal's background, green/violet accent balance, 1px translucent green borders, typography, and focus style. Desktop uses one open table/list surface rather than a card grid. Mobile collapses each row into a compact labeled block. Add `prefers-reduced-motion` handling and visible keyboard focus.

- [ ] **Step 5: Add restrained portal navigation**

Add a `Human help` link beside Reset memory without changing the voice-stage order or first-view composition. On narrow screens it remains reachable without overlapping connection status.

- [ ] **Step 6: Build and browser-test the core workflow**

Run `pnpm build` and `pnpm exec tsc --noEmit`. Start the local app, then use Browser/IAB to verify:

1. `/help-requests` loads and shows seeded rows;
2. status and urgency filters work;
3. expanding a request reveals `checks_performed` and created time;
4. moving open → in progress → resolved updates the row;
5. API failure shows retry without deleting the last successful list;
6. the voice portal link opens the dashboard and Back returns home;
7. mobile viewport has no horizontal overflow.

Capture desktop and mobile screenshots. Inspect them with `view_image` beside the generated concept. Write a fidelity ledger covering copy, layout, typography, palette, container model, icons, responsiveness, and core interactions; fix every material mismatch.

- [ ] **Step 7: Commit Task 5**

```bash
git add frontend/app/help-requests frontend/components/app/help-requests-dashboard.tsx frontend/components/app/help-requests-dashboard.module.css frontend/components/app/kisan-sahayak-view.tsx frontend/components/app/voice-portal/voice-portal.module.css
git commit -m "feat: add human help request dashboard"
```

---

### Task 6: Day 7 Documentation

**Files:**
- Modify: `README.md`
- Modify: `backend/README.md`

**Interfaces:**
- Documents the local SQLite data source, dashboard URL, triggers, consent/privacy behavior, statuses, tests, and video script.

- [ ] **Step 1: Write a failing documentation assertion**

Run:

```bash
rg -n "Day 7|help-requests|serious crop|market data|explicit consent|\[REDACTED\]|in_progress" README.md backend/README.md
```

Expected: required Day 7 terms are absent or incomplete.

- [ ] **Step 2: Add exact documentation**

Document:

- requests are live local SQLite records in `backend/memory.db`, not an external help desk;
- the two trigger reasons and urgency mapping;
- the exact information shared after consent;
- sensitive redaction and no transcript storage;
- duplicate handling and status meanings;
- `/help-requests` and how to run frontend/backend;
- the serious, refusal, normal, and market demo prompts;
- the honest next step and Kisan Call Center fallback;
- the Day 7 LinkedIn requirements including Murf Falcon and `#VoiceForBharat`.

- [ ] **Step 3: Verify docs and commit**

Run the `rg` command again and `git diff --check README.md backend/README.md`, then:

```bash
git add README.md backend/README.md
git commit -m "docs: explain Day 7 human escalation workflow"
```

---

### Task 7: Full Verification and Demo Readiness

**Files:**
- Verify all files from Tasks 1–6.
- Update tests or implementation only when a failing check proves a defect.

**Interfaces:**
- Produces a verified browser-based Day 7 workflow and evidence for the demo video.

- [ ] **Step 1: Run the complete backend quality gate**

```bash
cd backend
.venv/bin/python -m pytest -q
.venv/bin/ruff check .
.venv/bin/ruff format --check .
```

Expected: all pass with no warnings from changed files.

- [ ] **Step 2: Run the complete frontend quality gate**

```bash
cd frontend
pnpm test:unit
pnpm exec tsc --noEmit
pnpm format:check
pnpm build
```

Expected: all pass and `/help-requests` appears in the route output.

- [ ] **Step 3: Start the browser agent and execute the serious path**

Use a fresh caller ID. Say: `My tomato plants are suddenly black and half the field is dying.` Verify the agent explains human help, states the fields it will share, and asks permission without creating a row. Say `Yes, create the request.` Verify one row appears, the spoken response includes the stored reference ID, and no immediate-reply promise is made.

- [ ] **Step 4: Execute refusal, normal, and market paths**

- Refusal: repeat a severe problem with a different caller and answer `No`; row count stays unchanged.
- Normal: ask `How often should I water tomatoes?`; no escalation offer or row.
- Market: ask `What is today's exact tomato mandi price?`; the agent offers a medium human request and creates it only after consent.

- [ ] **Step 5: Verify privacy and duplicate behavior in the real UI**

Create a consented request containing a fake `OTP 829144` and `account number 123456789012`. Verify the dashboard displays `[REDACTED]`, never the digits. Recreate the same reason for the same caller and verify the original reference ID remains and the row updates rather than duplicates.

- [ ] **Step 6: Final visual fidelity review**

Inspect desktop and mobile dashboard screenshots alongside the generated concept with `view_image`. Confirm exact allowed copy, dark palette, green/violet balance, row/table density, readable typography, restrained glow, no invented cards or badges, faithful icons, keyboard focus, and no mobile overflow. Record any intentional deviation; fix all unintentional drift.

- [ ] **Step 7: Review repository safety and commit fixes**

```bash
git status --short
git diff --check
git log --oneline -8
```

Confirm `.env.local`, SQLite data, credentials, OTPs, phone numbers, screenshots containing private data, and generated runtime logs are not staged. Commit only verified corrective changes with a scoped message such as `fix: harden Day 7 escalation workflow`.

- [ ] **Step 8: Prepare the handoff**

Report:

- backend test count and quality-gate results;
- frontend build/type/unit/format results;
- browser paths tested;
- one created reference ID using non-sensitive demo data;
- dashboard desktop/mobile screenshot paths;
- fidelity ledger result and any intentional deviations;
- exact start commands;
- four demo prompts and expected outcomes;
- the Git branch/commit state and whether changes are pushed.
