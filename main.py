from __future__ import annotations

from contextlib import asynccontextmanager

import httpx
from fastapi import Depends, FastAPI, HTTPException, Query, Request, status

from config import Settings, get_settings
from schemas import (
    CityCompareResponse,
    CityCompareResult,
    ForecastPoint,
    ForecastResponse,
    HourlyForecastResponse,
    WeatherByCoordsResponse,
    WeatherNowResponse,
    WeatherSummaryResponse,
)
from services.weather_service import OpenWeatherClient, OpenWeatherError


def _model_to_dict(model) -> dict:
    return model.model_dump() if hasattr(model, "model_dump") else model.dict()


def _map_weather_now(payload: dict) -> WeatherNowResponse:
    return WeatherNowResponse(
        city=payload["name"],
        country=payload["sys"]["country"],
        temperature_c=payload["main"]["temp"],
        feels_like_c=payload["main"]["feels_like"],
        humidity_percent=payload["main"]["humidity"],
        wind_speed_mps=payload["wind"]["speed"],
        condition=payload["weather"][0]["main"],
        description=payload["weather"][0]["description"],
    )


def _map_weather_summary(payload: dict) -> WeatherSummaryResponse:
    now = _map_weather_now(payload)
    visibility = payload.get("visibility")
    return WeatherSummaryResponse(
        **_model_to_dict(now),
        pressure_hpa=payload["main"]["pressure"],
        visibility_m=visibility if isinstance(visibility, int) else None,
    )


def _map_forecast_points(payload: dict, limit: int) -> list[ForecastPoint]:
    points: list[ForecastPoint] = []
    for item in payload.get("list", [])[:limit]:
        points.append(
            ForecastPoint(
                time=item.get("dt_txt", ""),
                temperature_c=item["main"]["temp"],
                feels_like_c=item["main"]["feels_like"],
                humidity_percent=item["main"]["humidity"],
                condition=item["weather"][0]["main"],
                description=item["weather"][0]["description"],
            )
        )
    return points


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    app.state.settings = settings
    app.state.http_client = httpx.AsyncClient(
        base_url=settings.openweather_base_url,
        timeout=httpx.Timeout(settings.http_timeout_seconds),
    )
    try:
        yield
    finally:
        await app.state.http_client.aclose()


app = FastAPI(
    title="Weather API",
    description="Weather API with current conditions and forecasts (OpenWeather provider).",
    version="1.1.0",
    lifespan=lifespan,
)


def get_openweather_client(
    request: Request,
) -> OpenWeatherClient:
    settings: Settings = request.app.state.settings
    return OpenWeatherClient(request.app.state.http_client, settings)


@app.get("/", tags=["meta"])
def home():
    return {"status": "ok", "service": "weather-api"}


@app.get("/weather", response_model=WeatherNowResponse, tags=["weather"])
async def get_weather(
    city: str = Query(..., min_length=1, max_length=80, description="City name"),
    client: OpenWeatherClient = Depends(get_openweather_client),
):
    try:
        payload = await client.current_by_city(city)
    except OpenWeatherError as exc:
        raise HTTPException(status_code=exc.http_status, detail=exc.message) from exc
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"City '{city}' not found.",
        )
    return _map_weather_now(payload)


@app.get("/weather/coords", response_model=WeatherByCoordsResponse, tags=["weather"])
async def weather_by_coords(
    lat: float = Query(..., ge=-90, le=90),
    lon: float = Query(..., ge=-180, le=180),
    client: OpenWeatherClient = Depends(get_openweather_client),
):
    try:
        payload = await client.current_by_coords(lat=lat, lon=lon)
    except OpenWeatherError as exc:
        raise HTTPException(status_code=exc.http_status, detail=exc.message) from exc
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Location not found for given coordinates.",
        )
    now = _map_weather_now(payload)
    return WeatherByCoordsResponse(latitude=lat, longitude=lon, **_model_to_dict(now))


@app.get("/weather/summary", response_model=WeatherSummaryResponse, tags=["weather"])
async def weather_summary(
    city: str = Query(..., min_length=1, max_length=80),
    client: OpenWeatherClient = Depends(get_openweather_client),
):
    try:
        payload = await client.current_by_city(city)
    except OpenWeatherError as exc:
        raise HTTPException(status_code=exc.http_status, detail=exc.message) from exc
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"City '{city}' not found.",
        )
    return _map_weather_summary(payload)


@app.get("/forecast", response_model=ForecastResponse, tags=["forecast"])
async def get_forecast(
    city: str = Query(..., min_length=1, max_length=80),
    client: OpenWeatherClient = Depends(get_openweather_client),
):
    try:
        payload = await client.forecast_by_city(city)
    except OpenWeatherError as exc:
        raise HTTPException(status_code=exc.http_status, detail=exc.message) from exc
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"City '{city}' not found.",
        )
    return ForecastResponse(city=city, forecast=_map_forecast_points(payload, limit=5))


@app.get("/forecast/hourly", response_model=HourlyForecastResponse, tags=["forecast"])
async def hourly_forecast(
    city: str = Query(..., min_length=1, max_length=80),
    client: OpenWeatherClient = Depends(get_openweather_client),
):
    try:
        payload = await client.forecast_by_city(city)
    except OpenWeatherError as exc:
        raise HTTPException(status_code=exc.http_status, detail=exc.message) from exc
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"City '{city}' not found.",
        )
    return HourlyForecastResponse(
        city=city, hourly_forecast=_map_forecast_points(payload, limit=10)
    )


@app.get("/weather/compare", response_model=CityCompareResponse, tags=["weather"])
async def compare_cities(
    cities: str = Query(
        ...,
        min_length=1,
        description="Comma separated cities, e.g. London,Karachi,Tokyo",
    ),
    client: OpenWeatherClient = Depends(get_openweather_client),
):
    city_list = [c.strip() for c in cities.split(",") if c.strip()]
    if not city_list:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Provide at least one city.",
        )

    if len(city_list) > 5:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Maximum 5 cities allowed per request.",
        )

    results: list[CityCompareResult] = []
    for city in city_list:
        try:
            payload = await client.current_by_city(city)
        except OpenWeatherError as exc:
            raise HTTPException(status_code=exc.http_status, detail=exc.message) from exc
        if not payload:
            results.append(CityCompareResult(city=city, error="City not found"))
            continue

        now = _map_weather_now(payload)
        results.append(
            CityCompareResult(
                city=now.city,
                country=now.country,
                temperature_c=now.temperature_c,
                humidity_percent=now.humidity_percent,
                condition=now.condition,
                description=now.description,
            )
        )

    return CityCompareResponse(results=results)
