"""
Campus AeroAllergen Mapping (CAM) - Campus Data

Multi-campus registry. Each campus defines its center, satellite-image bounds,
boundary polygon, trees, buildings, and student paths. Access a campus via
get_campus(key); the default campus is "gunn".

Campuses:
- gunn: Gunn High School (780 Arastradero Rd, Palo Alto) - center 37.4027, -122.1342
- stanford: Stanford Main Quad - center ~37.4275, -122.1697

Tree positions placed by matching visible canopy on satellite imagery.
Building positions from site maps. Boundaries traced from property outlines.
"""

import math
import numpy as np
from typing import Tuple, List


def _meters_per_deg_lon(lat: float) -> float:
    return 111320.0 * math.cos(math.radians(lat))


def _make_local_to_latlng(center_lat: float, center_lon: float):
    """Return a local-meters -> lat/lng converter for a given campus center."""
    mplat = 111320.0
    mplon = _meters_per_deg_lon(center_lat)

    def local_to_latlng(x: float, y: float) -> Tuple[float, float]:
        lat = center_lat + y / mplat
        lng = center_lon + x / mplon
        return round(lat, 7), round(lng, 7)

    return local_to_latlng


def _rotate_point(cx, cy, x, y, angle_deg):
    """Rotate point (x,y) around (cx,cy) by angle_deg. Returns (lat, lng)."""
    rad = math.radians(angle_deg)
    dx, dy = x - cx, y - cy
    rx = dx * math.cos(rad) - dy * math.sin(rad)
    ry = dx * math.sin(rad) + dy * math.cos(rad)
    return (round(cy + ry, 6), round(cx + rx, 6))


def _rotated_rect_boundary(center_lat, center_lng, half_w, half_h, angle):
    """Build a closed rotated-rectangle boundary polygon as [(lat, lng), ...]."""
    corners_unrotated = [
        (center_lng - half_w, center_lat - half_h),
        (center_lng + half_w, center_lat - half_h),
        (center_lng + half_w, center_lat + half_h),
        (center_lng - half_w, center_lat + half_h),
    ]
    boundary: List[Tuple[float, float]] = []
    for (lng, lat) in corners_unrotated:
        rlat, rlng = _rotate_point(center_lng, center_lat, lng, lat, angle)
        boundary.append((rlat, rlng))
    boundary.append(boundary[0])
    return boundary


# ============================================================
# GUNN HIGH SCHOOL
# ============================================================
GUNN_CENTER_LAT = 37.4027
GUNN_CENTER_LON = -122.1342
_gunn_local = _make_local_to_latlng(GUNN_CENTER_LAT, GUNN_CENTER_LON)


def local_to_latlng(x: float, y: float) -> Tuple[float, float]:
    """Backward-compatible Gunn local->lat/lng converter."""
    return _gunn_local(x, y)


def _tree(x: float, y: float, species_key: str) -> dict:
    lat, lng = _gunn_local(x, y)
    return {"x": x, "y": y, "species_key": species_key, "lat": lat, "lng": lng}


# Gunn boundary: rectangle rotated 25 deg to align with Arastradero Rd
GUNN_BOUNDARY = _rotated_rect_boundary(37.4018, -122.1338, 0.0032, 0.0022, 25)

# Backward-compatible aliases (default campus = Gunn)
CAMPUS_BOUNDARY = GUNN_BOUNDARY
CAMPUS_CENTER_LAT = GUNN_CENTER_LAT
CAMPUS_CENTER_LON = GUNN_CENTER_LON
METERS_PER_DEG_LAT = 111320.0
METERS_PER_DEG_LON = _meters_per_deg_lon(GUNN_CENTER_LAT)

# ============================================================
# CAMPUS TREES - Placed by matching satellite canopy
# ============================================================
# Key visible canopy clusters on satellite:
# 1. Dense row along Arastradero Rd (N border) - mix of oaks, eucalyptus
# 2. Large grove W of Spangenberg Theater - redwoods, eucalyptus
# 3. Central scattered canopy between buildings - oaks
# 4. Row along Miranda Ave (W border) - various
# 5. Athletic fields (S) - grass only
# 6. Scattered between E-side buildings - oaks, elms
# 7. Courtyard trees between classroom wings

