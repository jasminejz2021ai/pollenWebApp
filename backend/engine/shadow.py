"""
Campus AeroAllergen Mapping (CAM) - Spatial Shadow Engine

Computes building wake zones and wind shadow matrices for
aerodynamic obstruction modeling on campus grid.
"""

import numpy as np
from typing import List, Dict, Tuple


def compute_wake_footprint(
    building: Dict,
    wind_dir_deg: float,
    grid_x: np.ndarray,
    grid_y: np.ndarray,
) -> np.ndarray:
    """
    Compute binary wake mask M_wake for a single building.
    M_wake(x,y) = 1 if point falls within geometric wake footprint.

    Wake extends 3*H_b downwind and W_b wide from building rear.
    """
    bx, by = building["x"], building["y"]
    bw = building["width"]
    bh = building["height"]
    bl = building["length"]

    theta = np.radians(270.0 - wind_dir_deg)
    ux = np.cos(theta)
    uy = np.sin(theta)

    dx = grid_x - bx
    dy = grid_y - by

    x_prime = dx * ux + dy * uy
    y_prime = -dx * uy + dy * ux

    wake_length = 3.0 * bh
    half_width = bw / 2.0

    mask = (
        (x_prime > 0)
        & (x_prime < wake_length)
        & (np.abs(y_prime) < half_width)
    )
    return mask.astype(np.float64)


def compute_full_shadow_matrix(
    buildings: List[Dict],
    wind_dir_deg: float,
    grid_x: np.ndarray,
    grid_y: np.ndarray,
) -> np.ndarray:
    """
    Compute combined wake shadow matrix for all campus buildings.
    Returns M_wake where values > 0 indicate shadow zones.
    """
    shadow = np.zeros_like(grid_x, dtype=np.float64)
    for bldg in buildings:
        shadow += compute_wake_footprint(bldg, wind_dir_deg, grid_x, grid_y)
    return np.clip(shadow, 0, 1)


def apply_wake_damping(
    wind_u: float,
    wind_v: float,
    deposition_rate: float,
    wake_matrix: np.ndarray,
    velocity_damping: float = 0.4,
    deposition_multiplier: float = 2.5,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Apply aerodynamic damping in wake zones:
    - Wind velocity reduced by up to 60% (damping=0.4 means 40% retained)
    - Deposition rate increased by 2.5x

    Returns (u_field, v_field, lambda_field) as 2D arrays.
    """
    u_field = np.full_like(wake_matrix, wind_u)
    v_field = np.full_like(wake_matrix, wind_v)
    lambda_field = np.full_like(wake_matrix, deposition_rate)

    in_wake = wake_matrix > 0.5
    u_field[in_wake] *= velocity_damping
    v_field[in_wake] *= velocity_damping
    lambda_field[in_wake] *= deposition_multiplier

    return u_field, v_field, lambda_field
