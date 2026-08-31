"""
Campus AeroAllergen Mapping (CAM) - Flask Application Server

REST API providing:
- Real-time pollen concentration grid calculations
- Student path exposure analysis
- Weather and pollen forecast data
- Flora and building campus data
"""

import os
import json
import numpy as np
from datetime import date
from flask import Flask, jsonify, request
from flask_cors import CORS

from engine.dispersion import superpose_sources, superpose_sources_varwind, wind_components
from engine.potential_flow import solve_potential_flow
from engine.phenology import (
    BOTANICAL_CATALOG,
    build_flora_matrix,
    day_of_year,
    get_active_species,
)
from engine.shadow import compute_full_shadow_matrix
from engine.path_integration import (
    path_exposure_dose,
    find_lowest_exposure_path,
    dose_to_risk_level,
)
from api.weather_service import fetch_current_wind, build_wind_override
from api.pollen_service import fetch_pollen_forecast, get_current_upi, upi_to_clinical_level
from data.campus_data import get_campus, CAMPUSES, DEFAULT_CAMPUS

app = Flask(__name__, static_folder='static', static_url_path='/static')
CORS(app)

# Grid configuration: covers the FULL map area for each campus.
GRID_SIZE = 120
GRID_EXTENT_X = 320.0  # meters E-W from center
GRID_EXTENT_Y = 280.0  # meters N-S from center
_x_lin = np.linspace(-GRID_EXTENT_X, GRID_EXTENT_X, GRID_SIZE)
_y_lin = np.linspace(-GRID_EXTENT_Y, GRID_EXTENT_Y, GRID_SIZE)
GRID_X, GRID_Y = np.meshgrid(_x_lin, _y_lin)

# Fixed scale: peak spring concentration (April with all oaks active)
# This ensures summer shows as low relative to spring peak
FIXED_MAX_CONCENTRATION = 500.0  # grains/m³ (spring peak reference)

# Meters per degree latitude (approx constant)
METERS_PER_DEG_LAT = 111320.0


def resolve_campus():
    """Read the ?campus= query param and return the campus record."""
    return get_campus(request.args.get("campus", DEFAULT_CAMPUS))


def resolve_receptor_height():
    """Read the ?height= query param (breathing-zone height, m). Default 1.5,
    clamped to a sensible 0.5-3.0 m range."""
    h = request.args.get("height", 1.5, type=float)
    if h is None:
        h = 1.5
    return max(0.5, min(3.0, h))


def resolve_potential_flow():
    """Read the ?flow= query param. Defaults to the 2D potential-flow wind
    field diverted around buildings; pass flow=uniform to opt out (uniform wind
    + empirical wake model)."""
    return request.args.get("flow", "potential") != "uniform"


def resolve_wind(campus, body=None):
    """Return wind conditions. In test mode (explicit wind params supplied via
    query string or JSON body) build the wind from those values; otherwise fetch
    live conditions for the campus. Test params: wind_speed, wind_dir,
    stability (optional), temperature (optional), humidity (optional)."""
    src = body if body else request.args

    def _get(key, cast=float):
        if body is not None:
            return body.get(key)
        v = request.args.get(key)
        return cast(v) if v is not None else None

    speed = _get("wind_speed")
    direction = _get("wind_dir")
    if speed is not None and direction is not None:
        stability = _get("stability", str)
        temperature = _get("temperature")
        humidity = _get("humidity")
        return build_wind_override(
            float(speed), float(direction),
            stability_class=stability if stability else None,
            temperature=float(temperature) if temperature is not None else None,
            humidity=float(humidity) if humidity is not None else None,
        )
    return fetch_current_wind(campus["center_lat"], campus["center_lon"])


def campus_static_path(campus_key: str, filename: str) -> str:
    """Path to a per-campus static file, falling back to the legacy top-level file."""
    base = os.path.dirname(__file__)
    campus_path = os.path.join(base, 'static', campus_key, filename)
    if os.path.exists(campus_path):
        return campus_path
    return os.path.join(base, 'static', filename)