CAMPUS_TREES = GUNN_TREES = [
    # === ARASTRADERO ROAD FRONTAGE (North border) - Dense tree line ===
    # Large visible canopy along the entire north edge
    _tree(-110, 80, "valley_oak"),
    _tree(-95, 82, "eucalyptus"),
    _tree(-80, 80, "valley_oak"),
    _tree(-65, 78, "coast_live_oak"),
    _tree(-50, 80, "valley_oak"),
    _tree(-35, 79, "coast_live_oak"),
    _tree(-20, 80, "valley_oak"),
    _tree(-5, 82, "ginkgo"),
    _tree(10, 80, "valley_oak"),
    _tree(25, 79, "coast_live_oak"),
    _tree(40, 80, "valley_oak"),
    _tree(55, 78, "coast_live_oak"),
    _tree(70, 80, "valley_oak"),
    _tree(85, 79, "pine"),
    _tree(100, 80, "valley_oak"),

    # === MIRANDA AVE / WEST BORDER - Tree line ===
    _tree(-125, 65, "eucalyptus"),
    _tree(-125, 50, "eucalyptus"),
    _tree(-125, 35, "eucalyptus"),
    _tree(-122, 20, "redwood"),
    _tree(-120, 5, "redwood"),
    _tree(-120, -10, "redwood"),
    _tree(-118, -25, "valley_oak"),
    _tree(-118, -40, "coast_live_oak"),
    _tree(-115, -55, "valley_oak"),

    # === SPANGENBERG THEATER GROVE (W side) - Dense redwood grove ===
    _tree(-100, 35, "redwood"),
    _tree(-95, 30, "redwood"),
    _tree(-105, 28, "redwood"),
    _tree(-98, 22, "redwood"),
    _tree(-92, 25, "redwood"),
    _tree(-100, 18, "redwood"),
    _tree(-95, 15, "redwood"),
    _tree(-88, 20, "redwood"),
    _tree(-105, 40, "redwood"),
    _tree(-90, 35, "redwood"),

    # === J-BUILDING AREA (NW campus) ===
    _tree(-70, 55, "valley_oak"),
    _tree(-55, 58, "coast_live_oak"),
    _tree(-60, 50, "valley_oak"),
    _tree(-45, 55, "coast_live_oak"),
    _tree(-75, 45, "valley_oak"),
    _tree(-58, 42, "coast_live_oak"),

    # === CENTRAL QUAD / N-WING AREA ===
    # Scattered oaks visible between classroom buildings
    _tree(-15, 30, "valley_oak"),
    _tree(5, 32, "valley_oak"),
    _tree(-5, 22, "coast_live_oak"),
    _tree(15, 25, "coast_live_oak"),
    _tree(-20, 15, "valley_oak"),
    _tree(10, 18, "valley_oak"),
    _tree(0, 10, "coast_live_oak"),
    _tree(20, 12, "coast_live_oak"),
    _tree(-10, 5, "chinese_elm"),
    _tree(8, 5, "chinese_elm"),

    # === H/K/G BUILDING CORRIDORS (Central-East) ===
    _tree(30, 30, "coast_live_oak"),
    _tree(45, 28, "valley_oak"),
    _tree(35, 18, "chinese_elm"),
    _tree(50, 20, "chinese_elm"),
    _tree(40, 10, "chinese_elm"),
    _tree(55, 12, "chinese_elm"),
    _tree(30, 5, "coast_live_oak"),
    _tree(48, 35, "valley_oak"),

    # === A/B BUILDING AREA (NE, new buildings) ===
    _tree(65, 50, "sycamore"),
    _tree(75, 55, "sycamore"),
    _tree(85, 48, "sycamore"),
    _tree(70, 42, "sycamore"),
    _tree(90, 52, "valley_oak"),
    _tree(60, 58, "coast_live_oak"),
    _tree(80, 60, "coast_live_oak"),

    # === D-LIBRARY / BG AREA (East) ===
    _tree(70, 20, "valley_oak"),
    _tree(80, 15, "coast_live_oak"),
    _tree(75, 5, "valley_oak"),
    _tree(85, 10, "coast_live_oak"),
    _tree(90, 25, "pine"),
    _tree(95, 18, "pine"),
    _tree(65, 0, "chinese_elm"),
    _tree(80, -5, "chinese_elm"),

    # === F-BUILDING / S-BUILDING AREA (SW) ===
    _tree(-55, 5, "valley_oak"),
    _tree(-65, 0, "coast_live_oak"),
    _tree(-50, -8, "valley_oak"),
    _tree(-70, -10, "coast_live_oak"),
    _tree(-60, -18, "olive"),
    _tree(-48, -15, "olive"),
    _tree(-55, -25, "olive"),

    # === P-BUILDING AREA (South-Central) ===
    _tree(-20, -20, "valley_oak"),
    _tree(-10, -25, "coast_live_oak"),
    _tree(5, -22, "valley_oak"),
    _tree(-30, -30, "coast_live_oak"),
    _tree(15, -28, "chinese_elm"),
    _tree(-5, -35, "chinese_elm"),

    # === TITAN GYM / BG AREA (South) ===
    _tree(20, -40, "valley_oak"),
    _tree(35, -38, "coast_live_oak"),
    _tree(50, -35, "valley_oak"),
    _tree(25, -50, "pine"),
    _tree(40, -48, "pine"),
    _tree(55, -42, "pine"),
    _tree(10, -48, "cedar"),
    _tree(-5, -50, "cedar"),

    # === EAST BOUNDARY - scattered trees ===
    _tree(100, 35, "redwood"),
    _tree(105, 25, "redwood"),
    _tree(100, 10, "redwood"),
    _tree(105, -5, "redwood"),
    _tree(100, -20, "valley_oak"),
    _tree(95, -35, "coast_live_oak"),

    # === SOUTH CAMPUS - between buildings and fields ===
    _tree(-80, -35, "valley_oak"),
    _tree(-90, -30, "coast_live_oak"),
    _tree(-85, -45, "valley_oak"),
    _tree(-75, -50, "coast_live_oak"),
    _tree(65, -30, "valley_oak"),
    _tree(75, -25, "cedar"),
    _tree(80, -35, "cedar"),

    # === NW AREA - near custodial/M buildings ===
    _tree(-85, 60, "valley_oak"),
    _tree(-90, 50, "coast_live_oak"),
    _tree(-80, 55, "pine"),
    _tree(-95, 55, "eucalyptus"),

    # === WALNUT TREES (rare, S-Central per survey) ===
    _tree(60, -15, "california_black_walnut"),
    _tree(55, -20, "california_black_walnut"),

    # === CEDAR CLUSTERS ===
    _tree(-30, 40, "cedar"),
    _tree(-15, 45, "cedar"),
    _tree(25, 45, "cedar"),
    _tree(40, 42, "cedar"),
    _tree(-40, -5, "cedar"),
    _tree(-25, 0, "cedar"),

    # === ATHLETIC FIELDS (South) - Perennial Grass ===
    # Large open area south of buildings
    _tree(-80, -70, "perennial_grass"),
    _tree(-50, -70, "perennial_grass"),
    _tree(-20, -70, "perennial_grass"),
    _tree(10, -70, "perennial_grass"),
    _tree(40, -70, "perennial_grass"),
    _tree(70, -70, "perennial_grass"),
    _tree(-65, -85, "perennial_grass"),
    _tree(-30, -85, "perennial_grass"),
    _tree(5, -85, "perennial_grass"),
    _tree(40, -85, "perennial_grass"),
    _tree(70, -85, "perennial_grass"),
    _tree(-50, -100, "perennial_grass"),
    _tree(-15, -100, "perennial_grass"),
    _tree(20, -100, "perennial_grass"),
    _tree(55, -100, "perennial_grass"),
]

