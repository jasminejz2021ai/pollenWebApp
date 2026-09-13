"""
Campus AeroAllergen Mapping (CAM) - 2D Incompressible Navier-Stokes Wind Field

Time-marches the 2D incompressible Navier-Stokes equations on the same regular
grid used by the potential-flow solver:

    ∂u/∂t + (u·∇)u = -∇p + ν ∇²u
    ∇·u = 0

with no-slip walls on building footprints (u = v = 0) and a prescribed
free-stream on inflow boundaries.

This is the viscous, rotational upgrade of potential flow. Continuity still
enforces mass conservation (Venturi / channeling). No-slip generates vorticity,
so the field can stagnate on windward faces AND form a lee-side recirculating
eddy. Potential flow cannot form that eddy.

Honest limits:
  - True atmospheric Reynolds numbers are O(10^6). A 5 m campus grid cannot
    resolve that. We therefore solve at a moderate *effective* Re (~300) so
    that 2D wakes exist and stay stable on this mesh. The eddy *topology* is
    physical; the eddy *size/intensity* is a laminar analogue, not LES/RANS.
  - 2D suppresses 3D vortex stretching and rooftop overflow.
  - Each request starts from the potential-flow field and marches a fraction of
    a flow-through time, then the result is cached by campus + wind direction.
"""

from __future__ import annotations

import numpy as np

from engine.potential_flow import solve_potential_flow


# Characteristic building width used only to set ν = U L / Re_eff.
L_REF_M = 20.0
RE_EFF = 280.0


def _apply_velocity_bc(u, v, solid, u_inf, v_inf, sponge=4):
    """Inflow = free stream (thick sponge), outflow = Neumann, walls = no-slip.

    A multi-cell inflow sponge is required: a 1-cell Dirichlet rim is immediately
    cancelled by the pressure projection, and the campus wind collapses.
    """
    # West
    if u_inf >= 0.0:
        u[:, :sponge] = u_inf
        v[:, :sponge] = v_inf
    else:
        u[:, 0] = u[:, 1]
        v[:, 0] = v[:, 1]
    # East
    if u_inf <= 0.0:
        u[:, -sponge:] = u_inf
        v[:, -sponge:] = v_inf
    else:
        u[:, -1] = u[:, -2]
        v[:, -1] = v[:, -2]
    # South
    if v_inf >= 0.0:
        u[:sponge, :] = u_inf
        v[:sponge, :] = v_inf
    else:
        u[0, :] = u[1, :]
        v[0, :] = v[1, :]
    # North
    if v_inf <= 0.0:
        u[-sponge:, :] = u_inf
        v[-sponge:, :] = v_inf
    else:
        u[-1, :] = u[-2, :]
        v[-1, :] = v[-2, :]
    u[solid] = 0.0
    v[solid] = 0.0
    return u, v


def _shift(field, drow, dcol):
    """Shift `field` by (drow, dcol) without periodic wrap (edge-padded)."""
    return np.pad(field, ((1, 1), (1, 1)), mode="edge")[
        1 + drow:1 + drow + field.shape[0],
        1 + dcol:1 + dcol + field.shape[1],
    ]


def _upwind_grad(field, vel, ds, axis):
    """First-order upwind derivative, no periodic wrap."""
    if axis == 1:
        backward = (field - _shift(field, 0, -1)) / ds
        forward = (_shift(field, 0, 1) - field) / ds
    else:
        backward = (field - _shift(field, -1, 0)) / ds
        forward = (_shift(field, 1, 0) - field) / ds
    return np.where(vel >= 0.0, backward, forward)


def _laplacian(field, dx, dy, solid):
    """5-point Laplacian with Neumann (zero-gradient) on solid neighbours."""
    up = _shift(field, 1, 0)
    down = _shift(field, -1, 0)
    left = _shift(field, 0, -1)
    right = _shift(field, 0, 1)
    up = np.where(_shift(solid, 1, 0), field, up)
    down = np.where(_shift(solid, -1, 0), field, down)
    left = np.where(_shift(solid, 0, -1), field, left)
    right = np.where(_shift(solid, 0, 1), field, right)
    return (right - 2.0 * field + left) / (dx * dx) + (up - 2.0 * field + down) / (dy * dy)


