import asyncio

import pytest

from weather import WeatherLookupError, fetch_district_weather


class FakeResponse:
    def __init__(self, payload: dict) -> None:
        self.payload = payload

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, traceback) -> None:
        return None

    def raise_for_status(self) -> None:
        return None

    async def json(self) -> dict:
        return self.payload


class SuccessfulWeatherSession:
    def __init__(self, expected_name: str = "Wardha") -> None:
        self.request_count = 0
        self.expected_name = expected_name

    def get(self, url: str, *, params: dict, timeout: float):
        self.request_count += 1
        assert timeout == 8.0

        if self.request_count == 1:
            assert url == "https://geocoding-api.open-meteo.com/v1/search"
            assert params == {
                "name": self.expected_name,
                "count": 1,
                "language": "en",
                "format": "json",
                "countryCode": "IN",
            }
            return FakeResponse(
                {
                    "results": [
                        {
                            "id": 1252942,
                            "name": "Wardha",
                            "latitude": 20.7453,
                            "longitude": 78.6022,
                            "timezone": "Asia/Kolkata",
                            "country_code": "IN",
                            "country": "India",
                            "admin1": "Maharashtra",
                        }
                    ],
                    "generationtime_ms": 0.3,
                }
            )

        assert url == "https://api.open-meteo.com/v1/forecast"
        assert params == {
            "latitude": 20.7453,
            "longitude": 78.6022,
            "current": "temperature_2m,weather_code,wind_speed_10m",
            "daily": (
                "weather_code,temperature_2m_max,temperature_2m_min,"
                "precipitation_probability_max"
            ),
            "forecast_days": 1,
            "timezone": "auto",
        }
        return FakeResponse(
            {
                "latitude": 20.75,
                "longitude": 78.625,
                "generationtime_ms": 0.4,
                "utc_offset_seconds": 19800,
                "timezone": "Asia/Kolkata",
                "timezone_abbreviation": "IST",
                "current_units": {
                    "time": "iso8601",
                    "interval": "seconds",
                    "temperature_2m": "°C",
                    "weather_code": "wmo code",
                    "wind_speed_10m": "km/h",
                },
                "current": {
                    "time": "2026-08-10T14:15",
                    "interval": 900,
                    "temperature_2m": 28.4,
                    "weather_code": 61,
                    "wind_speed_10m": 13.2,
                },
                "daily_units": {
                    "time": "iso8601",
                    "weather_code": "wmo code",
                    "temperature_2m_max": "°C",
                    "temperature_2m_min": "°C",
                    "precipitation_probability_max": "%",
                },
                "daily": {
                    "time": ["2026-08-10"],
                    "weather_code": [63],
                    "temperature_2m_max": [31.1],
                    "temperature_2m_min": [24.2],
                    "precipitation_probability_max": [70],
                },
            }
        )


class UnknownLocationSession:
    def get(self, url: str, *, params: dict, timeout: float):
        return FakeResponse({"generationtime_ms": 0.2})


class BengaluruAliasSession(SuccessfulWeatherSession):
    def __init__(self) -> None:
        super().__init__(expected_name="Bengaluru")


class TimeoutSession:
    def get(self, url: str, *, params: dict, timeout: float):
        raise asyncio.TimeoutError


@pytest.mark.asyncio
async def test_fetch_district_weather_returns_timestamped_live_report() -> None:
    report = await fetch_district_weather("Wardha", session=SuccessfulWeatherSession())

    assert report.location_name == "Wardha, Maharashtra"
    assert report.observed_at == "2026-08-10T14:15"
    assert report.forecast_date == "2026-08-10"
    assert report.temperature_c == 28.4
    assert report.weather_description == "light rain"
    assert report.wind_speed_kmh == 13.2
    assert report.minimum_temperature_c == 24.2
    assert report.maximum_temperature_c == 31.1
    assert report.precipitation_probability_percent == 70
    assert report.to_spoken_text() == (
        "Open-Meteo live weather for Wardha, Maharashtra. Open-Meteo data "
        "timestamp: 2026-08-10T14:15 local time. Temperature is 28.4°C with "
        "light rain and wind at "
        "13.2 km/h. For 2026-08-10, the forecast range is 24.2 to 31.1°C "
        "with a 70% maximum chance of rain."
    )


@pytest.mark.asyncio
async def test_fetch_district_weather_normalizes_bangalore_to_bengaluru() -> None:
    report = await fetch_district_weather(
        "Bangalore", session=BengaluruAliasSession()
    )

    assert report.location_name == "Wardha, Maharashtra"


@pytest.mark.asyncio
async def test_fetch_district_weather_rejects_unknown_district() -> None:
    with pytest.raises(
        WeatherLookupError,
        match=r"I could not find that district in India\.",
    ):
        await fetch_district_weather("Not a district", session=UnknownLocationSession())


@pytest.mark.asyncio
async def test_fetch_district_weather_turns_timeout_into_lookup_error() -> None:
    with pytest.raises(
        WeatherLookupError,
        match=r"The live weather service did not respond in time\.",
    ):
        await fetch_district_weather("Wardha", session=TimeoutSession())