# ============================================================
# CAMPUS BUILDINGS - From Gunn Site Map 2025-26
# All buildings are in the NORTHERN portion of campus (y > -20).
# Athletic fields are south of y = -50 (no buildings there).
# Buildings are smaller than you'd think; dimensions are reduced for accuracy.
# ============================================================
CAMPUS_BUILDINGS = GUNN_BUILDINGS = [
    {"building_id": "a_building", "name": "A-Bldg",
     "height": 12.0, "width": 20.0, "length": 35.0, "local_x": 55.0, "local_y": 50.0,
     "aerodynamic_fraction": 0.6,
     "lat": local_to_latlng(55, 50)[0], "lng": local_to_latlng(55, 50)[1]},
    {"building_id": "b_building", "name": "B-Bldg",
     "height": 12.0, "width": 18.0, "length": 30.0, "local_x": 75.0, "local_y": 40.0,
     "aerodynamic_fraction": 0.6,
     "lat": local_to_latlng(75, 40)[0], "lng": local_to_latlng(75, 40)[1]},
    {"building_id": "j_building", "name": "J-Bldg",
     "height": 9.0, "width": 15.0, "length": 40.0, "local_x": -55.0, "local_y": 55.0,
     "aerodynamic_fraction": 0.6,
     "lat": local_to_latlng(-55, 55)[0], "lng": local_to_latlng(-55, 55)[1]},
    {"building_id": "n_wing", "name": "N-Bldg",
     "height": 8.0, "width": 12.0, "length": 50.0, "local_x": 0.0, "local_y": 20.0,
     "aerodynamic_fraction": 0.65,
     "lat": local_to_latlng(0, 20)[0], "lng": local_to_latlng(0, 20)[1]},
    {"building_id": "k_building", "name": "K-Bldg",
     "height": 8.0, "width": 12.0, "length": 30.0, "local_x": 30.0, "local_y": 20.0,
     "aerodynamic_fraction": 0.6,
     "lat": local_to_latlng(30, 20)[0], "lng": local_to_latlng(30, 20)[1]},
    {"building_id": "g_building", "name": "G-Bldg",
     "height": 8.0, "width": 12.0, "length": 25.0, "local_x": 42.0, "local_y": 30.0,
     "aerodynamic_fraction": 0.6,
     "lat": local_to_latlng(42, 30)[0], "lng": local_to_latlng(42, 30)[1]},
    {"building_id": "h_building", "name": "H-Bldg",
     "height": 8.0, "width": 10.0, "length": 25.0, "local_x": 20.0, "local_y": 30.0,
     "aerodynamic_fraction": 0.6,
     "lat": local_to_latlng(20, 30)[0], "lng": local_to_latlng(20, 30)[1]},
    {"building_id": "f_building", "name": "F-Bldg",
     "height": 8.0, "width": 12.0, "length": 35.0, "local_x": -55.0, "local_y": 10.0,
     "aerodynamic_fraction": 0.6,
     "lat": local_to_latlng(-55, 10)[0], "lng": local_to_latlng(-55, 10)[1]},
    {"building_id": "p_building", "name": "P-Bldg",
     "height": 8.0, "width": 14.0, "length": 28.0, "local_x": -20.0, "local_y": -5.0,
     "aerodynamic_fraction": 0.6,
     "lat": local_to_latlng(-20, -5)[0], "lng": local_to_latlng(-20, -5)[1]},
    {"building_id": "d_library", "name": "D-Bldg/Library",
     "height": 7.0, "width": 18.0, "length": 28.0, "local_x": 65.0, "local_y": 15.0,
     "aerodynamic_fraction": 0.65,
     "lat": local_to_latlng(65, 15)[0], "lng": local_to_latlng(65, 15)[1]},
    {"building_id": "spangenberg", "name": "Spangenberg",
     "height": 14.0, "width": 25.0, "length": 35.0, "local_x": -95.0, "local_y": 30.0,
     "aerodynamic_fraction": 0.5,
     "lat": local_to_latlng(-95, 30)[0], "lng": local_to_latlng(-95, 30)[1]},
    {"building_id": "titan_gym", "name": "Titan Gym",
     "height": 12.0, "width": 25.0, "length": 40.0, "local_x": 25.0, "local_y": -20.0,
     "aerodynamic_fraction": 0.55,
     "lat": local_to_latlng(25, -20)[0], "lng": local_to_latlng(25, -20)[1]},
]

