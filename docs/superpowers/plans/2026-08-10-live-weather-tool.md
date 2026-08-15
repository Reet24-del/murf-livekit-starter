# Live District Weather Tool Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the broken weather function with a tested, live Open-Meteo district forecast tool that reuses Day 4 memory and fails safely.

**Architecture:** A focused `weather.py` module owns Open-Meteo requests, validation, and report formatting. `agent.py` resolves the caller's district, exposes the LiveKit tool, and turns service errors into useful spoken outcomes. Tests fake only the external HTTP session and exercise the real parsing and tool-location logic.

**Tech Stack:** Python 3.10+, aiohttp, LiveKit Agents, Open-Meteo Geocoding and Forecast APIs, pytest, Ruff.

## Global Constraints

- Use live Open-Meteo data and identify it in the README.
- Return the observation time and forecast date with every successful result.
- Never invent weather values when the source fails.
- Prefer an explicit district, then a saved Day 4 district, then participant location metadata.
- Keep spoken results concise and natural rather than JSON-shaped.

---

### Task 1: Live Open-Meteo service

**Files:**
- Create: `backend/src/weather.py`
- Create: `backend/tests/test_weather.py`

**Interfaces:**
- Produces: `WeatherLookupError(Exception)`
- Produces: `WeatherReport(location_name, observed_at, forecast_date, temperature_c, weather_description, wind_speed_kmh, minimum_temperature_c, maximum_temperature_c, precipitation_probability_percent)`
- Produces: `async fetch_district_weather(district: str, session: aiohttp.ClientSession | None = None) -> WeatherReport`

- [ ] **Step 1: Write failing tests for success, unknown district, and timeout**

```python
report = await fetch_district_weather("Wardha", session=fake_session)
assert report.location_name == "Wardha, Maharashtra"
assert report.observed_at == "2026-08-10T14:15"
assert report.precipitation_probability_percent == 70
```

- [ ] **Step 2: Run the weather tests and verify the missing service contract failure**

Run: `uv run pytest tests/test_weather.py -v`
Expected: FAIL because `fetch_district_weather` has not implemented the requested report values and failures.

- [ ] **Step 3: Implement URL parameter requests, response validation, and report formatting**

```python
async def fetch_district_weather(district, session=None):
    geocoding = await _get_json(session, GEOCODING_URL, params={"name": district, "count": 1, "language": "en", "format": "json", "countryCode": "IN"})
    location = geocoding["results"][0]
    forecast = await _get_json(session, FORECAST_URL, params=_forecast_params(location))
    return _parse_report(location, forecast)
```

- [ ] **Step 4: Run the weather tests and verify they pass**

Run: `uv run pytest tests/test_weather.py -v`
Expected: all weather tests pass.

### Task 2: LiveKit tool and Day 4 district reuse

**Files:**
- Modify: `backend/src/agent.py`
- Modify: `backend/tests/test_agent.py`

**Interfaces:**
- Consumes: `fetch_district_weather(district) -> WeatherReport`
- Produces: `Assistant.get_district_weather(context: RunContext, district: str | None = None) -> str`

- [ ] **Step 1: Write failing tests for saved-district selection and graceful failure text**

```python
assert assistant._weather_location() == "Wardha"
assert "live weather data is unavailable" in await assistant.get_district_weather(None, "Wardha")
```

- [ ] **Step 2: Run the targeted agent tests and verify failure for the missing tool**

Run: `uv run pytest tests/test_agent.py -k weather -v`
Expected: FAIL because `get_district_weather` is missing.

- [ ] **Step 3: Implement location precedence, the precise tool description, and spoken result formatting**

```python
@function_tool
async def get_district_weather(self, context, district=None):
    """Call for current weather, rain chance, temperature, wind, or today's farm planning."""
    location = district or self._weather_location()
    if not location:
        return "Please tell me your district so I can check live weather."
    return (await fetch_district_weather(location)).to_spoken_text()
```

- [ ] **Step 4: Run all deterministic backend tests**

Run: `uv run pytest tests/test_db.py tests/test_weather.py tests/test_agent.py -k "not offers_assistance and not grounding and not refuses_harmful_request" -v`
Expected: all deterministic tests pass.

### Task 3: Source documentation and final verification

**Files:**
- Modify: `README.md`
- Modify: `backend/README.md`

- [ ] **Step 1: Document the live data source, fields, timestamps, and failure behavior**

Add a Day 5 section naming Open-Meteo Geocoding and Forecast APIs, noting that results are live external data rather than a local dataset, and giving one demo question.

- [ ] **Step 2: Format and lint**

Run: `uv run ruff format src tests && uv run ruff check src tests`
Expected: no lint errors.

- [ ] **Step 3: Run deterministic tests and inspect the diff**

Run: `uv run pytest tests/test_db.py tests/test_weather.py tests/test_agent.py -k "not offers_assistance and not grounding and not refuses_harmful_request" -v`
Expected: all deterministic tests pass.

Run: `git diff --check`
Expected: no whitespace errors.
