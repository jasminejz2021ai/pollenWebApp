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

import hashlib
import os

import numpy as np

from engine.potential_flow import solve_potential_flow

try:  # Exact sparse-direct pressure Poisson (mass conservation). Preferred path.
    import scipy.sparse as _sp
    from scipy.sparse.linalg import splu as _splu

    _HAVE_SCIPY = True
except Exception:  # pragma: no cover - fall back to iterative SOR if unavailable
    _HAVE_SCIPY = False


# Characteristic building width used only to set ν = U L / Re_eff.
L_REF_M = 20.0
RE_EFF = 280.0


def _apply_velocity_bc(u, v, solid, u_inf, v_inf, sponge=4):
    """Open-domain BCs classified per face by the free-stream normal component.

    Each of the four domain faces is one of:
      * inflow   -> Dirichlet free stream over a multi-cell sponge. A single-cell
                    Dirichlet rim is cancelled by the pressure projection, so the
                    inflow requires the thicker sponge.
      * outflow  -> zero-gradient (Neumann/convective) copy of the interior.
      * parallel -> free-slip side wall: no penetration (normal velocity = 0)
                    and zero tangential shear (tangential component copied).

    Pinning a *lateral* wall to the free stream (the previous behaviour when the
    crosswind component was zero) confined the open channels beside blocked
    interiors and drove a spurious 2x over-speed rim at the domain edge. Free-slip
    on the flow-parallel faces removes that artifact. Building cells stay no-slip.
    """
    speed = max(float(np.hypot(u_inf, v_inf)), 1e-9)
    tol = 1e-3 * speed  # |normal component| below this => face is parallel to flow

    # --- West / East faces (x-normal; normal component is u) ---
    if u_inf > tol:            # west = inflow, east = outflow
        u[:, :sponge] = u_inf
        v[:, :sponge] = v_inf
        u[:, -1] = u[:, -2]
        v[:, -1] = v[:, -2]
    elif u_inf < -tol:         # east = inflow, west = outflow
        u[:, -sponge:] = u_inf
        v[:, -sponge:] = v_inf
        u[:, 0] = u[:, 1]
        v[:, 0] = v[:, 1]
    else:                      # flow parallel to x-faces => free-slip side walls
        u[:, 0] = 0.0
        v[:, 0] = v[:, 1]
        u[:, -1] = 0.0
        v[:, -1] = v[:, -2]

    # --- South / North faces (y-normal; normal component is v) ---
    if v_inf > tol:            # south = inflow, north = outflow
        u[:sponge, :] = u_inf
        v[:sponge, :] = v_inf
        u[-1, :] = u[-2, :]
        v[-1, :] = v[-2, :]
    elif v_inf < -tol:         # north = inflow, south = outflow
        u[-sponge:, :] = u_inf
        v[-sponge:, :] = v_inf
        u[0, :] = u[1, :]
        v[0, :] = v[1, :]
    else:                      # flow parallel to y-faces => free-slip top/bottom
        v[0, :] = 0.0
        u[0, :] = u[1, :]
        v[-1, :] = 0.0
        u[-1, :] = u[-2, :]

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


# Cache of factorized pressure operators keyed by (mask, shape, dx, dy). The
# building geometry is fixed within (and usually across) a solve, so we build
# and LU-factorize the discrete Laplacian once and reuse it every timestep.
_POISSON_CACHE: dict = {}