# ============================================================
# STUDENT PATHS
# ============================================================
STUDENT_PATHS = GUNN_PATHS = [
    {"name": "P-Building to Titan Gym",
     "waypoints": [{"x": -15, "y": -30}, {"x": 0, "y": -35}, {"x": 15, "y": -40}, {"x": 30, "y": -45}]},
    {"name": "A-Building to Athletic Fields",
     "waypoints": [{"x": 70, "y": 45}, {"x": 55, "y": 25}, {"x": 40, "y": 5}, {"x": 25, "y": -20}, {"x": 10, "y": -50}, {"x": 0, "y": -70}]},
    {"name": "J-Building to K-Building",
     "waypoints": [{"x": -55, "y": 50}, {"x": -30, "y": 35}, {"x": -5, "y": 25}, {"x": 15, "y": 18}, {"x": 35, "y": 15}]},
    {"name": "Main Entrance to Spangenberg",
     "waypoints": [{"x": 0, "y": 80}, {"x": -25, "y": 60}, {"x": -55, "y": 40}, {"x": -80, "y": 30}, {"x": -95, "y": 25}]},
    {"name": "N-Building to D-Library",
     "waypoints": [{"x": 0, "y": 15}, {"x": 20, "y": 12}, {"x": 40, "y": 10}, {"x": 55, "y": 8}, {"x": 70, "y": 5}]},
]


