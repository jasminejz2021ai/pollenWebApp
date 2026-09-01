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


# ---------------------------------------------------------------------------
# "Other" class as a prevalence-weighted mixture of unmodeled genera.
#
# Trees not confidently classified into a named genus are labeled "other". Such
# a tree is modeled not as one generic profile but as a weighted blend of the
# genera that make up the *unmodeled long tail* of each campus's real tree
# inventory. This gives "Other" a realistic, possibly multi-modal seasonal
# emission (e.g. a little spring, a little fall) grounded in what actually grows
# on campus, rather than a single hand-picked spring bump.
#
# TAIL_PROFILES holds phenology/emission for tail genera not already in
# BOTANICAL_CATALOG. Entries already in BOTANICAL_CATALOG (e.g. eucalyptus,
# olive, ginkgo, walnut, pine) are referenced by key in the weight tables.
# ---------------------------------------------------------------------------
TAIL_PROFILES = {
    # Low/moderate-allergen ornamentals and non-natives common on Bay Area
    # campuses. Values are representative aerobiological estimates.
    "hawthorn":    {"base_emission": 180.0, "potency_weight": 2.0, "start_day": 105, "end_day": 152, "peak_day": 128, "sigma_t": 15.0},
    "privet":      {"base_emission": 300.0, "potency_weight": 3.5, "start_day": 152, "end_day": 213, "peak_day": 182, "sigma_t": 18.0},
    "sweetgum":    {"base_emission": 200.0, "potency_weight": 2.0, "start_day": 74,  "end_day": 121, "peak_day": 98,  "sigma_t": 15.0},
    "pepper_tree": {"base_emission": 220.0, "potency_weight": 2.5, "start_day": 152, "end_day": 273, "peak_day": 213, "sigma_t": 30.0},
    "crape_myrtle":{"base_emission": 120.0, "potency_weight": 1.5, "start_day": 182, "end_day": 258, "peak_day": 213, "sigma_t": 20.0},
    "ornamental_pear": {"base_emission": 150.0, "potency_weight": 2.0, "start_day": 60, "end_day": 105, "peak_day": 82, "sigma_t": 12.0},
    "spruce":      {"base_emission": 250.0, "potency_weight": 2.0, "start_day": 105, "end_day": 152, "peak_day": 128, "sigma_t": 15.0},
    "plum":        {"base_emission": 130.0, "potency_weight": 2.0, "start_day": 46,  "end_day": 91,  "peak_day": 68,  "sigma_t": 12.0},
    "pistache":    {"base_emission": 260.0, "potency_weight": 3.0, "start_day": 91,  "end_day": 121, "peak_day": 105, "sigma_t": 12.0},
    "generic_broadleaf": {"base_emission": 250.0, "potency_weight": 3.0, "start_day": 60, "end_day": 151, "peak_day": 105, "sigma_t": 25.0},
}


def _tail_profile(key):
    """Look up a tail genus profile from BOTANICAL_CATALOG first, then TAIL_PROFILES."""
    if key in BOTANICAL_CATALOG:
        p = BOTANICAL_CATALOG[key]
        return {k: p[k] for k in ("base_emission", "potency_weight", "start_day", "end_day", "peak_day", "sigma_t")}
    return TAIL_PROFILES[key]


# Per-campus mixture weights for the "Other" class, taken from the unmodeled
# long tail of each campus's tree inventory (normalized internally). Gunn is
# from the 2009 PAUSD arborist survey; Stanford from its campus tree inventory.
OTHER_MIX_WEIGHTS = {
    "gunn": {
        # Gunn modeled genera are oak/redwood/cedar/sycamore/elm/pine; the tail
        # below is the remainder of the 2009 survey (approx. counts as weights).
        "cedar": 27, "hawthorn": 14, "privet": 11, "sweetgum": 9, "pepper_tree": 8,
        "eucalyptus": 6, "crape_myrtle": 5, "ornamental_pear": 5, "spruce": 4,
        "plum": 4, "olive": 3, "ginkgo": 1, "california_black_walnut": 2,
        "pistache": 2, "generic_broadleaf": 6,
    },
    "stanford": {
        # Stanford modeled genera are coast live oak/palm/eucalyptus/redwood/
        # valley oak/olive; the tail is the broad remainder of the inventory.
        "pistache": 8, "pine": 8, "sweetgum": 4, "privet": 4, "crape_myrtle": 3,
        "plum": 3, "ginkgo": 2, "california_black_walnut": 2, "cedar": 3,
        "generic_broadleaf": 20,
    },
}