def compute_concentration_field(campus: dict, wind_data: dict, current_day: int,
                                receptor_height: float = 1.5,
                                use_potential_flow: bool = False) -> np.ndarray:
    """Run the full dispersion simulation for a campus.

    Uses SAM-detected trees and SAM-detected building rooftops from the campus
    detection cache when available. Detected buildings carry a footprint
    (width_m x length_m) but no measured height (satellite imagery is top-down),
    so a default average height of 5 m is assumed for wake effects.
    receptor_height is the breathing-zone height (m) at which concentration is
    evaluated (default 1.5 m).
    """
    center_lat = campus["center_lat"]
    center_lon = campus["center_lon"]
    mplat = METERS_PER_DEG_LAT
    mplon = 111320.0 * np.cos(np.radians(center_lat))

    cache_path = campus_static_path(campus["key"], 'detect_cache.json')
    mask_path = campus_static_path(campus["key"], 'building_mask.npy')

    # Use detected trees if available; otherwise fall back to the campus flora set
    detected_trees = []
    detected_buildings = []
    if os.path.exists(cache_path):
        with open(cache_path) as f:
            detect_data = json.load(f)
            detected_trees = detect_data.get("trees", [])
            detected_buildings = detect_data.get("buildings", [])

    if detected_trees:
        tree_locations = []
        for dt in detected_trees:
            species_key = dt.get("species_key", "coast_live_oak")
            x = (dt["lng"] - center_lon) * mplon
            y = (dt["lat"] - center_lat) * mplat
            tree_locations.append({"x": x, "y": y, "species_key": species_key})
        flora_matrix = build_flora_matrix(tree_locations, current_day)
    else:
        flora_matrix = build_flora_matrix(campus["trees"], current_day)

    if flora_matrix.shape[0] == 0:
        return np.zeros_like(GRID_X)

    # Buildings for the wake model: prefer SAM-detected rooftops (converted from
    # lat/lng + footprint to local meters). Height is floors x 3 m when the
    # building carries a floor count or explicit height, else a 5 m default.
    DEFAULT_BUILDING_HEIGHT_M = 5.0
    METERS_PER_FLOOR = 3.0
    if detected_buildings:
        buildings = []
        for b in detected_buildings:
            bx = (b["lng"] - center_lon) * mplon
            by = (b["lat"] - center_lat) * mplat
            width = b.get("width_m", 15.0)
            length = b.get("length_m", b.get("height_m", 15.0))
            if b.get("floors"):
                height = float(b["floors"]) * METERS_PER_FLOOR
            elif b.get("height"):
                height = float(b["height"])
            else:
                height = DEFAULT_BUILDING_HEIGHT_M
            buildings.append({
                "x": bx, "y": by,
                "width": width,
                "length": length,
                "height": height,
            })
    else:
        buildings = [
            {"x": b["local_x"], "y": b["local_y"],
             "width": b["width"], "height": b["height"], "length": b["length"]}
            for b in campus["buildings"]
        ]

    if use_potential_flow and detected_buildings:
        # Physically-computed 2D potential-flow wind field diverted around the
        # building footprints, then plumes advected along the local flow.
        building_mask = _rasterize_buildings(detected_buildings, center_lat, center_lon, mplat, mplon)
        u_inf, v_inf = wind_components(wind_data["speed"], wind_data["direction"])
        u_field, v_field = solve_potential_flow(building_mask, u_inf, v_inf)
        concentration = superpose_sources_varwind(
            GRID_X, GRID_Y, flora_matrix, u_field, v_field,
            GRID_EXTENT_X, GRID_EXTENT_Y, current_day,
            wind_data.get("stability_class", "D"), receptor_height,
        )
    else:
        concentration = superpose_sources(
            GRID_X, GRID_Y,
            flora_matrix,
            wind_data["speed"],
            wind_data["direction"],
            buildings,
            current_day,
            wind_data.get("stability_class", "D"),
            receptor_height,
        )

    # Zero out concentration over building footprints: at breathing height
    # inside a building there is no outdoor pollen exposure. Build the mask
    # directly from the detected building polygons so it always matches the
    # buildings shown on the map (works for every campus, no stale .npy needed).
    if detected_buildings:
        building_mask = _rasterize_buildings(detected_buildings, center_lat, center_lon, mplat, mplon)
        concentration[building_mask] = 0.0
    elif os.path.exists(mask_path):
        building_mask = np.load(mask_path)
        if building_mask.shape == concentration.shape:
            concentration[building_mask] = 0.0

    return concentration


