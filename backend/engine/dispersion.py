"""
Campus AeroAllergen Mapping (CAM) - Core Dispersion Engine

Implements:
- Gaussian Plume Model for pollen transport
- Advection-Diffusion steady-state solutions
- Building wake/downwash modifications (Schulman-Scire)
- Multi-source linear superposition
- Pasquill-Gifford stability parameters
"""

import numpy as np
from scipy.special import erf
from typing import Tuple, Optional


# Pasquill-Gifford dispersion coefficients for stability classes A-F
# Format: (a_y, b_y, a_z, b_z) where sigma = a * x^b
PG_COEFFICIENTS = {
    "A": (0.22, 0.894, 0.20, 0.894),
    "B": (0.16, 0.894, 0.12, 0.894),
    "C": (0.11, 0.894, 0.08, 0.894),
    "D": (0.08, 0.894, 0.06, 0.894),
    "E": (0.06, 0.894, 0.03, 0.894),
    "F": (0.04, 0.894, 0.016, 0.894),
}


def wind_components(speed: float, direction_deg: float) -> Tuple[float, float]:
    """
    Convert meteorological wind speed and direction to u,v grid components.
    Direction is degrees from true North (meteorological convention).
    """
    theta_rad = np.radians(270.0 - direction_deg)
    u = speed * np.cos(theta_rad)
    v = speed * np.sin(theta_rad)
    return u, v


