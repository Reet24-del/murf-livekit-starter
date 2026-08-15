# Call Analytics Dashboard Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Record privacy-safe outcomes for every browser and SIP call and expose real metrics through a responsive Field Intelligence analytics dashboard.

**Architecture:** A focused Python analytics module owns the SQLite schema, deterministic lifecycle tracker, aggregation, filters, and privacy validation. Browser and SIP workers each create one tracker and finalize it through the LiveKit job shutdown callback. A small JSON CLI bridges the existing Next.js server to SQLite; the React dashboard polls that API and renders the approved `design.md` without seeded values.

**Tech Stack:** Python 3.14, SQLite, LiveKit Agents 1.4, pytest, Next.js 15, React 19, TypeScript, Node test runner, CSS Modules, inline accessible SVG charts.

## Global Constraints

- Success means the farmer asks at least one farming or weather question and receives a complete answer, live-data result, or confirmed expert request before the call ends.
- Store only random call ID, timestamps, duration, channel, language, outcome, controlled result category, and controlled failure category.
- Never store or return caller identity, phone number, profile facts, summaries, or transcript text.
- Use real SQLite records only; no sample, seeded, or hardcoded analytics values.
- Follow the Field Intelligence palette, typography, navigation rail, open metric hierarchy, single chart canvas, and ledger defined in `design.md`.
- Refresh every five seconds only while visible and preserve the last successful payload during transient errors.
- Support desktop, tablet, and 320-pixel mobile layouts without horizontal page overflow.

---

### Task 1: Privacy-safe analytics model and aggregation

**Files:**
- Create: `backend/src/call_analytics.py`
- Create: `backend/tests/test_call_analytics.py`
- Modify: `backend/src/db.py`
- Modify: `backend/tests/test_db.py`

**Interfaces:**
- Produces: `CallTracker(channel, started_at=None, recorder=record_call)`, `observe_user(text)`, `observe_assistant(text)`, `mark_result(category)`, `mark_failure(category)`, and `finalize(ended_at=None)`.
- Produces: `record_call(record, db_path=None)`, `get_call_analytics(filters, db_path=None)`, and `init_call_analytics_table(db_path=None)`.
- Produces controlled literals for channel, language, outcome, result, and failure values.

- [ ] Write failing tests proving a successful browser call, incomplete call, tool failure, idempotent finalization, strict enum validation, privacy-safe schema, aggregate reconciliation, date/channel/language/outcome filters, trend buckets, and recent-call ordering.
- [ ] Run `.venv/bin/python -m pytest -q tests/test_call_analytics.py tests/test_db.py` and verify failures are caused by the missing module/table.
- [ ] Implement the minimal SQLite schema, lifecycle tracker, validation, and aggregation functions.
- [ ] Run the focused tests and verify they pass.
- [ ] Run Ruff on the new Python files.

### Task 2: Browser and SIP lifecycle instrumentation

**Files:**
- Modify: `backend/src/agent.py`
- Modify: `backend/src/telephony/outbound/agent.py`
- Modify: `backend/tests/test_agent.py`
- Modify: `backend/tests/test_outbound_agent.py`

**Interfaces:**
- Consumes: `CallTracker` from Task 1.
- Browser worker creates `CallTracker("browser")`, observes conversation events, marks weather/escalation outcomes, and finalizes through `ctx.add_shutdown_callback`.
- SIP worker creates `CallTracker("sip")`, records no-answer/dial failures, observes conversation events, marks advisory/opt-out results, and finalizes exactly once.

- [ ] Write failing tests for browser tool success/failure markers, browser shutdown persistence, SIP advisory success, SIP no-answer failure, and duplicate shutdown protection.
- [ ] Run the focused agent tests and verify the expected failures.
- [ ] Inject the tracker into both agents and register lifecycle/event hooks without storing conversation text.
- [ ] Run the focused tests and verify they pass.
- [ ] Run all offline backend tests and Ruff.

### Task 3: Analytics bridge and Next.js API

**Files:**
- Create: `backend/src/call_analytics_cli.py`
- Create: `backend/tests/test_call_analytics_cli.py`
- Create: `frontend/lib/call-analytics-values.mjs`
- Create: `frontend/lib/call-analytics.ts`
- Create: `frontend/lib/call-analytics-server.ts`
- Create: `frontend/app/api/call-analytics/route.ts`
- Create: `frontend/tests/call-analytics.test.mjs`

**Interfaces:**
- CLI: `call_analytics_cli.py summary --days N [--channel ...] [--language ...] [--outcome ...] --db-path PATH` emits one JSON payload.
- API: `GET /api/call-analytics?days=7&channel=all&language=all&outcome=all` returns `{ summary, trend, breakdowns, recent_calls, generated_at }` with `Cache-Control: no-store`.

- [ ] Write failing Python CLI tests and Node validation/query tests.
- [ ] Run the focused tests and verify missing-module failures.
- [ ] Implement strict validators, CLI JSON serialization, server bridge, and route error handling.
- [ ] Run focused tests, TypeScript, and format checks.

### Task 4: Field Intelligence dashboard

**Files:**
- Create: `frontend/app/call-analytics/page.tsx`
- Create: `frontend/components/app/call-analytics-dashboard.tsx`
- Create: `frontend/components/app/call-analytics-dashboard.module.css`
- Create: `frontend/components/app/call-analytics-chart.tsx`
- Modify: `frontend/components/app/kisan-sahayak-view.tsx`
- Modify: `frontend/components/app/help-requests-dashboard.tsx`
- Modify: `frontend/app/layout.tsx`

**Interfaces:**
- Dashboard polls `/api/call-analytics` every five seconds while visible.
- Filters update every dashboard region from the same payload.
- Chart renders accessible SVG paths from `trend`; ledger renders controlled result labels only.

- [ ] Implement the shared Field Intelligence navigation and exact approved visible copy from `design.md`.
- [ ] Implement open outcome metrics, proportional outcome bar, single chart canvas, breakdown strips, skeleton/error/zero states, and responsive ledger.
- [ ] Add Call analytics navigation to the voice and human-request pages.
- [ ] Run unit tests, TypeScript, formatting, and production build.

### Task 5: End-to-end and visual verification

**Files:**
- Create: `design-qa-day8.md`
- Modify: `README.md`
- Modify: `backend/README.md`

**Interfaces:**
- Documents the success definition, live/local SQLite source, stored privacy fields, test script, and dashboard URL.

- [ ] Start the updated backend and frontend without stopping unrelated processes.
- [ ] Create one successful lifecycle record through the real tracker path and verify total/success reconciliation through the API and dashboard.
- [ ] Verify one incomplete lifecycle increments failed exactly once.
- [ ] Exercise filters, refresh, zero/error states, desktop viewport, current viewport, and 320-pixel layout in the in-app browser.
- [ ] Capture the final dashboard, compare it with the approved Field Intelligence concept using `view_image`, and record at least five fidelity checks in `design-qa-day8.md`.
- [ ] Run the complete backend/frontend verification suite and report any external-only checks separately.