# ============================================================
# STANFORD - MAIN QUAD
# Center on the Main Quad / Memorial Court area.
# ============================================================
STANFORD_CENTER_LAT = 37.4275
STANFORD_CENTER_LON = -122.1697
_stanford_local = _make_local_to_latlng(STANFORD_CENTER_LAT, STANFORD_CENTER_LON)


def _stree(x: float, y: float, species_key: str) -> dict:
    lat, lng = _stanford_local(x, y)
    return {"x": x, "y": y, "species_key": species_key, "lat": lat, "lng": lng}


# Satellite-image bounds for Stanford. Widened to capture the full core campus
# plus surrounding areas (about 2.4 km E-W x 2.1 km N-S), centered on the Quad.
STANFORD_BOUNDS = {
    "north": STANFORD_CENTER_LAT + 0.0095,
    "south": STANFORD_CENTER_LAT - 0.0095,
    "east": STANFORD_CENTER_LON + 0.0137,
    "west": STANFORD_CENTER_LON - 0.0137,
}

# Boundary: axis-aligned rectangle around the Main Quad (no rotation).
STANFORD_BOUNDARY = _rotated_rect_boundary(
    STANFORD_CENTER_LAT, STANFORD_CENTER_LON, 0.0030, 0.0021, 0
)

# Fallback flora for Stanford Main Quad. Real per-tree data is produced by
# satellite detection at runtime; this set keeps the dispersion model meaningful
# before/without detection. Notable: the Palm Drive Canary Island date palms,
# coast live oaks around the Oval, and mixed canopy around the Quad.
STANFORD_TREES = [
    # Palm Drive approach (north, running toward Memorial Court)
    _stree(-6, 210, "palm"),
    _stree(6, 210, "palm"),
    _stree(-6, 190, "palm"),
    _stree(6, 190, "palm"),
    _stree(-6, 170, "palm"),
    _stree(6, 170, "palm"),
    _stree(-6, 150, "palm"),
    _stree(6, 150, "palm"),

    # The Oval (north entrance lawn) - ring of coast live oaks
    _stree(-45, 175, "coast_live_oak"),
    _stree(45, 175, "coast_live_oak"),
    _stree(-55, 150, "coast_live_oak"),
    _stree(55, 150, "coast_live_oak"),
    _stree(-40, 130, "valley_oak"),
    _stree(40, 130, "valley_oak"),

    # Memorial Court / around the Quad (central)
    _stree(-70, 40, "coast_live_oak"),
    _stree(70, 40, "coast_live_oak"),
    _stree(-80, 10, "valley_oak"),
    _stree(80, 10, "valley_oak"),
    _stree(-75, -25, "coast_live_oak"),
    _stree(75, -25, "coast_live_oak"),
    _stree(-60, -55, "redwood"),
    _stree(60, -55, "redwood"),

    # Redwood/eucalyptus clusters flanking the Quad (west/east edges)
    _stree(-140, 60, "redwood"),
    _stree(-145, 20, "redwood"),
    _stree(-150, -20, "redwood"),
    _stree(140, 60, "eucalyptus"),
    _stree(145, 20, "eucalyptus"),
    _stree(150, -20, "eucalyptus"),

    # South of the Quad toward the science area - oaks and elms
    _stree(-30, -90, "coast_live_oak"),
    _stree(30, -90, "coast_live_oak"),
    _stree(-10, -110, "chinese_elm"),
    _stree(10, -110, "chinese_elm"),
    _stree(-50, -120, "valley_oak"),
    _stree(50, -120, "valley_oak"),

    # Scattered central canopy
    _stree(-20, 60, "sycamore"),
    _stree(20, 60, "sycamore"),
    _stree(0, 90, "coast_live_oak"),
    _stree(0, -30, "valley_oak"),

    # Lawn areas (grass sources)
    _stree(-100, 130, "perennial_grass"),
    _stree(100, 130, "perennial_grass"),
    _stree(-100, 160, "perennial_grass"),
    _stree(100, 160, "perennial_grass"),
]

