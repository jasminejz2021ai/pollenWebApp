"""
Campus AeroAllergen Mapping (CAM) - Campus Data

Gunn High School (780 Arastradero Rd, Palo Alto, CA 94306)
Center: 37.4027°N, 122.1342°W

Tree positions placed by matching visible canopy on satellite imagery.
Building positions from Gunn Site Map 2025-26.
Boundary traced from property outline.
"""

import numpy as np
from typing import Tuple, List

CAMPUS_CENTER_LAT = 37.4027
CAMPUS_CENTER_LON = -122.1342
METERS_PER_DEG_LAT = 111320.0
METERS_PER_DEG_LON = 111320.0 * np.cos(np.radians(CAMPUS_CENTER_LAT))


def local_to_latlng(x: float, y: float) -> Tuple[float, float]:
    """Convert local meter coordinates (origin=campus center) to lat/lng."""
    lat = CAMPUS_CENTER_LAT + y / METERS_PER_DEG_LAT
    lng = CAMPUS_CENTER_LON + x / METERS_PER_DEG_LON
    return round(lat, 7), round(lng, 7)


def _tree(x: float, y: float, species_key: str) -> dict:
    lat, lng = local_to_latlng(x, y)
    return {"x": x, "y": y, "species_key": species_key, "lat": lat, "lng": lng}


# ============================================================
# CAMPUS BOUNDARY - Rectangle rotated 25° to align with Arastradero Rd
# Arastradero runs ENE-WSW at roughly 25° from east
# ============================================================
def _rotate_point(cx, cy, x, y, angle_deg):
    """Rotate point (x,y) around (cx,cy) by angle_deg."""
    import math
    rad = math.radians(angle_deg)
    dx, dy = x - cx, y - cy
    rx = dx * math.cos(rad) - dy * math.sin(rad)
    ry = dx * math.sin(rad) + dy * math.cos(rad)
    return (round(cy + ry, 6), round(cx + rx, 6))

_center_lat = 37.4018
_center_lng = -122.1338
_half_w = 0.0032  # half-width in lng degrees
_half_h = 0.0022  # half-height in lat degrees
_angle = 25  # degrees counterclockwise to match Arastradero tilt

# Build rotated rectangle corners
_corners_unrotated = [
    (_center_lng - _half_w, _center_lat - _half_h),
    (_center_lng + _half_w, _center_lat - _half_h),
    (_center_lng + _half_w, _center_lat + _half_h),
    (_center_lng - _half_w, _center_lat + _half_h),
]

CAMPUS_BOUNDARY: List[Tuple[float, float]] = []
for (lng, lat) in _corners_unrotated:
    rlat, rlng = _rotate_point(_center_lng, _center_lat, lng, lat, _angle)
    CAMPUS_BOUNDARY.append((rlat, rlng))
CAMPUS_BOUNDARY.append(CAMPUS_BOUNDARY[0])  # close polygon

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

CAMPUS_TREES = [
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
CAMPUS_BUILDINGS = [
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
STUDENT_PATHS = [
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