def _divergence(u, v, dx, dy):
    du_dx = (_shift(u, 0, 1) - _shift(u, 0, -1)) / (2.0 * dx)
    dv_dy = (_shift(v, 1, 0) - _shift(v, -1, 0)) / (2.0 * dy)
    return du_dx + dv_dy


def _gradient(p, dx, dy, solid):
    """Central pressure gradient; one-sided at solid faces (no-slip walls)."""
    pe = _shift(p, 0, 1)
    pw = _shift(p, 0, -1)
    pn = _shift(p, 1, 0)
    ps = _shift(p, -1, 0)
    pe = np.where(_shift(solid, 0, 1), p, pe)
    pw = np.where(_shift(solid, 0, -1), p, pw)
    pn = np.where(_shift(solid, 1, 0), p, pn)
    ps = np.where(_shift(solid, -1, 0), p, ps)
    return (pe - pw) / (2.0 * dx), (pn - ps) / (2.0 * dy)


def _solve_pressure_poisson(rhs, solid, dx, dy, p, iterations=40, tol=2e-4):
    """Red-black SOR for ∇²p = rhs, Neumann on solid and domain boundary."""
    ny, nx = rhs.shape
    inv_dx2 = 1.0 / (dx * dx)
    inv_dy2 = 1.0 / (dy * dy)
    denom = 2.0 * inv_dx2 + 2.0 * inv_dy2

    boundary = np.zeros((ny, nx), dtype=bool)
    boundary[0, :] = boundary[-1, :] = boundary[:, 0] = boundary[:, -1] = True
    fluid = (~solid) & (~boundary)

    ii, jj = np.meshgrid(np.arange(ny), np.arange(nx), indexing="ij")
    checker = (ii + jj) % 2
    red = fluid & (checker == 0)
    black = fluid & (checker == 1)

    n_char = max(nx, ny)
    omega = 2.0 / (1.0 + np.sin(np.pi / n_char))

    def sweep(cells):
        up = np.roll(p, -1, axis=0)
        down = np.roll(p, 1, axis=0)
        left = np.roll(p, 1, axis=1)
        right = np.roll(p, -1, axis=1)
        up = np.where(np.roll(solid, -1, axis=0) | np.roll(boundary, -1, axis=0), p, up)
        down = np.where(np.roll(solid, 1, axis=0) | np.roll(boundary, 1, axis=0), p, down)
        left = np.where(np.roll(solid, 1, axis=1) | np.roll(boundary, 1, axis=1), p, left)
        right = np.where(np.roll(solid, -1, axis=1) | np.roll(boundary, -1, axis=1), p, right)
        new = ((right + left) * inv_dx2 + (up + down) * inv_dy2 - rhs) / denom
        p[cells] = (1.0 - omega) * p[cells] + omega * new[cells]

    for it in range(iterations):
        p_old = p.copy()
        sweep(red)
        sweep(black)
        # Pin the mean on fluid cells so the Neumann Poisson problem is unique.
        if fluid.any():
            p[fluid] -= p[fluid].mean()
        p[solid] = 0.0
        if it % 8 == 0 and fluid.any():
            if np.max(np.abs(p - p_old)[fluid]) < tol:
                break
    return p