# Stanford Main Quad buildings (approximate footprints of the sandstone quad,
# Memorial Church, and flanking halls). Local meters from the Quad center.
STANFORD_BUILDINGS = [
    {"building_id": "memorial_church", "name": "Memorial Church",
     "height": 26.0, "width": 40.0, "length": 55.0, "local_x": 0.0, "local_y": -20.0,
     "aerodynamic_fraction": 0.5,
     "lat": _stanford_local(0, -20)[0], "lng": _stanford_local(0, -20)[1]},
    {"building_id": "main_quad_w", "name": "Main Quad (West)",
     "height": 12.0, "width": 18.0, "length": 90.0, "local_x": -60.0, "local_y": 0.0,
     "aerodynamic_fraction": 0.6,
     "lat": _stanford_local(-60, 0)[0], "lng": _stanford_local(-60, 0)[1]},
    {"building_id": "main_quad_e", "name": "Main Quad (East)",
     "height": 12.0, "width": 18.0, "length": 90.0, "local_x": 60.0, "local_y": 0.0,
     "aerodynamic_fraction": 0.6,
     "lat": _stanford_local(60, 0)[0], "lng": _stanford_local(60, 0)[1]},
    {"building_id": "main_quad_s", "name": "Main Quad (South Row)",
     "height": 12.0, "width": 90.0, "length": 16.0, "local_x": 0.0, "local_y": -50.0,
     "aerodynamic_fraction": 0.6,
     "lat": _stanford_local(0, -50)[0], "lng": _stanford_local(0, -50)[1]},
    {"building_id": "memorial_court", "name": "Memorial Court Arcade",
     "height": 10.0, "width": 90.0, "length": 14.0, "local_x": 0.0, "local_y": 50.0,
     "aerodynamic_fraction": 0.6,
     "lat": _stanford_local(0, 50)[0], "lng": _stanford_local(0, 50)[1]},
    {"building_id": "hoover_tower", "name": "Hoover Tower",
     "height": 87.0, "width": 20.0, "length": 20.0, "local_x": 130.0, "local_y": -70.0,
     "aerodynamic_fraction": 0.4,
     "lat": _stanford_local(130, -70)[0], "lng": _stanford_local(130, -70)[1]},
]

STANFORD_PATHS = [
    {"name": "Palm Drive to Main Quad",
     "waypoints": [{"x": 0, "y": 210}, {"x": 0, "y": 150}, {"x": 0, "y": 90}, {"x": 0, "y": 50}, {"x": 0, "y": 0}]},
    {"name": "Oval to Memorial Church",
     "waypoints": [{"x": 0, "y": 175}, {"x": 0, "y": 100}, {"x": 0, "y": 30}, {"x": 0, "y": -20}]},
    {"name": "West Quad to East Quad",
     "waypoints": [{"x": -60, "y": 0}, {"x": -30, "y": 0}, {"x": 0, "y": 0}, {"x": 30, "y": 0}, {"x": 60, "y": 0}]},
    {"name": "Main Quad to Hoover Tower",
     "waypoints": [{"x": 0, "y": 0}, {"x": 40, "y": -20}, {"x": 80, "y": -45}, {"x": 130, "y": -70}]},
    {"name": "Memorial Court to Science Quad",
     "waypoints": [{"x": 0, "y": 50}, {"x": 0, "y": 0}, {"x": 0, "y": -50}, {"x": 0, "y": -100}, {"x": 0, "y": -120}]},
]


# ============================================================
# CAMPUS REGISTRY
# ============================================================
CAMPUSES = {
    "gunn": {
        "key": "gunn",
        "name": "Gunn High School",
        "subtitle": "Palo Alto, CA",
        "center_lat": GUNN_CENTER_LAT,
        "center_lon": GUNN_CENTER_LON,
        "bounds": {"north": 37.4038, "south": 37.3988, "east": -122.1300, "west": -122.1372},
        "boundary": GUNN_BOUNDARY,
        "trees": GUNN_TREES,
        "buildings": GUNN_BUILDINGS,
        "paths": GUNN_PATHS,
    },
    "stanford": {
        "key": "stanford",
        "name": "Stanford University",
        "subtitle": "Main Quad, Stanford, CA",
        "center_lat": STANFORD_CENTER_LAT,
        "center_lon": STANFORD_CENTER_LON,
        "bounds": STANFORD_BOUNDS,
        "boundary": STANFORD_BOUNDARY,
        "trees": STANFORD_TREES,
        "buildings": STANFORD_BUILDINGS,
        "paths": STANFORD_PATHS,
    },
}

DEFAULT_CAMPUS = "gunn"


def get_campus(key: str) -> dict:
    """Return the campus record for key, falling back to the default campus."""
    return CAMPUSES.get((key or "").lower(), CAMPUSES[DEFAULT_CAMPUS])
