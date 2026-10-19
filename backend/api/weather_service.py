"""
Campus AeroAllergen Mapping (CAM) - Weather Service

Fetches real-time wind data from OpenWeatherMap API and converts
meteorological measurements into grid-aligned velocity components.
"""

import os
import time
import requests
from datetime import datetime
from typing import Dict, Optional, Tuple

# Gunn High School coordinates
CAMPUS_LAT = 37.4027
CAMPUS_LON = -122.1342

# One page load asks for the wind from several endpoints; the upstream APIs
# update roughly every 10-15 minutes, so reuse a live reading for that long.
WIND_CACHE_TTL_S = 600
_WIND_CACHE: Dict[Tuple[float, float], Tuple[float, Dict]] = {}


def fetch_current_wind(lat: Optional[float] = None, lon: Optional[float] = None,
                       api_key: Optional[str] = None) -> Dict:
    """
    Fetch current wind conditions from OpenWeatherMap for a location.
    Defaults to Gunn's coordinates. Returns dict with speed, direction, u, v
    components, and stability class.
    """
    if lat is None:
        lat = CAMPUS_LAT
    if lon is None:
        lon = CAMPUS_LON
    if api_key is None:
        api_key = os.environ.get("OPENWEATHER_API_KEY", "")

    key = (round(lat, 4), round(lon, 4))
    hit = _WIND_CACHE.get(key)
    if hit and time.time() - hit[0] < WIND_CACHE_TTL_S:
        return dict(hit[1])

    result = None
    if api_key:
        try:
            result = _fetch_openweathermap(lat, lon, api_key)
        except (requests.RequestException, KeyError, ValueError):
            pass
    if result is None:
        try:
            result = _fetch_open_meteo(lat, lon)
        except (requests.RequestException, KeyError, ValueError):
            return _mock_wind_data()
    _WIND_CACHE[key] = (time.time(), result)
    return dict(result)


def _fetch_openweathermap(lat: float, lon: float, api_key: str) -> Dict:
    url = "https://api.openweathermap.org/data/2.5/weather"
    params = {
        "lat": lat,
        "lon": lon,
        "appid": api_key,
        "units": "metric",
    }
    response = requests.get(url, params=params, timeout=10)
    response.raise_for_status()
    data = response.json()

    wind_speed = float(data["wind"]["speed"])
    wind_dir = float(data["wind"]["deg"])
    temp = float(data["main"]["temp"])
    clouds = data.get("clouds", {}).get("all", 50)
    u, v = _wind_components(wind_speed, wind_dir)
    return {
        "speed": wind_speed,
        "direction": wind_dir,
        "u": round(u, 3),
        "v": round(v, 3),
        "temperature": temp,
        "humidity": data["main"].get("humidity"),
        "stability_class": _estimate_stability_class(wind_speed, clouds, temp),
        "timestamp": datetime.utcnow().isoformat(),
        "source": "openweathermap",
    }


def _fetch_open_meteo(lat: float, lon: float) -> Dict:
    """Live current conditions; no API key required (CC BY 4.0 attribution)."""
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": lat,
        "longitude": lon,
        "current": "temperature_2m,relative_humidity_2m,cloud_cover,wind_speed_10m,wind_direction_10m",
        "wind_speed_unit": "ms",
        "timezone": "America/Los_Angeles",
    }
    response = requests.get(url, params=params, timeout=10)
    response.raise_for_status()
    cur = response.json()["current"]
    wind_speed = float(cur["wind_speed_10m"])
    wind_dir = float(cur["wind_direction_10m"])
    temp = float(cur["temperature_2m"])
    humidity = cur.get("relative_humidity_2m")
    clouds = int(cur.get("cloud_cover") or 50)
    u, v = _wind_components(wind_speed, wind_dir)
    return {
        "speed": round(wind_speed, 2),
        "direction": round(wind_dir, 1),
        "u": round(u, 3),
        "v": round(v, 3),
        "temperature": temp,
        "humidity": humidity,
        "stability_class": _estimate_stability_class(wind_speed, clouds, temp),
        "timestamp": cur.get("time") or datetime.utcnow().isoformat(),
        "source": "open-meteo",
    }


def build_wind_override(speed: float, direction: float,
                        stability_class: Optional[str] = None,
                        temperature: Optional[float] = None,
                        humidity: Optional[float] = None) -> Dict:
    """Build a wind_data dict from explicit values (test/simulation mode).

    Derives u/v components and, when stability_class is not given, estimates it
    from wind speed (assuming clear skies). temperature/humidity are carried for
    display only; they do not affect the dispersion computation.
    """
    u, v = _wind_components(speed, direction)
    if not stability_class:
        stability_class = _estimate_stability_class(speed, 20, temperature or 18.0)
    return {
        "speed": speed,
        "direction": direction,
        "u": round(u, 3),
        "v": round(v, 3),
        "temperature": temperature if temperature is not None else 18.0,
        "humidity": humidity if humidity is not None else 55,
        "stability_class": stability_class,
        "timestamp": datetime.utcnow().isoformat(),
        "source": "test-mode",
    }


def _wind_components(speed: float, direction_deg: float) -> Tuple[float, float]:
    """Convert wind speed/direction to u,v grid components."""
    import numpy as np
    theta = np.radians(270.0 - direction_deg)
    u = speed * np.cos(theta)
    v = speed * np.sin(theta)
    return float(u), float(v)


def _estimate_stability_class(
    wind_speed: float, cloud_cover: int, temperature: float
) -> str:
    """
    Estimate Pasquill-Gifford atmospheric stability class.
    Simplified estimation based on wind speed and cloud cover.
    """
    if wind_speed < 2.0:
        return "A" if cloud_cover < 30 else "B"
    elif wind_speed < 3.0:
        return "B" if cloud_cover < 50 else "C"
    elif wind_speed < 5.0:
        return "C" if cloud_cover < 50 else "D"
    elif wind_speed < 6.0:
        return "D"
    else:
        return "D" if cloud_cover < 70 else "E"


def _mock_wind_data() -> Dict:
    """Return realistic mock wind data for development/testing."""
    return {
        "speed": 3.5,
        "direction": 240.0,
        "u": -3.03,
        "v": -1.75,
        "temperature": 18.5,
        "humidity": 55,
        "stability_class": "D",
        "timestamp": datetime.utcnow().isoformat(),
        "source": "mock",
    }
