# Live District Weather Tool Design

## Goal

Give Kisan Sahayak a reliable internet-backed weather lookup that speaks useful, time-stamped farm weather and fails without silence or invented data.

## Source and scope

The tool uses Open-Meteo's public Geocoding API to resolve an Indian district or city and its Forecast API to retrieve current temperature, current weather code, current wind speed, today's temperature range, and today's maximum precipitation probability. Requests use `timezone=auto` so returned ISO-8601 times and daily dates match the resolved location.

The tool is for current conditions and today's forecast only. It does not claim long-range accuracy, invent typical conditions, or fetch market prices. The README identifies Open-Meteo as a live external source and states that availability depends on internet access.

## Components and data flow

`backend/src/weather.py` owns the Open-Meteo HTTP contract, response validation, WMO weather-code descriptions, and a concise `WeatherReport` value. `fetch_district_weather(district)` resolves a location in India, requests one forecast day, and returns a report containing the source timestamp.

`Assistant.get_district_weather` is the LiveKit function tool. The model supplies a district when the caller names one. Otherwise the tool reuses the Day 4 saved district for the current caller; participant location metadata is the final fallback. If no location is available, the result asks the caller for their district.

The tool description tells the model to call it for current weather, rain likelihood, temperature, wind, and same-day farm-planning questions. The system prompt tells the model to speak the result naturally and never add weather facts that are absent from the tool output.

## Failure behavior

HTTP failures, timeouts, unknown locations, and incomplete API responses produce a controlled `WeatherLookupError`. The function tool converts that to a short, useful result: live weather is unavailable, no weather value should be guessed, and the caller may try again or contact a local weather/agriculture service. Exceptions are logged for operators but are not read aloud.

## Testing

Unit tests replace only the external HTTP boundary with a small fake session. They prove the exact geocoding and forecast parameters, timestamped successful formatting, unknown-location behavior, and timeout behavior. Agent tests prove saved-district reuse and the absence of the old fabricated 28°C fallback. Ruff and the local backend test subset must pass.