def _build_pressure_operator(solid, dx, dy):
    """Factorize the 5-point Laplacian on fluid cells for the pressure Poisson.

    Neumann (zero normal gradient) holds on the domain boundary and on every
    solid face. The resulting pure-Neumann system is singular (pressure is
    defined up to a constant), so a tiny diagonal regularization (epsilon*I) is
    added to make it invertible. Regularizing is preferred over deleting one
    cell's equation: deletion leaves that cell's divergence uncorrected and
    produces a localized velocity spike wherever the reference cell happens to
    sit. Returns an LU factorization plus the fluid index map, cached by
    geometry.
    """
    key = (hash(solid.tobytes()), solid.shape, round(float(dx), 6), round(float(dy), 6))
    hit = _POISSON_CACHE.get(key)
    if hit is not None:
        return hit

    ny, nx = solid.shape
    fluid = ~solid
    idx = -np.ones((ny, nx), dtype=np.int64)
    ids = np.where(fluid.ravel())[0]
    idx.flat[ids] = np.arange(ids.size)
    inv_dx2 = 1.0 / (dx * dx)
    inv_dy2 = 1.0 / (dy * dy)

    fi, fj = np.where(fluid)
    k = np.arange(ids.size)
    rows, cols, data = [], [], []
    diag = np.zeros(ids.size)
    for di, dj, w in ((0, 1, inv_dx2), (0, -1, inv_dx2), (1, 0, inv_dy2), (-1, 0, inv_dy2)):
        ii = fi + di
        jj = fj + dj
        ok = (ii >= 0) & (ii < ny) & (jj >= 0) & (jj < nx)
        okf = ok.copy()
        okf[ok] = fluid[ii[ok], jj[ok]]
        rows.append(k[okf])
        cols.append(idx[ii[okf], jj[okf]])
        data.append(np.full(int(okf.sum()), w))
        diag[okf] -= w
    # Tiny diagonal regularization to lift the constant null space without
    # deleting any equation (which would leave a cell's divergence uncorrected).
    eps = 1e-8 * (2.0 * inv_dx2 + 2.0 * inv_dy2)
    diag -= eps
    rows.append(k)
    cols.append(k)
    data.append(diag)
    R = np.concatenate(rows)
    C = np.concatenate(cols)
    D = np.concatenate(data)
    A = _sp.csc_matrix((D, (R, C)), shape=(ids.size, ids.size))
    lu = _splu(A)
    _POISSON_CACHE[key] = (lu, idx, ids)
    return lu, idx, ids


def _project_pressure(u_star, v_star, solid, dx, dy, dt, p_prev):
    """Solve ∇²p = ∇·u*/dt and return the pressure that makes u divergence-free.

    Uses the exact sparse-direct factorization when SciPy is available; otherwise
    falls back to (many) red-black SOR sweeps.
    """
    rhs = _divergence(u_star, v_star, dx, dy) / max(dt, 1e-6)
    rhs[solid] = 0.0
    if _HAVE_SCIPY:
        lu, idx, ids = _build_pressure_operator(solid, dx, dy)
        b = rhs.ravel()[ids]
        x = lu.solve(b)
        p = np.zeros(idx.shape, dtype=float)
        p.flat[ids] = x
        return p
    return _solve_pressure_poisson(rhs, solid, dx, dy, p_prev, iterations=400)