def dispersion_sigmas(
    x_downwind: np.ndarray, stability_class: str = "D"
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Compute Pasquill-Gifford crosswind and vertical dispersion coefficients.
    Returns sigma_y, sigma_z as arrays matching x_downwind shape.
    """
    a_y, b_y, a_z, b_z = PG_COEFFICIENTS[stability_class]
    x_safe = np.maximum(x_downwind, 1.0)
    sigma_y = a_y * np.power(x_safe, b_y)
    sigma_z = a_z * np.power(x_safe, b_z)
    return sigma_y, sigma_z


def gaussian_plume(
    x_grid: np.ndarray,
    y_grid: np.ndarray,
    source_x: float,
    source_y: float,
    emission_rate: float,
    wind_speed: float,
    wind_dir_deg: float,
    source_height: float = 5.0,
    receptor_height: float = 1.5,
    stability_class: str = "D",
) -> np.ndarray:
    """
    Steady-state Gaussian plume concentration at receptor grid points.

    C(x,y) = Q / (2π·u·σ_y·σ_z) * exp(-y'^2 / 2σ_y^2) *
             [exp(-(z-H)^2 / 2σ_z^2) + exp(-(z+H)^2 / 2σ_z^2)]

    Parameters:
        x_grid, y_grid: 2D coordinate meshgrids (meters)
        source_x, source_y: Source location (meters)
        emission_rate: Q in grains/second
        wind_speed: m/s
        wind_dir_deg: degrees from North
        source_height: effective emission height (m)
        receptor_height: breathing zone height (m), default 1.5m
        stability_class: Pasquill-Gifford class A-F
    """
    if wind_speed < 0.5:
        wind_speed = 0.5

    u, v = wind_components(wind_speed, wind_dir_deg)
    wind_mag = np.sqrt(u**2 + v**2)

    # Wind unit vector
    ux, uy = u / wind_mag, v / wind_mag

    # Translate grid relative to source
    dx = x_grid - source_x
    dy = y_grid - source_y

    # Rotate coordinates into wind-aligned frame
    x_prime = dx * ux + dy * uy  # downwind distance
    y_prime = -dx * uy + dy * ux  # crosswind distance

    # Only compute where downwind > 0
    concentration = np.zeros_like(x_grid, dtype=float)
    mask = x_prime > 1.0

    if not np.any(mask):
        return concentration

    sigma_y, sigma_z = dispersion_sigmas(x_prime[mask], stability_class)

    # Gaussian plume formula
    z = receptor_height
    H = source_height

    lateral = np.exp(-0.5 * (y_prime[mask] ** 2) / (sigma_y**2))
    vertical = np.exp(-0.5 * ((z - H) ** 2) / (sigma_z**2)) + np.exp(
        -0.5 * ((z + H) ** 2) / (sigma_z**2)
    )

    denom = 2.0 * np.pi * wind_mag * sigma_y * sigma_z
    concentration[mask] = (emission_rate / denom) * lateral * vertical

    return concentration


def building_modified_sigmas(
    sigma_y: np.ndarray,
    sigma_z: np.ndarray,
    building_width: float,
    building_height: float,
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Apply Schulman-Scire building downwash modifications:
    σ_y' = sqrt(σ_y² + W_b² / 4π)
    σ_z' = sqrt(σ_z² + H_b² / 4π)
    """
    sigma_y_mod = np.sqrt(sigma_y**2 + (building_width**2) / (4.0 * np.pi))
    sigma_z_mod = np.sqrt(sigma_z**2 + (building_height**2) / (4.0 * np.pi))
    return sigma_y_mod, sigma_z_mod


def cavity_concentration(
    emission_rate: float,
    wind_speed: float,
    building_height: float,
    building_width: float,
    aerodynamic_fraction: float = 0.6,
    max_concentration: float = None,
) -> float:
    """
    Uniform cavity concentration for near-wake zone (x' <= 3·H_b):
    C_cavity = Q / (B_e · H_b · W_b · u)

    The result is clamped to max_concentration when provided. This guards
    against unrealistically large values when the assumed building height is
    small (H_b appears in the denominator), which otherwise lets many stacked
    cavity zones produce non-physical peaks.
    """
    if wind_speed < 0.5:
        wind_speed = 0.5
    # Enforce a minimum effective height so a small assumed height cannot make
    # the cavity concentration diverge.
    h_eff = max(building_height, 5.0)
    c = emission_rate / (aerodynamic_fraction * h_eff * building_width * wind_speed)
    if max_concentration is not None:
        c = min(c, max_concentration)
    return c


def gaussian_plume_with_downwash(
    x_grid: np.ndarray,
    y_grid: np.ndarray,
    source_x: float,
    source_y: float,
    emission_rate: float,
    wind_speed: float,
    wind_dir_deg: float,
    buildings: list,
    source_height: float = 5.0,
    receptor_height: float = 1.5,
    stability_class: str = "D",
    cavity_cap: float = 500.0,
) -> np.ndarray:
    """
    Gaussian plume with building wake modifications.
    Buildings is a list of dicts with keys:
        x, y, width, height, length, polygon (optional)
    """
    if wind_speed < 0.5:
        wind_speed = 0.5

    u, v = wind_components(wind_speed, wind_dir_deg)
    wind_mag = np.sqrt(u**2 + v**2)
    ux, uy = u / wind_mag, v / wind_mag

    dx = x_grid - source_x
    dy = y_grid - source_y
    x_prime = dx * ux + dy * uy
    y_prime = -dx * uy + dy * ux

    concentration = np.zeros_like(x_grid, dtype=float)
    mask = x_prime > 1.0

    if not np.any(mask):
        return concentration

    sigma_y, sigma_z = dispersion_sigmas(x_prime[mask], stability_class)

    # Track, per grid point, whether it lies in ANY building's near-wake cavity
    # and the cavity concentration of the building responsible for it. Each
    # building writes only its own wake zone (nearest wins on overlap), so the
    # distance from each nearby building governs where its cavity applies.
    n_masked = int(np.sum(mask))
    wake_mask = np.zeros(n_masked, dtype=bool)
    cavity_value = np.zeros(n_masked, dtype=float)
    x_masked = x_prime[mask]
    y_masked = y_prime[mask]

    for bldg in buildings:
        bx, by = bldg["x"], bldg["y"]
        bw, bh = bldg["width"], bldg["height"]

        # Building position in the wind-aligned frame relative to this source
        bdx = bx - source_x
        bdy = by - source_y
        bx_prime = bdx * ux + bdy * uy
        by_prime = -bdx * uy + bdy * ux

        # Near-wake cavity: within 3*H_b downwind of the building and within
        # half its width crosswind.
        in_wake = (
            (x_masked > bx_prime)
            & (x_masked < bx_prime + 3.0 * bh)
            & (np.abs(y_masked - by_prime) < bw / 2.0)
        )
        if np.any(in_wake):
            # Cap the cavity value at the calibrated spring-peak reference so a
            # small assumed building height cannot produce a peak larger than
            # the model's open-field maximum (a cavity dilutes, not concentrates
            # beyond the source field).
            c_cav = cavity_concentration(
                emission_rate, wind_speed, bh, bw,
                max_concentration=cavity_cap,
            )
            cavity_value[in_wake] = np.maximum(cavity_value[in_wake], c_cav)
            wake_mask |= in_wake

        # Schulman-Scire dispersion inflation in the near-building zone (out to
        # 10*H_b downwind) outside the cavity.
        near_building = (
            (x_masked > bx_prime)
            & (x_masked < bx_prime + 10.0 * bh)
            & (~in_wake)
        )
        if np.any(near_building):
            sigma_y[near_building], sigma_z[near_building] = building_modified_sigmas(
                sigma_y[near_building], sigma_z[near_building], bw, bh
            )

    z = receptor_height
    H = source_height

    lateral = np.exp(-0.5 * (y_prime[mask] ** 2) / (sigma_y**2))
    vertical = np.exp(-0.5 * ((z - H) ** 2) / (sigma_z**2)) + np.exp(
        -0.5 * ((z + H) ** 2) / (sigma_z**2)
    )

    denom = 2.0 * np.pi * wind_mag * sigma_y * sigma_z
    plume_values = (emission_rate / denom) * lateral * vertical

    # Override cavity zones with each responsible building's uniform value.
    if np.any(wake_mask):
        plume_values[wake_mask] = cavity_value[wake_mask]

    concentration[mask] = plume_values
    return concentration


def superpose_sources(
    x_grid: np.ndarray,
    y_grid: np.ndarray,
    flora_matrix: np.ndarray,
    wind_speed: float,
    wind_dir_deg: float,
    buildings: list,
    current_day: int,
    stability_class: str = "D",
    receptor_height: float = 1.5,
) -> np.ndarray:
    """
    Linear superposition of all active pollen sources.
    C_total(x,y) = Σ C_i(x,y)

    flora_matrix: N×8 array with columns:
        [x, y, Q_base, potency_weight, start_day, end_day, peak_day, sigma_t]
    """
    total_concentration = np.zeros_like(x_grid, dtype=float)

    for i in range(flora_matrix.shape[0]):
        sx, sy = flora_matrix[i, 0], flora_matrix[i, 1]
        q_base = flora_matrix[i, 2]
        potency = flora_matrix[i, 3]
        start_day = int(flora_matrix[i, 4])
        end_day = int(flora_matrix[i, 5])
        peak_day = flora_matrix[i, 6]
        sigma_t = flora_matrix[i, 7]

        # Temporal gate function
        if current_day < start_day or current_day > end_day:
            continue

        gamma = np.exp(-((current_day - peak_day) ** 2) / (2.0 * sigma_t**2))
        effective_emission = q_base * potency * gamma

        if effective_emission < 0.01:
            continue

        # Source height estimated from tree type (average canopy emission)
        source_height = 6.0

        if buildings:
            # Only consider buildings near this source; a building far away has
            # no wake effect here. This turns the O(sources x buildings) inner
            # loop into O(sources x few), the key speedup for dense campuses.
            nearby = [
                b for b in buildings
                if (b["x"] - sx) ** 2 + (b["y"] - sy) ** 2 < 250.0 ** 2
            ]
            if nearby:
                c_i = gaussian_plume_with_downwash(
                    x_grid, y_grid, sx, sy,
                    effective_emission, wind_speed, wind_dir_deg,
                    nearby, source_height, receptor_height, stability_class,
                )
            else:
                c_i = gaussian_plume(
                    x_grid, y_grid, sx, sy,
                    effective_emission, wind_speed, wind_dir_deg,
                    source_height, receptor_height, stability_class,
                )
        else:
            c_i = gaussian_plume(
                x_grid, y_grid, sx, sy,
                effective_emission, wind_speed, wind_dir_deg,
                source_height, receptor_height, stability_class,
            )

        total_concentration += c_i

    return total_concentration
