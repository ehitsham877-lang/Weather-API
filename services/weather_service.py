from __future__ import annotations

import httpx

from config import Settings


class OpenWeatherError(Exception):
    def __init__(self, http_status: int, message: str) -> None:
        super().__init__(message)
        self.http_status = http_status
        self.message = message


class OpenWeatherClient:
    def __init__(self, http_client: httpx.AsyncClient, settings: Settings) -> None:
        self._http = http_client
        self._settings = settings

    async def current_by_city(self, city: str) -> dict | None:
        return await self._get("/weather", params={"q": city})

    async def current_by_coords(self, lat: float, lon: float) -> dict | None:
        return await self._get("/weather", params={"lat": lat, "lon": lon})

    async def forecast_by_city(self, city: str) -> dict | None:
        return await self._get("/forecast", params={"q": city})

    async def _get(self, path: str, params: dict) -> dict | None:
        request_params = {
            **params,
            "appid": self._settings.openweather_api_key,
            "units": "metric",
        }

        try:
            response = await self._http.get(path, params=request_params)
        except httpx.TimeoutException as exc:
            raise OpenWeatherError(
                http_status=504,
                message="Weather provider timed out. Try again in a moment.",
            ) from exc
        except httpx.HTTPError as exc:
            raise OpenWeatherError(
                http_status=503,
                message="Weather provider is unreachable (network error).",
            ) from exc

        if response.status_code == 404:
            return None

        if response.status_code == 401:
            raise OpenWeatherError(
                http_status=500,
                message="Server misconfigured: invalid OPENWEATHER_API_KEY.",
            )

        if response.status_code != 200:
            raise OpenWeatherError(
                http_status=502,
                message=f"Weather provider error (status {response.status_code}).",
            )

        try:
            return response.json()
        except ValueError as exc:
            raise OpenWeatherError(
                http_status=502,
                message="Weather provider returned an invalid response.",
            ) from exc