def solve_navier_stokes(
    building_mask: np.ndarray,
    u_inf: float,
    v_inf: float,
    dx: float,
    dy: float,
    steps: int = 150,
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
    # present; NS then adds vorticity and the lee eddy. The clip is a *safety
    # net only*: it tames the singular potential-flow corner spikes on step 1 so
    # they cannot violate the CFL condition. The converged incompressible field
    # stays well below this limit, so the clip does not sculpt the solution.
    u, v = solve_potential_flow(solid, u_inf, v_inf)
    lim = 6.0 * speed

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
        dt = float(min(0.25 * min(dx, dy) / (umax + 1e-6), dt_diff, 0.5))

        conv_u = u * _upwind_grad(u, u, dx, axis=1) + v * _upwind_grad(u, v, dy, axis=0)
        conv_v = u * _upwind_grad(v, u, dx, axis=1) + v * _upwind_grad(v, v, dy, axis=0)
        visc_u = nu * _laplacian(u, dx, dy, solid)
        visc_v = nu * _laplacian(v, dx, dy, solid)

        u_star = u + dt * (-conv_u + visc_u)
        v_star = v + dt * (-conv_v + visc_v)
        u_star, v_star = _apply_velocity_bc(u_star, v_star, solid, u_inf, v_inf)

        # Exact pressure projection -> divergence-free (mass-conserving) field.
        p = _project_pressure(u_star, v_star, solid, dx, dy, dt, p)
        dp_dx, dp_dy = _gradient(p, dx, dy, solid)
        u = u_star - dt * dp_dx
        v = v_star - dt * dp_dy
        u, v = _clip(u, v)
        u, v = _apply_velocity_bc(u, v, solid, u_inf, v_inf)
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
DIR_BIN_DEG = 10.0
REF_SPEED = 4.0


def mask_digest(building_mask: np.ndarray) -> str:
    """Stable across processes, unlike hash(), so it can key an on-disk cache."""
    m = np.ascontiguousarray(building_mask, dtype=bool)
    return hashlib.sha1(m.tobytes() + str(m.shape).encode()).hexdigest()


def _bin_id(u_inf: float, v_inf: float, dir_bin_deg: float) -> int:
    toward = float(np.degrees(np.arctan2(v_inf, u_inf))) % 360.0
    return int(round(toward / dir_bin_deg)) % int(round(360.0 / dir_bin_deg))


def precompute_ns_fields(building_mask, dx, dy, out_path, dir_bin_deg=DIR_BIN_DEG):
    """Solve every direction bin for one building mask and save them to .npz,
    so the web server never has to run the NS march inside a request."""
    n_bins = int(round(360.0 / dir_bin_deg))
    u_hat = np.zeros((n_bins,) + building_mask.shape, dtype=np.float32)
    v_hat = np.zeros_like(u_hat)
    for b in range(n_bins):
        ang = np.radians(b * dir_bin_deg)
        u, v = solve_navier_stokes(building_mask, REF_SPEED * np.cos(ang),
                                   REF_SPEED * np.sin(ang), dx, dy)
        u_hat[b], v_hat[b] = u / REF_SPEED, v / REF_SPEED
    np.savez_compressed(out_path, mask_sha1=mask_digest(building_mask),
                        dir_bin_deg=dir_bin_deg, u_hat=u_hat, v_hat=v_hat)


def load_ns_fields(path: str) -> bool:
    """Seed the in-memory cache from a precomputed .npz. Fields for a mask that
    no longer matches the buildings are simply never looked up."""
    if not os.path.exists(path):
        return False
    with np.load(path) as data:
        if float(data["dir_bin_deg"]) != DIR_BIN_DEG:
            return False
        digest = str(data["mask_sha1"])
        u_hat, v_hat = data["u_hat"], data["v_hat"]
    for b in range(u_hat.shape[0]):
        key = (digest, b)
        _NS_CACHE[key] = (u_hat[b].astype(float), v_hat[b].astype(float))
    return True


def solve_navier_stokes_cached(
    building_mask: np.ndarray,
    u_inf: float,
    v_inf: float,
    dx: float,
    dy: float,
    dir_bin_deg: float = DIR_BIN_DEG,
):
    """Cached NS solve. Reuses a previous field for the same obstacles and
    a nearby wind direction, then scales to the requested speed."""
    speed = float(np.hypot(u_inf, v_inf))
    if speed < 1e-6:
        z = np.zeros_like(building_mask, dtype=float)
        return z, z

    bin_id = _bin_id(u_inf, v_inf, dir_bin_deg)
    key = (mask_digest(building_mask), bin_id)

    if key in _NS_CACHE:
        u_hat, v_hat = _NS_CACHE[key]
        return u_hat * speed, v_hat * speed

    # Solve at the reference speed along the binned direction, then scale.
    ang = np.radians(bin_id * dir_bin_deg)
    u_ref, v_ref = REF_SPEED * np.cos(ang), REF_SPEED * np.sin(ang)
    u, v = solve_navier_stokes(building_mask, u_ref, v_ref, dx, dy)
    u_hat = u / REF_SPEED
    v_hat = v / REF_SPEED
    _NS_CACHE[key] = (u_hat, v_hat)
    return u_hat * speed, v_hat * speed
