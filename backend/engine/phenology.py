"""
Campus AeroAllergen Mapping (CAM) - Phenological Engine

Implements temporal gate functions for species-specific pollen emission modeling.
Tracks blooming periods and calculates time-variant emission rates.
"""

import numpy as np
from datetime import date, datetime
from typing import Dict, List, Optional, Tuple


# Palo Alto / Gunn High School campus botanical profiles
# Each entry: (common_name, scientific_name, start_day, end_day, peak_day, sigma_t, potency_weight, base_emission)
BOTANICAL_CATALOG = {
    "palm": {
        "common_name": "Canary Island Date Palm",
        "scientific_name": "Phoenix canariensis",
        "family": "Arecaceae",
        "start_day": 74,   # March 15
        "end_day": 135,    # May 15
        "peak_day": 105,   # April 15
        "sigma_t": 20.0,
        "potency_weight": 3.0,
        "base_emission": 350.0,
        "symptoms": "Moderate allergic rhinitis, sneezing, itchy eyes",
    },
    "coast_live_oak": {
        "common_name": "Coast Live Oak",
        "scientific_name": "Quercus agrifolia",
        "family": "Fagaceae",
        "start_day": 60,   # March 1
        "end_day": 120,    # April 30
        "peak_day": 91,    # April 1
        "sigma_t": 21.0,
        "potency_weight": 4.0,
        "base_emission": 500.0,
        "symptoms": "Severe allergic rhinitis, explosive sneezing, asthma triggers",
    },
    "valley_oak": {
        "common_name": "Valley Oak",
        "scientific_name": "Quercus lobata",
        "family": "Fagaceae",
        "start_day": 60,   # March 1
        "end_day": 120,    # April 30
        "peak_day": 95,    # April 5
        "sigma_t": 21.0,
        "potency_weight": 4.5,
        "base_emission": 550.0,
        "symptoms": "Severe allergic rhinitis, explosive sneezing, asthma exacerbation",
    },
    "ginkgo": {
        "common_name": "Maidenhair Tree",
        "scientific_name": "Ginkgo biloba",
        "family": "Ginkgoaceae",
        "start_day": 74,   # March 15
        "end_day": 105,    # April 15
        "peak_day": 90,    # March 31
        "sigma_t": 14.0,
        "potency_weight": 2.0,
        "base_emission": 200.0,
        "symptoms": "Mild ocular itching, localized nasal congestion",
    },
    "california_black_walnut": {
        "common_name": "California Black Walnut",
        "scientific_name": "Juglans hindsii",
        "family": "Juglandaceae",
        "start_day": 91,   # April 1
        "end_day": 151,    # May 31
        "peak_day": 121,   # May 1
        "sigma_t": 21.0,
        "potency_weight": 5.0,
        "base_emission": 450.0,
        "symptoms": "Intense throat irritation, itchy watery eyes, sinus headaches",
    },
    "olive": {
        "common_name": "Olive Tree",
        "scientific_name": "Olea europaea",
        "family": "Oleaceae",
        "start_day": 105,  # April 15
        "end_day": 150,    # May 30
        "peak_day": 128,   # May 8
        "sigma_t": 18.0,
        "potency_weight": 5.0,
        "base_emission": 600.0,
        "symptoms": "Severe wheezing, skin flares, chronic congestion",
    },
    "perennial_grass": {
        "common_name": "Perennial Turf Grass",
        "scientific_name": "Poaceae spp.",
        "family": "Poaceae",
        "start_day": 121,  # May 1
        "end_day": 181,    # June 30
        "peak_day": 152,   # June 1
        "sigma_t": 21.0,
        "potency_weight": 4.0,
        "base_emission": 350.0,
        "symptoms": "Itchy roof of mouth, heavy tearing, fatigue",
    },
    "redwood": {
        "common_name": "Coast Redwood",
        "scientific_name": "Sequoia sempervirens",
        "family": "Cupressaceae",
        "start_day": 32,   # February 1
        "end_day": 91,     # April 1
        "peak_day": 60,    # March 1
        "sigma_t": 21.0,
        "potency_weight": 2.5,
        "base_emission": 300.0,
        "symptoms": "Mild nasal congestion, sneezing in sensitized individuals",
    },
    "cedar": {
        "common_name": "Cedar",
        "scientific_name": "Cedrus spp.",
        "family": "Pinaceae",
        "start_day": 274,  # October 1
        "end_day": 335,    # December 1
        "peak_day": 305,   # November 1
        "sigma_t": 21.0,
        "potency_weight": 3.0,
        "base_emission": 400.0,
        "symptoms": "Nasal congestion, itchy eyes, mild asthma triggers",
    },
    "pine": {
        "common_name": "Pine",
        "scientific_name": "Pinus spp.",
        "family": "Pinaceae",
        "start_day": 91,   # April 1
        "end_day": 181,    # June 30
        "peak_day": 135,   # May 15
        "sigma_t": 30.0,
        "potency_weight": 2.0,
        "base_emission": 400.0,
        "symptoms": "Mild congestion; large heavy grains, less allergenic",
    },
    "eucalyptus": {
        "common_name": "Eucalyptus",
        "scientific_name": "Eucalyptus spp.",
        "family": "Myrtaceae",
        "start_day": 1,    # Year-round potential
        "end_day": 120,    # Peaks Jan-April
        "peak_day": 60,    # March
        "sigma_t": 30.0,
        "potency_weight": 2.0,
        "base_emission": 250.0,
        "symptoms": "Mild rhinitis, some cross-reactivity with grass allergies",
    },
    "chinese_elm": {
        "common_name": "Chinese Elm",
        "scientific_name": "Ulmus parvifolia",
        "family": "Ulmaceae",
        "start_day": 244,  # September 1
        "end_day": 305,    # November 1
        "peak_day": 274,   # October 1
        "sigma_t": 21.0,
        "potency_weight": 3.0,
        "base_emission": 350.0,
        "symptoms": "Nasal congestion, sneezing, itchy throat",
    },
    "sycamore": {
        "common_name": "Western Sycamore",
        "scientific_name": "Platanus racemosa",
        "family": "Platanaceae",
        "start_day": 74,   # March 15
        "end_day": 121,    # May 1
        "peak_day": 100,   # April 10
        "sigma_t": 18.0,
        "potency_weight": 3.5,
        "base_emission": 400.0,
        "symptoms": "Moderate rhinitis, eye irritation, throat scratchiness",
    },
}


