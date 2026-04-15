from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field


class WeatherNowResponse(BaseModel):
    city: str
    country: str
    temperature_c: float = Field(..., description="Current temperature in Celsius")
    feels_like_c: float = Field(..., description="Feels-like temperature in Celsius")
    humidity_percent: int = Field(..., ge=0, le=100)
    wind_speed_mps: float = Field(..., ge=0)
    condition: str
    description: str


class WeatherByCoordsResponse(WeatherNowResponse):
    latitude: float
    longitude: float


class WeatherSummaryResponse(WeatherNowResponse):
    pressure_hpa: int = Field(..., ge=0)
    visibility_m: Optional[int] = Field(None, ge=0)


class ForecastPoint(BaseModel):
    time: str = Field(..., description="Forecast timestamp (provider format)")
    temperature_c: float
    feels_like_c: float
    humidity_percent: int = Field(..., ge=0, le=100)
    condition: str
    description: str


class ForecastResponse(BaseModel):
    city: str
    forecast: List[ForecastPoint]


class HourlyForecastResponse(BaseModel):
    city: str
    hourly_forecast: List[ForecastPoint]


class CityCompareResult(BaseModel):
    city: str
    country: Optional[str] = None
    temperature_c: Optional[float] = None
    humidity_percent: Optional[int] = None
    condition: Optional[str] = None
    description: Optional[str] = None
    error: Optional[str] = None


class CityCompareResponse(BaseModel):
    results: List[CityCompareResult]
