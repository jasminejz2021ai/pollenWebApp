"""
Campus AeroAllergen Mapping (CAM) - Path Integration Engine

Calculates cumulative pollen exposure dose along student transit paths
using numerical path integration: D = ∫_γ C_total(x,y,t) dt
"""

import numpy as np
from typing import List, Tuple, Dict


def path_exposure_dose(
    path_points: List[Tuple[float, float]],
    concentration_grid: np.ndarray,
    grid_x: np.ndarray,
    grid_y: np.ndarray,
    walking_speed: float = 1.4,
) -> Dict:
    """
    Calculate cumulative exposure dose along a student walking path.

    D = ∫_γ C_total(x,y,t) dt ≈ Σ C(x_i, y_i) · Δt_i

    Parameters:
        path_points: List of (x,y) coordinates along path
        concentration_grid: 2D pollen concentration field
        grid_x, grid_y: Coordinate meshgrids
        walking_speed: Average student walking speed (m/s), default 1.4 m/s

    Returns dict with total_dose, max_concentration, segment_doses, risk_level
    """
    if len(path_points) < 2:
        return {"total_dose": 0, "max_concentration": 0, "segment_doses": [], "risk_level": "low"}

    x_vals = grid_x[0, :]
    y_vals = grid_y[:, 0]

    total_dose = 0.0
    max_conc = 0.0
    segment_doses = []

    for i in range(len(path_points) - 1):
        x1, y1 = path_points[i]
        x2, y2 = path_points[i + 1]

        segment_length = np.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)
        dt = segment_length / walking_speed

        mid_x = (x1 + x2) / 2.0
        mid_y = (y1 + y2) / 2.0

        ix = np.argmin(np.abs(x_vals - mid_x))
        iy = np.argmin(np.abs(y_vals - mid_y))

        ix = np.clip(ix, 0, concentration_grid.shape[1] - 1)
        iy = np.clip(iy, 0, concentration_grid.shape[0] - 1)

        local_conc = concentration_grid[iy, ix]
        segment_dose = local_conc * dt

        total_dose += segment_dose
        max_conc = max(max_conc, local_conc)
        segment_doses.append({
            "from": path_points[i],
            "to": path_points[i + 1],
            "concentration": round(float(local_conc), 2),
            "dose": round(float(segment_dose), 4),
            "duration_s": round(float(dt), 2),
        })

    risk_level = dose_to_risk_level(total_dose)

    return {
        "total_dose": round(float(total_dose), 4),
        "max_concentration": round(float(max_conc), 2),
        "segment_doses": segment_doses,
        "risk_level": risk_level,
        "path_length_m": round(sum(
            np.sqrt((p2[0] - p1[0])**2 + (p2[1] - p1[1])**2)
            for p1, p2 in zip(path_points[:-1], path_points[1:])
        ), 1),
        "transit_time_s": round(sum(
            np.sqrt((p2[0] - p1[0])**2 + (p2[1] - p1[1])**2) / walking_speed
            for p1, p2 in zip(path_points[:-1], path_points[1:])
        ), 1),
    }


def dose_to_risk_level(dose: float) -> str:
    """Map cumulative dose to clinical risk level."""
    if dose < 50:
        return "low"
    elif dose < 200:
        return "moderate"
    elif dose < 500:
        return "high"
    else:
        return "very_high"


def find_lowest_exposure_path(
    start: Tuple[float, float],
    end: Tuple[float, float],
    concentration_grid: np.ndarray,
    grid_x: np.ndarray,
    grid_y: np.ndarray,
    num_waypoints: int = 5,
) -> List[Tuple[float, float]]:
    """
    Simple path optimization: find a lower-exposure route by sampling
    lateral offsets from the direct path and choosing minimum dose waypoints.
    """
    x_vals = grid_x[0, :]
    y_vals = grid_y[:, 0]

    dx = end[0] - start[0]
    dy = end[1] - start[1]
    path_length = np.sqrt(dx**2 + dy**2)

    ux, uy = dx / path_length, dy / path_length
    nx, ny = -uy, ux  # normal vector

    optimized_path = [start]
    offsets = np.linspace(-30, 30, 7)

    for k in range(1, num_waypoints + 1):
        t = k / (num_waypoints + 1)
        base_x = start[0] + t * dx
        base_y = start[1] + t * dy

        best_offset = 0
        min_conc = float("inf")

        for offset in offsets:
            test_x = base_x + offset * nx
            test_y = base_y + offset * ny

            ix = np.argmin(np.abs(x_vals - test_x))
            iy = np.argmin(np.abs(y_vals - test_y))
            ix = np.clip(ix, 0, concentration_grid.shape[1] - 1)
            iy = np.clip(iy, 0, concentration_grid.shape[0] - 1)

            conc = concentration_grid[iy, ix]
            if conc < min_conc:
                min_conc = conc
                best_offset = offset

        optimized_path.append((
            base_x + best_offset * nx,
            base_y + best_offset * ny,
        ))

    optimized_path.append(end)
    return optimized_path
