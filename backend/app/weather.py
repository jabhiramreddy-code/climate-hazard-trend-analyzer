import asyncio
import json
from datetime import date
import httpx
from fastapi import HTTPException
from app.analysis import normalize_weather

ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"
MAX_RESPONSE_BYTES = 16 * 1024 * 1024


class WeatherClient:
    def __init__(self, client):
        self.client = client

    async def fetch(self, latitude, longitude, start, end):
        params = {"latitude": latitude, "longitude": longitude,
                  "start_date": start.isoformat(), "end_date": end.isoformat(),
                  "daily": "temperature_2m_max", "temperature_unit": "celsius",
                  "timezone": "auto", "models": "era5"}
        try:
            async with self.client.stream("GET", ARCHIVE_URL, params=params) as response:
                if response.status_code == 429:
                    raise HTTPException(503, "Weather provider is rate-limited. Try again later.", headers={"Retry-After": "60"})
                if response.status_code != 200:
                    raise HTTPException(502, "Weather provider could not complete the request. Try again later.")
                body = bytearray()
                async for chunk in response.aiter_bytes():
                    body.extend(chunk)
                    if len(body) > MAX_RESPONSE_BYTES:
                        raise HTTPException(502, "Weather provider response exceeded the safe size limit.")
            payload = json.loads(body)
            normalized = normalize_weather(payload, start, end)
            normalized["source"] = {"provider": "Open-Meteo", "model": "ERA5", "timezone": payload.get("timezone"),
                                    "grid_latitude": payload.get("latitude"), "grid_longitude": payload.get("longitude"),
                                    "url": "https://open-meteo.com/en/docs/historical-weather-api"}
            return normalized
        except httpx.TimeoutException:
            raise HTTPException(504, "Weather provider timed out. Try again or choose a shorter interval.") from None
        except httpx.RequestError:
            raise HTTPException(502, "Weather provider is unreachable. Try again later.") from None
        except (ValueError, TypeError):
            raise HTTPException(502, "Weather provider returned unusable daily-temperature data.") from None