def _rasterize_buildings(detected_buildings, center_lat, center_lon, mplat, mplon):
    """Return a boolean grid mask that is True inside any detected building
    footprint. Polygons (lat/lng) are converted to local meters and tested
    against the concentration grid with a vectorized point-in-polygon test."""
    mask = np.zeros_like(GRID_X, dtype=bool)
    gx = GRID_X.ravel()
    gy = GRID_Y.ravel()
    inside = np.zeros(gx.shape, dtype=bool)

    for b in detected_buildings:
        poly = b.get("polygon")
        if not poly or len(poly) < 3:
            continue
        # Convert polygon corners (lat, lng) to local meters (x=E, y=N).
        xs = np.array([(pt[1] - center_lon) * mplon for pt in poly])
        ys = np.array([(pt[0] - center_lat) * mplat for pt in poly])
        # Quick bounding-box reject for speed.
        in_bbox = (gx >= xs.min()) & (gx <= xs.max()) & (gy >= ys.min()) & (gy <= ys.max())
        if not np.any(in_bbox):
            continue
        idx = np.where(in_bbox)[0]
        px, py = gx[idx], gy[idx]
        # Ray-casting point-in-polygon, vectorized over candidate points.
        n = len(xs)
        hit = np.zeros(px.shape, dtype=bool)
        j = n - 1
        for i in range(n):
            xi, yi, xj, yj = xs[i], ys[i], xs[j], ys[j]
            cond = ((yi > py) != (yj > py)) & (
                px < (xj - xi) * (py - yi) / (yj - yi + 1e-12) + xi)
            hit ^= cond
            j = i
        inside[idx] |= hit

    mask = inside.reshape(GRID_X.shape)
    return mask


