"""
Campus AeroAllergen Mapping (CAM) - Core Dispersion Engine

Implements:
- Straight Gaussian plume (uniform wind)
- Segmented Gaussian plume along wind-field streamlines (NS / potential flow)
- Building wake/downwash modifications (Schulman-Scire, uniform-wind mode)
- Multi-source linear superposition
- Pasquill-Gifford stability parameters
"""

import numpy as np
from scipy.special import erf
from scipy.spatial import cKDTree
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
            # Only consider buildings close to this source; a building far away
            # has negligible wake effect here. Restricting to the nearest few
            # keeps this fast even with thousands of detected buildings.
            near = []
            for b in buildings:
                d2 = (b["x"] - sx) ** 2 + (b["y"] - sy) ** 2
                if d2 < 120.0 ** 2:
                    near.append((d2, b))
            if near:
                near.sort(key=lambda z: z[0])
                nearby = [b for _, b in near[:5]]
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


def _wind_speed_dir_from_uv(u: float, v: float):
    """Convert grid velocity components (u=+east, v=+north) back to a
    meteorological speed and direction (degrees FROM which wind blows)."""
    speed = float(np.hypot(u, v))
    # Direction the wind is blowing TOWARD, math angle:
    toward = np.degrees(np.arctan2(v, u))
    # Meteorological "from" direction: invert and convert from math to compass.
    met_from = (270.0 - toward) % 360.0
    return speed, met_from


def _sample_uv(x, y, u_field, v_field, grid_extent_x, grid_extent_y):
    """Bilinear sample of (u, v) at a point in local meters."""
    ny, nx = u_field.shape
    fx = (x + grid_extent_x) / (2.0 * grid_extent_x) * (nx - 1)
    fy = (y + grid_extent_y) / (2.0 * grid_extent_y) * (ny - 1)
    if not (np.isfinite(fx) and np.isfinite(fy)):
        return 0.0, 0.0
    if fx < 0 or fy < 0 or fx > nx - 1 or fy > ny - 1:
        return 0.0, 0.0
    i0 = int(np.floor(fy)); j0 = int(np.floor(fx))
    i1 = min(i0 + 1, ny - 1); j1 = min(j0 + 1, nx - 1)
    ty = fy - i0; tx = fx - j0
    u = (u_field[i0, j0] * (1 - tx) * (1 - ty) + u_field[i0, j1] * tx * (1 - ty)
         + u_field[i1, j0] * (1 - tx) * ty + u_field[i1, j1] * tx * ty)
    v = (v_field[i0, j0] * (1 - tx) * (1 - ty) + v_field[i0, j1] * tx * (1 - ty)
         + v_field[i1, j0] * (1 - tx) * ty + v_field[i1, j1] * tx * ty)
    return float(u), float(v)


def trace_streamline(
    sx, sy, u_field, v_field, grid_extent_x, grid_extent_y,
    ds=5.0, max_s=520.0, min_speed=0.5,
):
    """Integrate a wind-field streamline from (sx, sy).

    Returns arrays (x, y, s, U) along the centerline. Stops at the domain
    edge, after max_s, or if the path re-enters a grid cell (closed eddy).
    """
    ny, nx = u_field.shape
    xs = [float(sx)]; ys = [float(sy)]; ss = [0.0]; Us = []
    u0, v0 = _sample_uv(sx, sy, u_field, v_field, grid_extent_x, grid_extent_y)
    U0 = max(float(np.hypot(u0, v0)), min_speed)
    Us.append(U0)

    def to_cell(x, y):
        gx = int(round((x + grid_extent_x) / (2.0 * grid_extent_x) * (nx - 1)))
        gy = int(round((y + grid_extent_y) / (2.0 * grid_extent_y) * (ny - 1)))
        return (min(max(gy, 0), ny - 1), min(max(gx, 0), nx - 1))

    first_s = {to_cell(sx, sy): 0.0}
    x, y = float(sx), float(sy)
    s = 0.0
    last_u, last_v = u0, v0
    while s < max_s:
        u, v = _sample_uv(x, y, u_field, v_field, grid_extent_x, grid_extent_y)
        spd = float(np.hypot(u, v))
        if spd < min_speed:
            if float(np.hypot(last_u, last_v)) < 1e-9:
                break
            u, v = last_u, last_v
            spd = max(float(np.hypot(u, v)), min_speed)
        last_u, last_v = u, v
        x += (u / spd) * ds
        y += (v / spd) * ds
        s += ds
        if abs(x) > grid_extent_x or abs(y) > grid_extent_y:
            break
        cell = to_cell(x, y)
        prev = first_s.get(cell)
        if prev is not None and (s - prev) > 2.5 * ds:
            break  # true closed eddy; ignore same-cell rounding on consecutive steps
        if prev is None:
            first_s[cell] = s
        xs.append(x); ys.append(y); ss.append(s); Us.append(spd)
    return (np.asarray(xs), np.asarray(ys), np.asarray(ss), np.asarray(Us))


