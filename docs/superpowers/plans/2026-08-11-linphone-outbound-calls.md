# Linphone Outbound Farm Advisory Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a consent-gated LiveKit SIP outbound agent that calls a controlled Linphone account and delivers a bilingual live rain advisory through Murf Falcon.

**Architecture:** A pure `call_config.py` module validates dispatch metadata, consent, destinations, language, and IST quiet hours. A CLI dispatches a separately named LiveKit worker, while the worker revalidates safety, dials through the configured SIP trunk, uses the existing Open-Meteo service, and persists opt-outs in the existing SQLite database.

**Tech Stack:** Python 3.10+, LiveKit Agents 1.4, LiveKit SIP API, Linphone SIP, Murf Falcon, Deepgram Nova-3, Google Gemini, SQLite, Open-Meteo, pytest, Ruff.

## Global Constraints

- Call only a destination owned by the operator or whose recipient consented.
- Require `--consent-confirmed` before creating any room or dispatch.
- Refuse destinations stored in the persistent opt-out table.
- Default calling hours are 08:00 through 19:59 Asia/Kolkata; an explicit demo override is required outside that window.
- The first two sentences must state Kisan Sahayak's identity, the rain-advisory reason, and how to stop future calls.
- Hindi must be written in Devanagari, never romanized; English must remain English.
- Use live Open-Meteo data with its timestamp, and never invent weather values on failure.
- Use Murf Falcon with the Anisha voice.
- Never commit personal Linphone credentials, a real SIP username, API secrets, or the local SQLite database.
- Preserve all unrelated dirty-worktree changes.

---

### Task 1: Persistent outbound opt-out state

**Files:**
- Modify: `backend/src/db.py`
- Modify: `backend/tests/test_db.py`

**Interfaces:**
- Produces: `record_outbound_opt_out(destination: str, db_path: str | None = None) -> None`
- Produces: `is_outbound_opted_out(destination: str, db_path: str | None = None) -> bool`

- [ ] **Step 1: Write failing opt-out tests**

```python
def test_outbound_opt_out_blocks_only_normalized_destination(tmp_path) -> None:
    db_path = str(tmp_path / "callers.db")
    init_db(db_path)
    record_outbound_opt_out("  farmer.demo  ", db_path)
    assert is_outbound_opted_out("farmer.demo", db_path) is True
    assert is_outbound_opted_out("another.farmer", db_path) is False


def test_outbound_opt_out_rejects_blank_destination(tmp_path) -> None:
    with pytest.raises(ValueError, match="destination"):
        record_outbound_opt_out("   ", str(tmp_path / "callers.db"))
```

- [ ] **Step 2: Run `uv run pytest tests/test_db.py -q` and verify import failures for the new functions**

- [ ] **Step 3: Add the `outbound_opt_outs(destination TEXT PRIMARY KEY, opted_out_at TEXT NOT NULL)` table and normalized lookup/write functions**

```python
def record_outbound_opt_out(destination: str, db_path: str | None = None) -> None:
    normalized = _validated_destination(destination)
    init_db(db_path)
    with sqlite3.connect(db_path or DB_PATH) as conn:
        conn.execute(
            "INSERT OR REPLACE INTO outbound_opt_outs(destination, opted_out_at) VALUES (?, ?)",
            (normalized, datetime.now().isoformat()),
        )
```

- [ ] **Step 4: Run `uv run pytest tests/test_db.py -q` and verify all database tests pass**

### Task 2: Safe metadata and language contract

**Files:**
- Create: `backend/src/telephony/__init__.py`
- Create: `backend/src/telephony/outbound/__init__.py`
- Create: `backend/src/telephony/outbound/call_config.py`
- Create: `backend/tests/test_outbound_call_config.py`

**Interfaces:**
- Produces: `CallSafetyError(ValueError)`
- Produces: `OutboundCallMetadata(destination: str, district: str, language: Literal["en", "hi"], crop: str | None, consent_confirmed: bool, quiet_hours_override: bool)`
- Produces: `OutboundCallMetadata.to_json() -> str`
- Produces: `OutboundCallMetadata.from_json(value: str) -> OutboundCallMetadata`
- Produces: `validate_call_request(metadata, now=None, override_quiet_hours=False) -> None`
- Produces: `opening_greeting(language: str) -> str`
- Produces: `turn_language_instruction(text: str) -> str`

- [ ] **Step 1: Write failing tests with literal expectations for Linphone/E.164 validation, metadata round-trip, consent, quiet hours, and both opening scripts**

```python
metadata = OutboundCallMetadata(
    destination="farmer.demo",
    district="Lucknow",
    language="hi",
    crop="tomato",
    consent_confirmed=True,
    quiet_hours_override=False,
)
assert OutboundCallMetadata.from_json(metadata.to_json()) == metadata
assert "किसान सहायक" in opening_greeting("hi")
assert "stop calls" in opening_greeting("en").lower()
with pytest.raises(CallSafetyError, match="consent"):
    validate_call_request(replace(metadata, consent_confirmed=False), allowed_time)
```

- [ ] **Step 2: Run `uv run pytest tests/test_outbound_call_config.py -q` and verify the missing-module failure**

- [ ] **Step 3: Implement the frozen metadata dataclass, strict JSON parsing, destination patterns, IST quiet-hours check, fixed greetings, and native-script turn instruction**

```python
@dataclass(frozen=True)
class OutboundCallMetadata:
    destination: str
    district: str
    language: Literal["en", "hi"] = "en"
    crop: str | None = None
    consent_confirmed: bool = False
    quiet_hours_override: bool = False
```

- [ ] **Step 4: Run the focused tests and `uv run ruff check src/telephony tests/test_outbound_call_config.py`**

