"""
Campus AeroAllergen Mapping (CAM) - Pollen API Service

Integrates with Google Maps Platform Pollen API for regional
background allergen forecasts (Universal Pollen Index).
"""

import os
import requests
from datetime import date, datetime
from typing import Dict, List, Optional


CAMPUS_LAT = 37.4027
CAMPUS_LON = -122.1342


def fetch_pollen_forecast(api_key: Optional[str] = None, days: int = 5,
                          lat: Optional[float] = None, lon: Optional[float] = None) -> List[Dict]:
    """
    Fetch regional pollen forecast from Google Pollen API.
    Returns list of daily forecasts with UPI values for TREE, GRASS, WEED.
    """
    if api_key is None:
        api_key = os.environ.get("GOOGLE_POLLEN_API_KEY", "")
    if lat is None:
        lat = CAMPUS_LAT
    if lon is None:
        lon = CAMPUS_LON

    if not api_key:
        return _mock_pollen_forecast(days)

    url = "https://pollen.googleapis.com/v1/forecast:lookup"
    params = {
        "key": api_key,
        "location.longitude": lon,
        "location.latitude": lat,
        "days": days,
    }

    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()

        forecasts = []
        for day_info in data.get("dailyInfo", []):
            forecast = {
                "date": day_info.get("date", {}).get("year", ""),
                "tree_upi": 0,
                "grass_upi": 0,
                "weed_upi": 0,
                "dominant_species": None,
            }

            for pollen_type in day_info.get("pollenTypeInfo", []):
                code = pollen_type.get("code", "")
                index_info = pollen_type.get("indexInfo", {})
                upi = index_info.get("value", 0)

                if code == "TREE":
                    forecast["tree_upi"] = upi
                elif code == "GRASS":
                    forecast["grass_upi"] = upi
                elif code == "WEED":
                    forecast["weed_upi"] = upi

            plant_info = day_info.get("plantInfo", [])
            if plant_info:
                top_plant = max(
                    plant_info,
                    key=lambda p: p.get("indexInfo", {}).get("value", 0),
                )
                forecast["dominant_species"] = top_plant.get("displayName", "")

            forecasts.append(forecast)

        return forecasts
    except (requests.RequestException, KeyError):
        return _mock_pollen_forecast(days)


def get_current_upi(lat: Optional[float] = None, lon: Optional[float] = None) -> Dict:
    """Get today's Universal Pollen Index values."""
    forecasts = fetch_pollen_forecast(days=1, lat=lat, lon=lon)
    if forecasts:
        return forecasts[0]
    return {"tree_upi": 0, "grass_upi": 0, "weed_upi": 0, "dominant_species": None}


def upi_to_clinical_level(upi: int) -> Dict:
    """Map UPI value to clinical severity and recommendations."""
    levels = {
        0: {
            "level": "None",
            "severity": "Negligible",
            "symptoms": "No immune response expected.",
            "recommendation": "Normal outdoor activities permitted.",
            "color": "#22c55e",
        },
        1: {
            "level": "Low",
            "severity": "Very Low",
            "symptoms": "Negligible immune response; safe for sensitive demographics.",
            "recommendation": "Normal outdoor activities. No preventative measures required.",
            "color": "#86efac",
        },
        2: {
            "level": "Moderate",
            "severity": "Moderate",
            "symptoms": "Mild histaminic reactions: itchy eyes, sneezing.",
            "recommendation": "Consider non-drowsy antihistamines. Avoid lingering near tree markers.",
            "color": "#facc15",
        },
        3: {
            "level": "High",
            "severity": "High",
            "symptoms": "Moderate reactions: congestion, upper airway irritation.",
            "recommendation": "Take antihistamines before school. Limit outdoor break time near high-risk zones.",
            "color": "#f97316",
        },
        4: {
            "level": "Very High",
            "severity": "Very High",
            "symptoms": "Severe respiratory triggers: acute rhinitis, asthma flare-ups.",
            "recommendation": "Mandatory window closures. Move PE indoors. Wear N95 on transit corridors.",
            "color": "#ef4444",
        },
        5: {
            "level": "Extreme",
            "severity": "Extreme",
            "symptoms": "Severe asthma attacks, heavy ocular inflammation, anaphylaxis risk.",
            "recommendation": "Consider remote attendance. All outdoor activities suspended.",
            "color": "#991b1b",
        },
    }
    return levels.get(min(upi, 5), levels[0])


def _mock_pollen_forecast(days: int) -> List[Dict]:
    """Generate realistic mock pollen forecast for development."""
    today = date.today()
    doy = today.timetuple().tm_yday
    forecasts = []

    for i in range(days):
        day = doy + i
        tree_upi = 4 if 60 <= day <= 150 else (2 if 50 <= day <= 160 else 0)
        grass_upi = 4 if 121 <= day <= 181 else (2 if 110 <= day <= 190 else 0)
        weed_upi = 2 if 150 <= day <= 270 else 0

        forecasts.append({
            "date": f"{today.year}-{today.month:02d}-{today.day + i:02d}",
            "tree_upi": tree_upi,
            "grass_upi": grass_upi,
            "weed_upi": weed_upi,
            "dominant_species": "Coast Live Oak" if tree_upi >= 3 else "Grass",
        })

    return forecasts