def gaussian_segmented_plume(
    x_grid, y_grid, sx, sy, emission_rate,
    u_field, v_field, grid_extent_x, grid_extent_y,
    source_height=6.0, receptor_height=1.5, stability_class="D",
    min_speed=0.5,
):
    """Gaussian segmented plume: centerline follows the (u,v) streamline.

    The classical straight-axis Gaussian uses one (U, θ) from the source and
    cannot bend around buildings or into a wake. Here the plume axis is the
    NS (or potential-flow) streamline. At each receptor the nearest centerline
    point supplies the along-path distance s (used as x' for Pasquill-Gifford
    σ) and the local speed U; the perpendicular distance to the path is y'.
    """
    px, py, ps, pU = trace_streamline(
        sx, sy, u_field, v_field, grid_extent_x, grid_extent_y,
        min_speed=min_speed,
    )
    concentration = np.zeros_like(x_grid, dtype=float)
    if px.size < 2:
        u, v = _sample_uv(sx, sy, u_field, v_field, grid_extent_x, grid_extent_y)
        speed, wind_dir = _wind_speed_dir_from_uv(u, v)
        if speed < min_speed:
            speed = min_speed
        return gaussian_plume(
            x_grid, y_grid, sx, sy, emission_rate, speed, wind_dir,
            source_height, receptor_height, stability_class,
        )

    # Nearest point on the polyline. Only receptors near the path can have
    # non-negligible concentration (Pasquill-Gifford σ_y at 500 m, class D,
    # is ~20 m; a 90 m band is conservative).
    gx = x_grid.ravel(); gy = y_grid.ravel()
    pad = 90.0
    near = (
        (gx >= px.min() - pad) & (gx <= px.max() + pad)
        & (gy >= py.min() - pad) & (gy <= py.max() + pad)
    )
    if not np.any(near):
        return concentration
    idx = np.where(near)[0]
    gx = gx[idx]; gy = gy[idx]
    # Nearest centerline vertex (ds ≈ 5 m, so this is within half a segment
    # of the true foot of the perpendicular — small vs. σ_y).
    _, j = cKDTree(np.column_stack([px, py])).query(np.column_stack([gx, gy]))
    s_hit = ps[j]
    n_hit = np.hypot(gx - px[j], gy - py[j])
    U_hit = np.maximum(pU[j], min_speed)

    # Only downwind of the source, and ignore the first metre (singular).
    valid = s_hit > 1.0
    if not np.any(valid):
        return concentration

    sigma_y, sigma_z = dispersion_sigmas(s_hit[valid], stability_class)
    z = receptor_height
    H = source_height
    lateral = np.exp(-0.5 * (n_hit[valid] ** 2) / (sigma_y ** 2))
    vertical = np.exp(-0.5 * ((z - H) ** 2) / (sigma_z ** 2)) + np.exp(
        -0.5 * ((z + H) ** 2) / (sigma_z ** 2)
    )
    denom = 2.0 * np.pi * U_hit[valid] * sigma_y * sigma_z
    vals = (emission_rate / denom) * lateral * vertical

    out = concentration.ravel()
    out[idx[valid]] = vals
    return out.reshape(x_grid.shape)


def superpose_sources_varwind(
    x_grid, y_grid, flora_matrix, u_field, v_field,
    grid_extent_x, grid_extent_y, current_day,
    stability_class="D", receptor_height=1.5, min_speed=0.5,
):
    """Superpose segmented Gaussian plumes on a spatially-varying wind field.

    Each tree's plume axis is the streamline of (u_field, v_field) starting at
    that tree, so the plume bends with Navier-Stokes channeling and can feed a
    lee-side eddy. This replaces the older source-local straight-axis coupling,
    which could not follow curved or recirculating flow.
    """
    total = np.zeros_like(x_grid, dtype=float)

    for i in range(flora_matrix.shape[0]):
        sx, sy = flora_matrix[i, 0], flora_matrix[i, 1]
        q_base = flora_matrix[i, 2]
        potency = flora_matrix[i, 3]
        start_day = int(flora_matrix[i, 4])
        end_day = int(flora_matrix[i, 5])
        peak_day = flora_matrix[i, 6]
        sigma_t = flora_matrix[i, 7]

        if current_day < start_day or current_day > end_day:
            continue
        gamma = np.exp(-((current_day - peak_day) ** 2) / (2.0 * sigma_t**2))
        effective_emission = q_base * potency * gamma
        if effective_emission < 0.01:
            continue

        total += gaussian_segmented_plume(
            x_grid, y_grid, sx, sy, effective_emission,
            u_field, v_field, grid_extent_x, grid_extent_y,
            6.0, receptor_height, stability_class, min_speed,
        )

    return total