### Task 3: Consent-gated LiveKit dispatch CLI

**Files:**
- Create: `backend/src/telephony/outbound/dial.py`
- Create: `backend/tests/test_outbound_dial.py`

**Interfaces:**
- Consumes: `OutboundCallMetadata`, `validate_call_request`, `is_outbound_opted_out`
- Produces: `async dispatch_call(metadata, room_name, livekit_api=None) -> str`
- Produces: `build_parser() -> argparse.ArgumentParser`
- Produces: `main(argv: Sequence[str] | None = None) -> int`

- [ ] **Step 1: Write failing CLI tests proving missing consent, invalid destination, quiet hours, and opted-out destinations return nonzero before `dispatch_call` is reached**

```python
def test_main_refuses_missing_consent(capsys) -> None:
    result = main(["--to", "farmer.demo", "--district", "Lucknow"])
    assert result == 2
    assert "consent" in capsys.readouterr().err.lower()
```

- [ ] **Step 2: Run `uv run pytest tests/test_outbound_dial.py -q` and verify the missing-module failure**

- [ ] **Step 3: Implement argument parsing, pre-dispatch safety and opt-out checks, unique room naming, LiveKit room creation, and `outbound-agent` dispatch metadata**

```python
await client.agent_dispatch.create_dispatch(
    api.CreateAgentDispatchRequest(
        agent_name="outbound-agent",
        room=room_name,
        metadata=metadata.to_json(),
    )
)
```

- [ ] **Step 4: Run the focused CLI tests and verify `--help` exits successfully without network access**

### Task 4: Outbound voice worker and tools

**Files:**
- Create: `backend/src/telephony/outbound/agent.py`
- Create: `backend/tests/test_outbound_agent.py`

**Interfaces:**
- Consumes: `OutboundCallMetadata.from_json`, `opening_greeting`, `turn_language_instruction`, `fetch_district_weather`, `record_outbound_opt_out`
- Produces: `OutboundFarmAgent(Agent)` with `get_live_weather`, `stop_future_calls`, `detected_answering_machine`, and `end_call` tools
- Produces: `metadata_from_job(ctx: JobContext) -> OutboundCallMetadata`
- Produces: LiveKit worker registration `agent_name="outbound-agent"`

- [ ] **Step 1: Write failing deterministic tests for metadata parsing, timestamped weather output, safe weather failure, Hindi turn routing, and persisted opt-out behavior**

```python
@pytest.mark.asyncio
async def test_weather_failure_is_spoken_without_guessing() -> None:
    async def failing_fetcher(district: str):
        raise WeatherLookupError("timeout")
    agent = OutboundFarmAgent(fake_context, metadata, weather_fetcher=failing_fetcher)
    result = await agent.get_live_weather(None)
    assert "unavailable" in result.lower()
    assert "guess" in result.lower()
```

- [ ] **Step 2: Run `uv run pytest tests/test_outbound_agent.py -q` and verify the missing-module failure**

- [ ] **Step 3: Implement the Farm & Field prompt, per-turn native-script instruction, four tools, telephony-tuned audio, SIP dialing, Twirp failure shutdown, and fixed post-answer greeting**

```python
await ctx.api.sip.create_sip_participant(
    api.CreateSIPParticipantRequest(
        room_name=ctx.room.name,
        sip_trunk_id=outbound_trunk_id,
        sip_call_to=metadata.destination,
        participant_identity="phone-user",
        participant_name="Farmer",
        wait_until_answered=True,
    )
)
```

- [ ] **Step 4: Run outbound agent/config/dial tests and Ruff for all new files**

### Task 5: Linphone configuration and Day 6 runbook

**Files:**
- Create: `backend/src/telephony/outbound/linphone-trunk.example.json`
- Modify: `backend/.env.example`
- Modify: `README.md`
- Modify: `backend/README.md`

**Interfaces:**
- Documents: Linphone account and app setup, LiveKit trunk creation, worker start, consent-gated dial command, English/Hindi demos, failure demo, and current data source.

- [ ] **Step 1: Add a credential-free trunk example**

```json
{
  "name": "linphone-trunk",
  "address": "sip.linphone.org",
  "transport": "SIP_TRANSPORT_TLS",
  "numbers": ["sip:YOUR_LINPHONE_USERNAME"]
}
```

- [ ] **Step 2: Document `LIVEKIT_SIP_OUTBOUND_TRUNK_ID` and exact commands using `uv run python -m telephony.outbound.agent dev` and `uv run python -m telephony.outbound.dial ... --consent-confirmed`**

- [ ] **Step 3: Document graceful-failure demonstrations by temporarily using an invalid district and by stopping the outbound worker before dispatch**

- [ ] **Step 4: State that Linphone/LiveKit SIP are live external services and Open-Meteo is fetched at call time**

### Task 6: Complete verification without placing an unauthorized call

**Files:**
- Verify all files from Tasks 1 through 5.

- [ ] **Step 1: Run `uv run ruff format src tests` and `uv run ruff check src tests`**

- [ ] **Step 2: Run deterministic tests with `uv run pytest -q tests/test_db.py tests/test_language.py tests/test_weather.py tests/test_agent.py tests/test_outbound_call_config.py tests/test_outbound_dial.py tests/test_outbound_agent.py -k "not offers_assistance and not grounding and not refuses_harmful_request"`**

- [ ] **Step 3: Run `uv run python -m telephony.outbound.dial --help` and a no-consent dry run, verifying neither reaches LiveKit**

- [ ] **Step 4: Run `git diff --check` and inspect `git status --short` to confirm no secret or database file is added**

- [ ] **Step 5: Report the one remaining integration gate: create a personal Linphone account, configure the LiveKit trunk ID, and explicitly confirm the controlled destination before a real call**