def _other_effective_emission(campus_key, current_day):
    """Weighted-sum effective emission (grains/s, potency-weighted) at
    current_day for the 'Other' class of a campus. Returns Q*W*Gamma summed
    over the campus's unmodeled tail genera with inventory-derived weights."""
    weights = OTHER_MIX_WEIGHTS.get(campus_key) or OTHER_MIX_WEIGHTS["gunn"]
    total_w = float(sum(weights.values())) or 1.0
    e = 0.0
    for key, w in weights.items():
        p = _tail_profile(key)
        if current_day < p["start_day"] or current_day > p["end_day"]:
            gamma = 0.0
        else:
            gamma = np.exp(-((current_day - p["peak_day"]) ** 2) / (2.0 * p["sigma_t"] ** 2))
        e += (w / total_w) * p["base_emission"] * p["potency_weight"] * gamma
    return float(e)


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
    tree_locations: List[Dict], current_day: Optional[int] = None,
    campus_key: Optional[str] = None,
) -> np.ndarray:
    """
    Build the N×8 Flora Characteristic Matrix P for the dispersion engine.

    tree_locations: list of dicts with keys:
        x, y, species_key
        (optional) radius_m: canopy radius in meters. When present, emission is
        scaled by canopy area relative to a nominal 4 m radius, so a larger
        canopy releases proportionally more pollen.
    campus_key: which campus (selects the "Other" mixture weights). The "Other"
        class is modeled as a prevalence-weighted blend of the campus's unmodeled
        tail genera rather than a single generic profile.

    Returns ndarray with columns:
        [x, y, Q_base, potency_weight, start_day, end_day, peak_day, sigma_t]

    The dispersion engine evaluates each row as
        effective = Q_base * potency_weight * Gamma(current_day; peak_day, sigma_t)
    gated by [start_day, end_day]. For "Other" rows we precompute the weighted
    mixture emission at current_day and encode it as a degenerate always-on gate
    (peak_day = current_day, wide sigma, full-year window) so the engine
    reproduces exactly that value.
    """
    if current_day is None:
        current_day = day_of_year()

    NOMINAL_RADIUS_M = 4.0

    # Precompute the "Other" mixture emission for this campus and day once.
    other_emission = _other_effective_emission(campus_key or "gunn", current_day)

    rows = []
    for tree in tree_locations:
        species_key = tree["species_key"]

        # Canopy-area scaling (shared by all species): larger canopy emits more.
        radius_m = tree.get("radius_m")
        if radius_m and radius_m > 0:
            area_factor = (radius_m / NOMINAL_RADIUS_M) ** 2
            area_factor = min(max(area_factor, 0.1), 10.0)
        else:
            area_factor = 1.0

        if species_key == "other" or species_key not in BOTANICAL_CATALOG:
            # Weighted-mixture "Other": emit the precomputed day value directly,
            # using a degenerate always-on gate so the engine returns it as-is.
            rows.append([
                tree["x"],
                tree["y"],
                other_emission * area_factor,  # Q_base already = sum(w*Q*W*Gamma)
                1.0,                            # potency folded into the mixture
                1,                              # start_day (full year)
                366,                            # end_day
                float(current_day),             # peak_day == today -> Gamma = 1
                1e6,                            # huge sigma -> Gamma ~ 1
            ])
            continue

        profile = BOTANICAL_CATALOG[species_key]
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
