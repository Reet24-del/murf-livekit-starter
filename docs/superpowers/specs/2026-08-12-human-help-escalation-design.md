# Day 7 Human-Help Escalation Design

## Goal

Teach Kisan Sahayak to recognize two situations that need a human expert, ask the farmer for permission before sharing a short summary, save a real help request, and give the farmer an honest reference ID and next step. Normal farming conversations must not create requests.

## Escalation reasons

Kisan Sahayak escalates only these Day 7 situations:

1. **Serious crop problem** — the farmer reports severe, rapidly spreading, or unexplained crop damage, disease, pest attack, or large crop loss that cannot be safely resolved through generic voice guidance. Urgency is `high`.
2. **Missing or stale market data** — the farmer needs a current market price or market decision, but the agent has no reliable current source or the available data is old. Urgency is `medium`.

A normal advice request, weather lookup, crop-suitability question, or memory request does not trigger human help.

## Consent flow

The model must not call `create_escalation` on the first alarming or unsupported request. It first states, in the caller's current language, that a human expert would be more appropriate and names the exact fields it proposes to share:

- the caller identity or saved name when available;
- a short description of what happened;
- what Kisan Sahayak already checked;
- the urgency level;
- the current conversation language;
- the preferred follow-up method, fixed to `in_app` for this implementation.

It then asks for clear permission. The tool description and system prompt both state that the tool may be called only after the caller explicitly agrees in that consent exchange. A refusal or ambiguous reply creates no database row.

## Tool contract

`Assistant.create_escalation` is a LiveKit `@function_tool` with these arguments:

- `reason`: `serious_crop_problem` or `market_data_unavailable`;
- `summary`: concise factual description of the problem;
- `checks_performed`: concise description of advice or data checks already completed;
- `urgency`: `high` for serious crop problems or `medium` for market data;
- `language`: `en`, `hi`, or `hinglish` from the current turn;
- `consent_confirmed`: must be `true`;
- `follow_up_method`: defaults to and only accepts `in_app`.

The tool derives the caller ID from the LiveKit participant and optionally reads the saved caller name. It rejects a missing caller identity, false consent, invalid reason, mismatched urgency, unsupported language, empty summary, empty checks, or unsupported follow-up method.

On success it returns natural-language tool output containing a reference such as `KS-20260812-A4F2`, status `open`, and an honest next step: the request is visible to a human in the Help Requests dashboard; no immediate reply time is promised.

## Persistence and privacy

The existing `backend/memory.db` SQLite database gains a `help_requests` table:

- `reference_id` primary key;
- `caller_id`;
- `caller_name` nullable;
- `reason`;
- `summary`;
- `checks_performed`;
- `urgency`;
- `language`;
- `follow_up_method`;
- `status` (`open`, `in_progress`, or `resolved`);
- `created_at` and `updated_at` ISO timestamps.

Only the short structured summary is saved; the full transcript is never stored in this table.

Before persistence, a redaction function removes likely passwords, OTPs, PINs, card/account numbers, and long digit sequences from the summary and checks. The saved text uses `[REDACTED]` in their place. Validation also limits each free-text field to 500 characters.

To prevent duplicates, a request with the same caller ID and reason that is still `open` or `in_progress` is updated instead of creating a second row. It keeps its original reference ID and creation time, replaces the sanitized summary/checks, updates urgency/language/follow-up, and refreshes `updated_at`.

## Backend boundaries

`backend/src/escalation.py` owns escalation validation, redaction, reference generation, persistence, duplicate handling, list/query operations, and status updates. The functions accept an optional database path so tests use isolated temporary databases.

`backend/src/agent.py` owns conversational policy and exposes the LiveKit tool. It delegates storage to `escalation.py` and does not build SQL itself.

`backend/src/db.py` remains responsible for initializing shared database tables and calls the escalation-table initializer so the table exists during normal agent startup.

## Dashboard and API

The frontend adds a dedicated `/help-requests` route that matches the current dark neon-green Kisan Sahayak product theme. It is an operational dashboard, not a marketing page.

The page contains:

- a compact header with Kisan Sahayak branding, a link back to the voice assistant, and an open-request count;
- status filters for all, open, in progress, and resolved;
- urgency filters for all, high, and medium;
- a readable desktop table/list with reference ID, caller, reason, summary, urgency, language, follow-up method, updated time, and status;
- a detail drawer or expanded region for `checks_performed` and creation time;
- status actions that move a request between open, in progress, and resolved;
- a clear empty state;
- a responsive mobile layout that turns each row into a single compact request block without horizontal overflow.

The existing voice portal gains one restrained `Human help` navigation link in the header. The voice-first home layout otherwise stays unchanged.

`GET /api/help-requests` returns sanitized requests with optional status and urgency filters. `PATCH /api/help-requests/[referenceId]` accepts only the three supported statuses and updates one request. The route invokes a small Python bridge that calls the same escalation module rather than duplicating SQLite and redaction rules in TypeScript.

The dashboard polls while visible so an escalation created during a voice demo appears without a manual database inspection. A short refresh interval is acceptable for the local challenge demo.

## Error handling

- If consent is absent, the tool returns that no request was created.
- If identity is absent, the tool asks the caller to reconnect so a safe reference can be tied to them.
- If storage fails, the agent says the request could not be created and provides the existing Kisan Call Center number as a fallback. It never invents a reference ID.
- Dashboard API failures show an inline retry state and retain the last successfully loaded list.
- Invalid dashboard filters or status updates receive a `400` or `404` response rather than changing arbitrary data.

## Testing

Backend tests are written first and must fail before implementation. They cover:

- table creation and reference ID format;
- consent rejection;
- reason/urgency validation;
- sensitive-data redaction;
- full-transcript absence from stored records;
- duplicate update behavior and stable reference ID;
- list filtering and status changes;
- agent tool exposure and description;
- system prompt requirements for the two triggers, explicit consent, refusal, short summaries, privacy, reference IDs, and honest next steps;
- tool success and failure responses using a temporary database.

Frontend verification covers:

- API list/filter/status behavior;
- dashboard build and lint/type checks;
- desktop and mobile rendering;
- status filters, urgency filters, request expansion, and status updates;
- empty and failure states;
- navigation between the voice portal and dashboard.

End-to-end manual conversations:

1. Serious path: “My tomato plants are suddenly black and half the field is dying.” The agent proposes human help, lists what it will share, asks permission, creates the request only after “yes,” speaks the returned reference ID, and the request appears in the dashboard.
2. Refusal path: the same problem followed by “no.” No request is created.
3. Normal path: “How often should I water tomatoes?” The agent answers normally and creates no request.
4. Market path: “What is today's exact tomato mandi price?” The agent explains that reliable current data is unavailable, offers a human request, and creates a medium-urgency request only after consent.

## Documentation and demo

README sections state that Day 7 uses a local SQLite dataset for human-help requests, not an external help-desk service. They document the two triggers, privacy behavior, consent gate, dashboard URL, status workflow, and three test conversations.

The recording should show the serious crop conversation, the consent question, the spoken reference ID, the new dashboard row, and one normal conversation with no new row.

## Out of scope

- Discord, Slack, or email delivery;
- automatic outbound callbacks after resolution;
- staff authentication or multi-user authorization;
- SLA promises;
- storing full transcripts;
- adding a market-price data integration on Day 7.