def day_of_year(d: Optional[date] = None) -> int:
    """Get Julian day number (1-365/366) for a given date or today."""
    if d is None:
        d = date.today()
    return d.timetuple().tm_yday


def temporal_gate(
    current_day: int, start_day: int, end_day: int, peak_day: float, sigma_t: float
) -> float:
    """
    Smooth Gaussian temporal gate function Γ(t):
    Γ(t) = exp(-(t - t_peak)² / (2σ_t²))  if t_start <= t <= t_end
    Γ(t) = 0                                 otherwise
    """
    if current_day < start_day or current_day > end_day:
        return 0.0
    return np.exp(-((current_day - peak_day) ** 2) / (2.0 * sigma_t**2))


def effective_emission(species_key: str, current_day: Optional[int] = None) -> float:
    """
    Calculate Q_i(t) = Q_base · W_potency · Γ_i(t) for a species.
    """
    if current_day is None:
        current_day = day_of_year()

    profile = BOTANICAL_CATALOG[species_key]
    gamma = temporal_gate(
        current_day,
        profile["start_day"],
        profile["end_day"],
        profile["peak_day"],
        profile["sigma_t"],
    )
    return profile["base_emission"] * profile["potency_weight"] * gamma


def get_active_species(current_day: Optional[int] = None) -> List[Dict]:
    """Return list of species currently in their pollination window."""
    if current_day is None:
        current_day = day_of_year()

    active = []
    for key, profile in BOTANICAL_CATALOG.items():
        if profile["start_day"] <= current_day <= profile["end_day"]:
            gamma = temporal_gate(
                current_day,
                profile["start_day"],
                profile["end_day"],
                profile["peak_day"],
                profile["sigma_t"],
            )
            active.append({
                "species_key": key,
                "common_name": profile["common_name"],
                "scientific_name": profile["scientific_name"],
                "family": profile["family"],
                "potency_weight": profile["potency_weight"],
                "gamma": round(gamma, 4),
                "effective_emission": round(
                    profile["base_emission"] * profile["potency_weight"] * gamma, 2
                ),
                "symptoms": profile["symptoms"],
            })
    return active


def build_flora_matrix(
    tree_locations: List[Dict], current_day: Optional[int] = None
) -> np.ndarray:
    """
    Build the N×8 Flora Characteristic Matrix P for the dispersion engine.

    tree_locations: list of dicts with keys:
        x, y, species_key
        (optional) radius_m: canopy radius in meters. When present, emission is
        scaled by canopy area relative to a nominal 4 m radius, so a larger
        canopy releases proportionally more pollen.

    Returns ndarray with columns:
        [x, y, Q_base, potency_weight, start_day, end_day, peak_day, sigma_t]
    """
    if current_day is None:
        current_day = day_of_year()

    NOMINAL_RADIUS_M = 4.0
    rows = []
    for tree in tree_locations:
        species_key = tree["species_key"]
        if species_key not in BOTANICAL_CATALOG:
            continue
        profile = BOTANICAL_CATALOG[species_key]
        # Scale emission by canopy area (~radius^2) relative to a nominal tree;
        # clamped so a hand-edited radius cannot produce absurd emission.
        radius_m = tree.get("radius_m")
        if radius_m and radius_m > 0:
            area_factor = (radius_m / NOMINAL_RADIUS_M) ** 2
            area_factor = min(max(area_factor, 0.1), 10.0)
        else:
            area_factor = 1.0
        rows.append([
            tree["x"],
            tree["y"],
            profile["base_emission"] * area_factor,
            profile["potency_weight"],
            profile["start_day"],
            profile["end_day"],
            profile["peak_day"],
            profile["sigma_t"],
        ])

    if not rows:
        return np.empty((0, 8))
    return np.array(rows)