def solve_navier_stokes(
    building_mask: np.ndarray,
    u_inf: float,
    v_inf: float,
    dx: float,
    dy: float,
    steps: int = 90,
    re_eff: float = RE_EFF,
    l_ref: float = L_REF_M,
):
    """March 2D incompressible NS to a quasi-steady wind field.

    building_mask: True on solid (building) cells.
    u_inf, v_inf: free-stream components (m/s), +x east, +y north.
    dx, dy: physical grid spacing (m).
    Returns (u, v) in m/s; solid cells are 0.
    """
    solid = building_mask.astype(bool)
    ny, nx = solid.shape
    speed = float(np.hypot(u_inf, v_inf))
    if speed < 1e-6 or not np.any(~solid):
        return np.zeros((ny, nx)), np.zeros((ny, nx))

    # Effective viscosity so Re_eff = U L / ν is moderate on this mesh.
    nu = max(speed * l_ref / max(re_eff, 1.0), 0.05)
    fluid = ~solid

    # Start from potential flow so the irrotational/channeling part is already
    # present; NS then adds vorticity and the lee eddy. Clip the singular
    # corner spikes so they cannot violate the CFL condition on step 1.
    u, v = solve_potential_flow(solid, u_inf, v_inf)
    lim = 2.2 * speed

    def _clip(uu, vv):
        mag = np.hypot(uu, vv)
        s = np.minimum(1.0, lim / (mag + 1e-9))
        return uu * s, vv * s

    u, v = _clip(u, v)
    u, v = _apply_velocity_bc(u, v, solid, u_inf, v_inf)

    p = np.zeros((ny, nx), dtype=float)
    dt_diff = 0.20 * min(dx, dy) ** 2 / (4.0 * nu + 1e-9)

    for _ in range(steps):
        umax = float(np.max(np.hypot(u[fluid], v[fluid]))) if fluid.any() else speed
        dt = float(min(0.20 * min(dx, dy) / (umax + 1e-6), dt_diff, 0.5))

        conv_u = u * _upwind_grad(u, u, dx, axis=1) + v * _upwind_grad(u, v, dy, axis=0)
        conv_v = u * _upwind_grad(v, u, dx, axis=1) + v * _upwind_grad(v, v, dy, axis=0)
        visc_u = nu * _laplacian(u, dx, dy, solid)
        visc_v = nu * _laplacian(v, dx, dy, solid)

        u_star = u + dt * (-conv_u + visc_u)
        v_star = v + dt * (-conv_v + visc_v)
        u_star, v_star = _clip(u_star, v_star)
        u_star, v_star = _apply_velocity_bc(u_star, v_star, solid, u_inf, v_inf)

        rhs = _divergence(u_star, v_star, dx, dy) / max(dt, 1e-6)
        rhs[solid] = 0.0
        p = _solve_pressure_poisson(rhs, solid, dx, dy, p)

        dp_dx, dp_dy = _gradient(p, dx, dy, solid)
        u = u_star - dt * dp_dx
        v = v_star - dt * dp_dy
        u, v = _clip(u, v)
        u, v = _apply_velocity_bc(u, v, solid, u_inf, v_inf)
        # Weak bulk restore so viscosity/projection cannot kill the free stream
        # while still allowing local wakes to persist.
        u[fluid] += 0.02 * (u_inf - u[fluid])
        v[fluid] += 0.02 * (v_inf - v[fluid])
        u[solid] = 0.0
        v[solid] = 0.0

        if not (np.isfinite(u).all() and np.isfinite(v).all()):
            # Rare blow-up: return the potential-flow seed rather than NaNs.
            u, v = solve_potential_flow(solid, u_inf, v_inf)
            break

    u[solid] = 0.0
    v[solid] = 0.0
    return u, v


# Direction-binned cache: (mask_hash, dir_bin) -> (u_hat, v_hat) at unit speed.
# Steady laminar NS at fixed Re is homogeneous in U, so we store u/U and scale.
_NS_CACHE: dict = {}


def solve_navier_stokes_cached(
    building_mask: np.ndarray,
    u_inf: float,
    v_inf: float,
    dx: float,
    dy: float,
    dir_bin_deg: float = 10.0,
):
    """Cached NS solve. Reuses a previous field for the same obstacles and
    a nearby wind direction, then scales to the requested speed."""
    speed = float(np.hypot(u_inf, v_inf))
    if speed < 1e-6:
        z = np.zeros_like(building_mask, dtype=float)
        return z, z

    toward = float(np.degrees(np.arctan2(v_inf, u_inf))) % 360.0
    bin_id = int(round(toward / dir_bin_deg)) % int(round(360.0 / dir_bin_deg))
    key = (hash(building_mask.tobytes()), bin_id, building_mask.shape)

    if key in _NS_CACHE:
        u_hat, v_hat = _NS_CACHE[key]
        return u_hat * speed, v_hat * speed

    # Solve at a reference 4 m/s along the binned direction, then scale.
    ang = np.radians(bin_id * dir_bin_deg)
    u_ref, v_ref = 4.0 * np.cos(ang), 4.0 * np.sin(ang)
    u, v = solve_navier_stokes(building_mask, u_ref, v_ref, dx, dy)
    u_hat = u / 4.0
    v_hat = v / 4.0
    _NS_CACHE[key] = (u_hat, v_hat)
    return u_hat * speed, v_hat * speed
