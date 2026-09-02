"""
Generate wind-flow figures for the CAM manuscript.

Uses the SAME 2D potential-flow solver the live system uses
(engine.potential_flow.solve_potential_flow) to visualize how the ambient wind
is diverted and channeled around building footprints in a school micro-
environment. Produces two figures in docs/:

  fig_windflow_idealized.png  - uniform wind vs. potential flow around an
                                idealized cluster of buildings (a corridor),
                                streamlines colored by local wind speed.
  fig_windflow_campus.png     - the real Gunn High School footprints, showing
                                the diverted/channeled wind field for two
                                ambient wind directions, plus the local
                                speed-up/slow-down relative to the free stream.

The solver is inviscid potential flow (Laplace's equation with no-penetration
walls); it captures diversion and channeling but no turbulent wake (see paper).
"""

import os
import json
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import TwoSlopeNorm

# Import ONLY the pure-numpy potential-flow solver (avoids scipy-dependent
# imports elsewhere in the engine package).
import importlib.util
_HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location(
    "cam_potential_flow", os.path.join(_HERE, "engine", "potential_flow.py"))
_pf = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_pf)
solve_potential_flow = _pf.solve_potential_flow

DOCS = os.path.abspath(os.path.join(_HERE, "..", "docs"))

# --- Grid configuration MATCHING the live system (app.py) ---------------------
GRID_SIZE = 120
GRID_EXTENT_X = 320.0   # meters E-W from center
GRID_EXTENT_Y = 280.0   # meters N-S from center
_x_lin = np.linspace(-GRID_EXTENT_X, GRID_EXTENT_X, GRID_SIZE)
_y_lin = np.linspace(-GRID_EXTENT_Y, GRID_EXTENT_Y, GRID_SIZE)
GRID_X, GRID_Y = np.meshgrid(_x_lin, _y_lin)
DX = 2 * GRID_EXTENT_X / (GRID_SIZE - 1)   # meters per cell (E-W)
DY = 2 * GRID_EXTENT_Y / (GRID_SIZE - 1)   # meters per cell (N-S)

METERS_PER_DEG_LAT = 111320.0


def wind_components(speed, direction_deg):
    """Meteorological wind (deg FROM which it blows) -> (u east, v north)."""
    theta = np.radians(270.0 - direction_deg)
    return speed * np.cos(theta), speed * np.sin(theta)


def rasterize_rects(rects):
    """rects: list of (x0, y0, x1, y1) footprints in meters. Returns bool mask."""
    mask = np.zeros_like(GRID_X, dtype=bool)
    for x0, y0, x1, y1 in rects:
        mask |= (GRID_X >= x0) & (GRID_X <= x1) & (GRID_Y >= y0) & (GRID_Y <= y1)
    return mask


def rasterize_campus(buildings, center_lat, center_lon):
    """Rasterize detected building polygons (lat/lng) to the grid, matching
    app._rasterize_buildings."""
    mplat = METERS_PER_DEG_LAT
    mplon = 111320.0 * np.cos(np.radians(center_lat))
    gx = GRID_X.ravel()
    gy = GRID_Y.ravel()
    inside = np.zeros(gx.shape, dtype=bool)
    for b in buildings:
        poly = b.get("polygon")
        if not poly or len(poly) < 3:
            continue
        xs = np.array([(pt[1] - center_lon) * mplon for pt in poly])
        ys = np.array([(pt[0] - center_lat) * mplat for pt in poly])
        in_bbox = (gx >= xs.min()) & (gx <= xs.max()) & (gy >= ys.min()) & (gy <= ys.max())
        if not np.any(in_bbox):
            continue
        idx = np.where(in_bbox)[0]
        px, py = gx[idx], gy[idx]
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
    return inside.reshape(GRID_X.shape)


