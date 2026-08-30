"""
Campus AeroAllergen Mapping (CAM) - Weather Service

Fetches real-time wind data from OpenWeatherMap API and converts
meteorological measurements into grid-aligned velocity components.
"""

import os
import requests
from datetime import datetime
from typing import Dict, Optional, Tuple

# Gunn High School coordinates
CAMPUS_LAT = 37.4027
CAMPUS_LON = -122.1342


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

    if not api_key:
        return _mock_wind_data()

    url = "https://api.openweathermap.org/data/2.5/weather"
    params = {
        "lat": lat,
        "lon": lon,
        "appid": api_key,
        "units": "metric",
    }

    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()

        wind_speed = data["wind"]["speed"]
        wind_dir = data["wind"]["deg"]
        temp = data["main"]["temp"]
        clouds = data.get("clouds", {}).get("all", 50)

        u, v = _wind_components(wind_speed, wind_dir)
        stability = _estimate_stability_class(wind_speed, clouds, temp)

        return {
            "speed": wind_speed,
            "direction": wind_dir,
            "u": round(u, 3),
            "v": round(v, 3),
            "temperature": temp,
            "humidity": data["main"].get("humidity"),
            "stability_class": stability,
            "timestamp": datetime.utcnow().isoformat(),
            "source": "openweathermap",
        }
    except (requests.RequestException, KeyError):
        return _mock_wind_data()


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
