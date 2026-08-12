import asyncio
from dataclasses import dataclass
from typing import Any

import aiohttp

GEOCODING_URL = "https://geocoding-api.open-meteo.com/v1/search"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
REQUEST_TIMEOUT_SECONDS = 8.0
GEOCODING_ALIASES = {
    "bangalore": "Bengaluru",
}

WMO_WEATHER_DESCRIPTIONS = {
    0: "clear sky",
    1: "mainly clear",
    2: "partly cloudy",
    3: "overcast",
    45: "fog",
    48: "freezing fog",
    51: "light drizzle",
    53: "drizzle",
    55: "heavy drizzle",
    56: "light freezing drizzle",
    57: "heavy freezing drizzle",
    61: "light rain",
    63: "rain",
    65: "heavy rain",
    66: "light freezing rain",
    67: "heavy freezing rain",
    71: "light snow",
    73: "snow",
    75: "heavy snow",
    77: "snow grains",
    80: "light rain showers",
    81: "rain showers",
    82: "heavy rain showers",
    85: "light snow showers",
    86: "heavy snow showers",
    95: "thunderstorm",
    96: "thunderstorm with light hail",
    99: "thunderstorm with heavy hail",
}


class WeatherLookupError(Exception):
    """Raised when live district weather cannot be retrieved safely."""


@dataclass(frozen=True, slots=True)
class WeatherReport:
    location_name: str
    observed_at: str
    forecast_date: str
    temperature_c: float
    weather_description: str
    wind_speed_kmh: float
    minimum_temperature_c: float
    maximum_temperature_c: float
    precipitation_probability_percent: int

    def to_spoken_text(self) -> str:
        return (
            f"Open-Meteo live weather for {self.location_name}. Open-Meteo data "
            f"timestamp: {self.observed_at} local time. Temperature is "
            f"{self.temperature_c}°C with {self.weather_description} and wind at "
            f"{self.wind_speed_kmh} km/h. "
            f"For {self.forecast_date}, the forecast range is "
            f"{self.minimum_temperature_c} to {self.maximum_temperature_c}°C with a "
            f"{self.precipitation_probability_percent}% maximum chance of rain."
        )


async def _get_json(session: Any, url: str, params: dict[str, Any]) -> dict:
    try:
        async with session.get(
            url,
            params=params,
            timeout=REQUEST_TIMEOUT_SECONDS,
        ) as response:
            response.raise_for_status()
            data = await response.json()
    except asyncio.TimeoutError as error:
        raise WeatherLookupError(
            "The live weather service did not respond in time."
        ) from error
    except aiohttp.ClientError as error:
        raise WeatherLookupError(
            "The live weather service is unavailable right now."
        ) from error

    if not isinstance(data, dict):
        raise WeatherLookupError("The live weather service returned invalid data.")
    return data


def _parse_report(location: dict, forecast: dict) -> WeatherReport:
    try:
        current = forecast["current"]
        daily = forecast["daily"]
        current_code = int(current["weather_code"])
        admin1 = location.get("admin1")
        location_name = location["name"]
        if admin1 and admin1 != location_name:
            location_name = f"{location_name}, {admin1}"

        return WeatherReport(
            location_name=location_name,
            observed_at=str(current["time"]),
            forecast_date=str(daily["time"][0]),
            temperature_c=float(current["temperature_2m"]),
            weather_description=WMO_WEATHER_DESCRIPTIONS.get(
                current_code, "unknown conditions"
            ),
            wind_speed_kmh=float(current["wind_speed_10m"]),
            minimum_temperature_c=float(daily["temperature_2m_min"][0]),
            maximum_temperature_c=float(daily["temperature_2m_max"][0]),
            precipitation_probability_percent=int(
                daily["precipitation_probability_max"][0]
            ),
        )
    except (KeyError, IndexError, TypeError, ValueError) as error:
        raise WeatherLookupError(
            "The live weather service returned incomplete data."
        ) from error


async def _fetch_district_weather(district: str, session: Any) -> WeatherReport:
    geocoding = await _get_json(
        session,
        GEOCODING_URL,
        {
            "name": district,
            "count": 1,
            "language": "en",
            "format": "json",
            "countryCode": "IN",
        },
    )
    results = geocoding.get("results")
    if not isinstance(results, list) or not results:
        raise WeatherLookupError("I could not find that district in India.")

    location = results[0]
    try:
        latitude = location["latitude"]
        longitude = location["longitude"]
    except (KeyError, TypeError) as error:
        raise WeatherLookupError(
            "The location service returned incomplete data."
        ) from error

    forecast = await _get_json(
        session,
        FORECAST_URL,
        {
            "latitude": latitude,
            "longitude": longitude,
            "current": "temperature_2m,weather_code,wind_speed_10m",
            "daily": (
                "weather_code,temperature_2m_max,temperature_2m_min,"
                "precipitation_probability_max"
            ),
            "forecast_days": 1,
            "timezone": "auto",
        },
    )
    return _parse_report(location, forecast)


async def fetch_district_weather(
    district: str,
    session: Any | None = None,
) -> WeatherReport:
    """Fetch current conditions and today's forecast for an Indian district."""
    normalized_district = district.strip()
    if len(normalized_district) < 2:
        raise WeatherLookupError("Please provide a valid district name.")

    normalized_district = GEOCODING_ALIASES.get(
        normalized_district.casefold(), normalized_district
    )

    if session is not None:
        return await _fetch_district_weather(normalized_district, session)

    async with aiohttp.ClientSession() as owned_session:
        return await _fetch_district_weather(normalized_district, owned_session)