@app.route("/api/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "service": "CAM Backend"})


@app.route("/api/campuses", methods=["GET"])
def list_campuses():
    """List available campuses with their display metadata and map config."""
    out = []
    for key, c in CAMPUSES.items():
        out.append({
            "key": key,
            "name": c["name"],
            "subtitle": c["subtitle"],
            "center_lat": c["center_lat"],
            "center_lon": c["center_lon"],
            "bounds": c["bounds"],
            "boundary": [{"lat": pt[0], "lng": pt[1]} for pt in c["boundary"]],
        })
    return jsonify({"campuses": out, "default": DEFAULT_CAMPUS})


@app.route("/api/static/<path:filename>", methods=["GET"])
def serve_static(filename):
    """Serve a per-campus static file (e.g. satellite.png). Use ?campus=."""
    from flask import send_from_directory
    campus_key = get_campus(request.args.get("campus", DEFAULT_CAMPUS))["key"]
    campus_dir = os.path.join(os.path.dirname(__file__), 'static', campus_key)
    if os.path.exists(os.path.join(campus_dir, filename)):
        return send_from_directory(campus_dir, filename)
    return send_from_directory('static', filename)


@app.route("/api/concentration", methods=["GET"])
def get_concentration():
    """
    Get current pollen concentration grid.
    Query params: day (optional, Julian day override)
    """
    campus = resolve_campus()
    current_day = request.args.get("day", day_of_year(), type=int)
    wind_data = resolve_wind(campus)

    concentration = compute_concentration_field(campus, wind_data, current_day,
                                                resolve_receptor_height(),
                                                resolve_potential_flow())

    # Downsample for JSON transfer (every 4th point)
    step = max(1, GRID_SIZE // 25)
    sampled_c = concentration[::step, ::step]
    sampled_x = GRID_X[::step, ::step]
    sampled_y = GRID_Y[::step, ::step]

    return jsonify({
        "concentration": sampled_c.tolist(),
        "grid_x": sampled_x.tolist(),
        "grid_y": sampled_y.tolist(),
        "max_concentration": float(np.max(concentration)),
        "mean_concentration": float(np.mean(concentration)),
        "wind": wind_data,
        "current_day": current_day,
        "grid_resolution_m": round(2 * GRID_EXTENT_X / GRID_SIZE, 1),
    })


@app.route("/api/heatmap", methods=["GET"])
def get_heatmap():
    """
    Get concentration data formatted for frontend heatmap overlay.
    Returns lat/lng weighted points for Google Maps HeatmapLayer.
    """
    current_day = request.args.get("day", day_of_year(), type=int)
    campus = resolve_campus()
    wind_data = resolve_wind(campus)
    concentration = compute_concentration_field(campus, wind_data, current_day,
                                                resolve_receptor_height(),
                                                resolve_potential_flow())

    center_lat = campus["center_lat"]
    center_lon = campus["center_lon"]
    meters_per_deg_lat = METERS_PER_DEG_LAT
    meters_per_deg_lon = 111320.0 * np.cos(np.radians(center_lat))

    heatmap_points = []
    step = max(1, GRID_SIZE // 40)
    # Use FIXED scale so spring peak = 1.0, summer shows as proportionally low
    max_c = FIXED_MAX_CONCENTRATION

    for i in range(0, GRID_SIZE, step):
        for j in range(0, GRID_SIZE, step):
            c = concentration[i, j]
            if c > 0.5:  # minimum threshold to show
                lat = center_lat + GRID_Y[i, j] / meters_per_deg_lat
                lng = center_lon + GRID_X[i, j] / meters_per_deg_lon
                weight = min(c / max_c, 1.0)
                heatmap_points.append({
                    "lat": round(lat, 7),
                    "lng": round(lng, 7),
                    "weight": round(weight, 4),
                })

    actual_max = float(np.max(concentration))
    return jsonify({
        "points": heatmap_points,
        "max_concentration": round(actual_max, 2),
        "fixed_scale_max": FIXED_MAX_CONCENTRATION,
        "pct_of_peak": round(actual_max / FIXED_MAX_CONCENTRATION * 100, 1),
        "wind": wind_data,
        "active_species": get_active_species(current_day),
    })


@app.route("/api/flora", methods=["GET"])
def get_flora():
    """Get all campus flora with current emission status. Query param: campus"""
    campus = resolve_campus()
    current_day = request.args.get("day", day_of_year(), type=int)
    active = get_active_species(current_day)
    active_keys = {s["species_key"] for s in active}

    flora_data = []
    for tree in campus["trees"]:
        profile = BOTANICAL_CATALOG.get(tree["species_key"], {})
        is_active = tree["species_key"] in active_keys
        flora_data.append({
            "x": tree["x"],
            "y": tree["y"],
            "lat": tree.get("lat", campus["center_lat"]),
            "lng": tree.get("lng", campus["center_lon"]),
            "species_key": tree["species_key"],
            "common_name": profile.get("common_name", "Unknown"),
            "scientific_name": profile.get("scientific_name", ""),
            "family": profile.get("family", ""),
            "potency_weight": profile.get("potency_weight", 0),
            "is_active": is_active,
            "symptoms": profile.get("symptoms", ""),
        })

    return jsonify({"flora": flora_data, "active_species": active, "current_day": current_day})


@app.route("/api/buildings", methods=["GET"])
def get_buildings():
    """Get campus building data for wake visualization. Query param: campus"""
    campus = resolve_campus()
    return jsonify({"buildings": campus["buildings"]})


@app.route("/api/boundary", methods=["GET"])
def get_boundary():
    """Get campus boundary polygon. Query param: campus"""
    campus = resolve_campus()
    return jsonify({"boundary": [{"lat": pt[0], "lng": pt[1]} for pt in campus["boundary"]]})


@app.route("/api/detect", methods=["GET"])
def detect_features():
    """Return cached tree/building detection for the campus. Query param: campus"""
    campus = resolve_campus()
    cache_path = campus_static_path(campus["key"], 'detect_cache.json')

    if os.path.exists(cache_path):
        with open(cache_path) as f:
            return jsonify(json.load(f))

    # No cache: try live detection (requires Pillow/scikit-image). We ship a
    # pre-generated cache so this path is not normally hit in production.
    try:
        from engine.detect import run_detection
        results = run_detection(bounds=campus["bounds"], use_position_classifier=(campus["key"] == "gunn"))
        campus_dir = os.path.join(os.path.dirname(__file__), 'static', campus["key"])
        os.makedirs(campus_dir, exist_ok=True)
        with open(os.path.join(campus_dir, 'detect_cache.json'), 'w') as f:
            json.dump(results, f)
        return jsonify(results)
    except Exception as e:
        return jsonify({"trees": [], "buildings": [], "error": str(e)})


@app.route("/api/detect/update", methods=["POST"])
def update_detection():
    """Update cached detection results (trees and/or buildings). Query param: campus.

    Body may include "trees" and/or "buildings" arrays. Whichever is provided is
    replaced; the other is preserved from the existing cache. This backs the
    interactive delete/edit workflow so corrections persist in the cache that
    the deployed server serves (no ML model needed in production).
    """
    campus = resolve_campus()
    campus_dir = os.path.join(os.path.dirname(__file__), 'static', campus["key"])
    os.makedirs(campus_dir, exist_ok=True)
    cache_path = os.path.join(campus_dir, 'detect_cache.json')

    body = request.get_json()
    if not body or ("trees" not in body and "buildings" not in body):
        return jsonify({"error": "Must include 'trees' and/or 'buildings' array"}), 400

    data = {"trees": [], "buildings": [], "image_size": [1398, 1600]}
    if os.path.exists(cache_path):
        with open(cache_path) as f:
            existing = json.load(f)
            data["trees"] = existing.get("trees", [])
            data["buildings"] = existing.get("buildings", [])
            data["image_size"] = existing.get("image_size", [1398, 1600])

    if "trees" in body:
        data["trees"] = body["trees"]
    if "buildings" in body:
        data["buildings"] = body["buildings"]

    with open(cache_path, 'w') as f:
        json.dump(data, f)

    return jsonify({
        "status": "ok",
        "trees_count": len(data["trees"]),
        "buildings_count": len(data["buildings"]),
    })


@app.route("/api/weather", methods=["GET"])
def get_weather():
    """Get current weather conditions. Query param: campus"""
    campus = resolve_campus()
    return jsonify(resolve_wind(campus))


@app.route("/api/pollen-forecast", methods=["GET"])
def get_pollen_forecast():
    """Get regional pollen forecast with clinical mappings. Query param: campus"""
    campus = resolve_campus()
    days = request.args.get("days", 5, type=int)
    forecasts = fetch_pollen_forecast(days=days, lat=campus["center_lat"], lon=campus["center_lon"])

    enriched = []
    for f in forecasts:
        max_upi = max(f["tree_upi"], f["grass_upi"], f["weed_upi"])
        clinical = upi_to_clinical_level(max_upi)
        enriched.append({**f, "clinical": clinical})

    return jsonify({"forecasts": enriched})


@app.route("/api/path-exposure", methods=["POST"])
def calculate_path_exposure():
    """
    Calculate exposure dose along a student walking path.
    Body: { "path": [[x1,y1], [x2,y2], ...] }
    """
    campus = resolve_campus()
    body = request.get_json()
    if not body or "path" not in body:
        return jsonify({"error": "Request body must include 'path' array"}), 400

    path_points = [tuple(p) for p in body["path"]]
    current_day = body.get("day", day_of_year())
    wind_data = resolve_wind(campus, body)

    height = body.get("height", resolve_receptor_height())
    concentration = compute_concentration_field(campus, wind_data, current_day, height)
    result = path_exposure_dose(path_points, concentration, GRID_X, GRID_Y)
    result["wind"] = wind_data
    result["current_day"] = current_day

    return jsonify(result)


@app.route("/api/optimal-route", methods=["POST"])
def get_optimal_route():
    """
    Find lowest-exposure path between two points.
    Body: { "start": [x, y], "end": [x, y] }
    """
    campus = resolve_campus()
    body = request.get_json()
    if not body or "start" not in body or "end" not in body:
        return jsonify({"error": "Body must include 'start' and 'end'"}), 400

    start = tuple(body["start"])
    end = tuple(body["end"])
    current_day = body.get("day", day_of_year())
    wind_data = resolve_wind(campus, body)

    height = body.get("height", resolve_receptor_height())
    concentration = compute_concentration_field(campus, wind_data, current_day, height)

    direct_path = [start, end]
    direct_dose = path_exposure_dose(direct_path, concentration, GRID_X, GRID_Y)

    optimized_path = find_lowest_exposure_path(start, end, concentration, GRID_X, GRID_Y)
    optimized_dose = path_exposure_dose(optimized_path, concentration, GRID_X, GRID_Y)

    return jsonify({
        "direct_route": {
            "path": direct_path,
            "exposure": direct_dose,
        },
        "optimized_route": {
            "path": [(round(p[0], 1), round(p[1], 1)) for p in optimized_path],
            "exposure": optimized_dose,
        },
        "dose_reduction_pct": round(
            (1 - optimized_dose["total_dose"] / max(direct_dose["total_dose"], 0.001)) * 100, 1
        ),
        "wind": wind_data,
    })


@app.route("/api/advisory", methods=["GET"])
def get_advisory():
    """
    Get pre-commute clinical advisory for current conditions.
    Returns personalized risk assessment and routing recommendations.
    """
    campus = resolve_campus()
    current_day = request.args.get("day", day_of_year(), type=int)
    wind_data = resolve_wind(campus)
    pollen_upi = get_current_upi(campus["center_lat"], campus["center_lon"])
    active = get_active_species(current_day)

    max_upi = max(pollen_upi.get("tree_upi", 0), pollen_upi.get("grass_upi", 0), pollen_upi.get("weed_upi", 0))
    clinical = upi_to_clinical_level(max_upi)

    concentration = compute_concentration_field(campus, wind_data, current_day,
                                                resolve_receptor_height(),
                                                resolve_potential_flow())

    # Evaluate all standard paths
    path_advisories = []
    for sp in campus["paths"]:
        waypoints = [(w["x"], w["y"]) for w in sp["waypoints"]]
        dose = path_exposure_dose(waypoints, concentration, GRID_X, GRID_Y)
        path_advisories.append({
            "path_name": sp["name"],
            "risk_level": dose["risk_level"],
            "total_dose": dose["total_dose"],
            "max_concentration": dose["max_concentration"],
        })

    high_risk_paths = [p for p in path_advisories if p["risk_level"] in ("high", "very_high")]

    # Find named detected buildings sitting in the highest-concentration areas,
    # so the advisory can refer to them by name (e.g. "near Bow Gym").
    hotspot_buildings = _named_building_hotspots(campus, concentration)

    advisory_message = ""
    if high_risk_paths:
        worst = max(high_risk_paths, key=lambda p: p["total_dose"])
        wind_dir_text = _wind_direction_text(wind_data["direction"])
        active_names = ", ".join(s["common_name"] for s in active[:2])
        advisory_message = (
            f"The route '{worst['path_name']}' currently has high pollen concentration "
            f"due to {wind_dir_text} winds during peak {active_names} season. "
            f"Consider an alternate route to reduce exposure."
        )
        if hotspot_buildings:
            names = ", ".join(hotspot_buildings)
            advisory_message += (
                f" Elevated pollen was detected near {names}; sensitive students "
                f"should minimize time in these areas."
            )
    elif hotspot_buildings:
        # Even without a high-risk standard path, flag named building hotspots.
        names = ", ".join(hotspot_buildings)
        advisory_message = (
            f"Pollen is currently elevated near {names}. Sensitive students may "
            f"wish to limit time in these areas."
        )

    return jsonify({
        "clinical_level": clinical,
        "regional_upi": pollen_upi,
        "active_species": active,
        "wind": wind_data,
        "path_advisories": path_advisories,
        "advisory_message": advisory_message,
        "timestamp": wind_data.get("timestamp"),
    })


def _wind_direction_text(deg: float) -> str:
    """Convert wind direction degrees to cardinal text."""
    directions = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]
    idx = int((deg + 22.5) / 45.0) % 8
    return directions[idx]


def _named_building_hotspots(campus, concentration, max_names=3, threshold=50.0):
    """Return up to max_names named detected buildings that sit in the highest
    pollen-concentration areas, so advisories can reference them by name.

    Samples the concentration grid at each named building's location and keeps
    those above `threshold` (grains/m^3), sorted by concentration descending.
    """
    cache_path = campus_static_path(campus["key"], 'detect_cache.json')
    if not os.path.exists(cache_path):
        return []
    with open(cache_path) as f:
        buildings = json.load(f).get("buildings", [])

    center_lat = campus["center_lat"]
    center_lon = campus["center_lon"]
    mplat = METERS_PER_DEG_LAT
    mplon = 111320.0 * np.cos(np.radians(center_lat))
    ny, nx = concentration.shape

    scored = []
    for b in buildings:
        name = (b.get("name") or "").strip()
        # Skip unnamed and default placeholder names.
        if not name or name.lower() == "new building":
            continue
        bx = (b["lng"] - center_lon) * mplon
        by = (b["lat"] - center_lat) * mplat
        gx = int(round((bx + GRID_EXTENT_X) / (2 * GRID_EXTENT_X) * (nx - 1)))
        gy = int(round((by + GRID_EXTENT_Y) / (2 * GRID_EXTENT_Y) * (ny - 1)))
        if not (0 <= gx < nx and 0 <= gy < ny):
            continue
        # Sample the max concentration in a small neighborhood around the building.
        y0, y1 = max(0, gy - 2), min(ny, gy + 3)
        x0, x1 = max(0, gx - 2), min(nx, gx + 3)
        c = float(np.max(concentration[y0:y1, x0:x1]))
        if c >= threshold:
            scored.append((c, name))

    scored.sort(reverse=True)
    # De-duplicate names while preserving order.
    seen, out = set(), []
    for _, name in scored:
        if name not in seen:
            seen.add(name)
            out.append(name)
        if len(out) >= max_names:
            break
    return out


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5001))
    app.run(host="0.0.0.0", port=port, debug=True)