def physical_velocity(mask, speed, direction_deg):
    """Solve potential flow and return (u, v, spd) in m/s on the grid.

    The solver returns velocity in per-cell (grid) units and rescales the mean
    fluid SPEED to the free-stream magnitude, so the returned field is already
    in m/s consistent with `speed`. We only need to correct the anisotropy from
    unequal DX/DY so directions are geometrically faithful."""
    u_inf, v_inf = wind_components(speed, direction_deg)
    # Match the live system's stable solver settings.
    u, v = solve_potential_flow(mask, u_inf, v_inf, iterations=400, tol=1e-4)
    # gradient in potential_flow is per-cell; correct for physical spacing so
    # directions are geometrically faithful on the unequal-spacing grid.
    u = u / DX
    v = v / DY
    # re-normalize mean fluid speed to the requested free-stream speed, guarding
    # against any non-finite cells.
    fluid = ~mask
    finite = fluid & np.isfinite(u) & np.isfinite(v)
    cur = np.mean(np.hypot(u[finite], v[finite])) if finite.any() else 0.0
    if np.isfinite(cur) and cur > 1e-9:
        s = speed / cur
        u *= s
        v *= s
    spd = np.hypot(u, v)
    spd[mask] = np.nan
    return u, v, spd


def draw_buildings(ax, mask, color="#444", alpha=0.9):
    ax.contourf(GRID_X, GRID_Y, mask.astype(float), levels=[0.5, 1.5],
                colors=[color], alpha=alpha)
    ax.contour(GRID_X, GRID_Y, mask.astype(float), levels=[0.5],
               colors="black", linewidths=0.8)


# =============================================================================
# Figure 1: idealized building cluster - uniform wind vs. potential flow
# =============================================================================
def make_idealized():
    # A small campus cluster: two rows of buildings forming a central corridor,
    # plus an isolated block. Coordinates in meters.
    rects = [
        (-180, 40, -60, 150),    # upper-left block
        (-30, 40, 90, 150),      # upper-right block
        (-180, -150, -60, -40),  # lower-left block
        (-30, -150, 90, -40),    # lower-right block
        (150, -30, 240, 60),     # isolated downwind block
    ]
    mask = rasterize_rects(rects)

    speed = 4.0
    direction = 270.0   # wind FROM the west -> blows toward the east (+x)
    u, v, spd = physical_velocity(mask, speed, direction)

    vmax = 2.0 * speed  # clip corner singularities for a readable color scale
    fig, axes = plt.subplots(1, 2, figsize=(13, 5.4))

    # (a) Uniform wind: same vector everywhere.
    ax = axes[0]
    u_u, v_u = wind_components(speed, direction)
    step = 8
    ax.quiver(GRID_X[::step, ::step], GRID_Y[::step, ::step],
              np.full_like(GRID_X[::step, ::step], u_u),
              np.full_like(GRID_Y[::step, ::step], v_u),
              color="#1f77b4", scale=110, width=0.004, alpha=0.85)
    draw_buildings(ax, mask)
    ax.set_title("(a) Uniform wind (conventional assumption)", fontsize=12)
    ax.set_xlabel("East (m)"); ax.set_ylabel("North (m)")
    ax.set_xlim(-GRID_EXTENT_X, GRID_EXTENT_X)
    ax.set_ylim(-GRID_EXTENT_Y, GRID_EXTENT_Y)
    ax.set_aspect("equal")

    # (b) Potential flow: speed heatmap + black streamlines.
    ax = axes[1]
    spd_plot = np.clip(np.nan_to_num(spd, nan=0.0), 0, vmax)
    pcm = ax.pcolormesh(GRID_X, GRID_Y, spd_plot, cmap="turbo",
                        vmin=0, vmax=vmax, shading="auto")
    ax.streamplot(_x_lin, _y_lin, u, v, color="black", density=1.5,
                  linewidth=0.8, arrowsize=0.9)
    draw_buildings(ax, mask, color="#dddddd", alpha=1.0)
    cb = fig.colorbar(pcm, ax=ax, fraction=0.046, pad=0.02)
    cb.set_label("wind speed (m/s)")
    ax.set_title("(b) Potential flow diverted & channeled by buildings", fontsize=12)
    ax.set_xlabel("East (m)"); ax.set_ylabel("North (m)")
    ax.set_xlim(-GRID_EXTENT_X, GRID_EXTENT_X)
    ax.set_ylim(-GRID_EXTENT_Y, GRID_EXTENT_Y)
    ax.set_aspect("equal")

    fig.suptitle("Ambient 4 m/s westerly wind in a school micro-environment",
                 fontsize=13, y=0.99)
    fig.tight_layout(rect=[0, 0, 1, 0.96])
    out = os.path.join(DOCS, "fig_windflow_idealized.png")
    fig.savefig(out, dpi=170)
    plt.close(fig)
    print("wrote", out)
    # report channeling / stagnation statistics
    gap = (GRID_X > -60) & (GRID_X < -30) & (np.abs(GRID_Y) < 40)   # N-S alley
    windward = (GRID_X > -195) & (GRID_X < -180) & (GRID_Y > 40) & (GRID_Y < 150)
    print("  free stream: %.1f m/s" % speed)
    if np.isfinite(spd[gap]).any():
        print("  alley (between L/R blocks) mean speed: %.2f m/s" % np.nanmean(spd[gap]))
    if np.isfinite(spd[windward]).any():
        print("  windward-face mean speed: %.2f m/s" % np.nanmean(spd[windward]))
    print("  max local speed (corner, clipped in plot): %.2f m/s" % np.nanmax(spd))


# =============================================================================
# Figure 2: real Gunn campus footprints
# =============================================================================
def make_campus():
    cache = os.path.join(_HERE, "static", "gunn", "detect_cache.json")
    with open(cache) as f:
        data = json.load(f)
    buildings = data.get("buildings", [])
    # campus center from campus_data
    center_lat, center_lon = 37.4033, -122.1289
    try:
        import importlib.util as _u
        cd_spec = _u.spec_from_file_location(
            "cam_campus_data", os.path.join(_HERE, "data", "campus_data.py"))
        cd = _u.module_from_spec(cd_spec)
        cd_spec.loader.exec_module(cd)
        g = cd.CAMPUSES["gunn"] if hasattr(cd, "CAMPUSES") else None
        if g:
            center_lat, center_lon = g["center_lat"], g["center_lon"]
    except Exception as e:
        print("  (using default Gunn center)", e)

    mask = rasterize_campus(buildings, center_lat, center_lon)
    print("  campus building cells: %d / %d" % (mask.sum(), mask.size))

    speed = 4.0
    scenarios = [(225.0, "SW wind (from 225\u00b0)"),
                 (270.0, "W wind (from 270\u00b0)")]

    vmax = 2.0 * speed
    fig, axes = plt.subplots(1, 2, figsize=(13.5, 6.2))
    for ax, (direction, label) in zip(axes, scenarios):
        u, v, spd = physical_velocity(mask, speed, direction)
        spd_plot = np.clip(np.nan_to_num(spd, nan=0.0), 0, vmax)
        pcm = ax.pcolormesh(GRID_X, GRID_Y, spd_plot, cmap="turbo",
                            vmin=0, vmax=vmax, shading="auto")
        ax.streamplot(_x_lin, _y_lin, u, v, color="black", density=2.0,
                      linewidth=0.6, arrowsize=0.8)
        draw_buildings(ax, mask, color="#dddddd", alpha=1.0)
        cb = fig.colorbar(pcm, ax=ax, fraction=0.046, pad=0.02)
        cb.set_label("wind speed (m/s)")
        ax.set_title(label, fontsize=12)
        ax.set_xlabel("East (m)"); ax.set_ylabel("North (m)")
        ax.set_xlim(-GRID_EXTENT_X, GRID_EXTENT_X)
        ax.set_ylim(-GRID_EXTENT_Y, GRID_EXTENT_Y)
        ax.set_aspect("equal")
        print("  %s: max local speed %.2f m/s, min %.2f m/s" % (
            label, np.nanmax(spd), np.nanmin(spd)))

    fig.suptitle("Simulated wind field over Gunn High School footprints "
                 "(4 m/s ambient, 2D potential flow)", fontsize=13, y=0.99)
    fig.tight_layout(rect=[0, 0, 1, 0.95])
    out = os.path.join(DOCS, "fig_windflow_campus.png")
    fig.savefig(out, dpi=170)
    plt.close(fig)
    print("wrote", out)


if __name__ == "__main__":
    make_idealized()
    make_campus()
