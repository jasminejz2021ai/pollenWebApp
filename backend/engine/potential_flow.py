"""
Campus AeroAllergen Mapping (CAM) - 2D Potential-Flow Wind Field

Computes a spatially-varying, incompressible, irrotational (potential) wind
field that flows AROUND building footprints, by solving Laplace's equation for
the velocity potential phi:

    div(grad phi) = 0,   u = d phi/dx,  v = d phi/dy

with:
  - a uniform free-stream (U, direction) imposed at the domain boundary, and
  - a no-penetration condition on building walls (normal velocity = 0), which
    makes the flow deflect around the buildings.

IMPORTANT (honest limitation): potential flow is inviscid and has NO wakes,
separation, or recirculation. Flow speeds up around building corners and
rejoins smoothly downwind. It therefore does NOT reproduce the pollen-trapping
low-velocity wake behind a building. It is the classical, computationally cheap
approximation for how wind is diverted by obstacles, not a substitute for CFD.
"""

import numpy as np


def solve_potential_flow(building_mask: np.ndarray, u_inf: float, v_inf: float,
                         iterations: int = 4000, tol: float = 1e-6):
    """Solve 2D potential flow around obstacles on a regular grid.

    building_mask: 2D bool array, True where a building blocks flow.
    u_inf, v_inf: free-stream velocity components (m/s) in grid axes
        (u = +x/east, v = +y/north).
    Returns (u, v): 2D arrays of the flow velocity at each grid cell. Cells
        inside buildings are set to 0.

    Method: seed phi with the uniform-flow potential phi0 = u_inf*x + v_inf*y,
    then relax Laplace's equation to convergence holding the domain boundary at
    the uniform-flow values (Dirichlet) and enforcing zero normal gradient on
    building faces (no penetration / Neumann). Velocity is the gradient of phi.

    The relaxation uses RED-BLACK Gauss-Seidel with successive over-relaxation
    (SOR). Red-black ordering is essential: a plain Jacobi sweep (updating every
    cell from the previous iterate) is only stable for omega <= 1, so applying
    SOR over-relaxation (omega > 1) to a Jacobi sweep slowly diverges and blows
    up at obstacle corners. Updating the two colours in sequence makes the sweep
    a true Gauss-Seidel step, for which SOR is stable and rapidly convergent for
    0 < omega < 2.
    """
    ny, nx = building_mask.shape
    # Grid coordinates (unit spacing; gradients are per-cell, rescaled later).
    xs = np.arange(nx, dtype=float)
    ys = np.arange(ny, dtype=float)
    X, Y = np.meshgrid(xs, ys)

    # Uniform-flow potential as initial guess and boundary condition.
    phi0 = u_inf * X + v_inf * Y
    phi = phi0.copy()

    solid = building_mask
    fluid = ~solid

    # Interior fluid cells only (domain boundary is Dirichlet and never updated).
    boundary = np.zeros((ny, nx), dtype=bool)
    boundary[0, :] = boundary[-1, :] = boundary[:, 0] = boundary[:, -1] = True
    interior = fluid & ~boundary

    ii, jj = np.meshgrid(np.arange(ny), np.arange(nx), indexing="ij")
    checker = (ii + jj) % 2
    red = interior & (checker == 0)
    black = interior & (checker == 1)

    # Optimal SOR factor for a Laplacian on an ~N x N grid.
    n_char = max(nx, ny)
    omega = 2.0 / (1.0 + np.sin(np.pi / n_char))

    def _sweep(cells):
        # 4-neighbour average with a no-penetration (reflective) rule: a solid
        # neighbour contributes the centre value, i.e. zero normal gradient.
        up = np.roll(phi, -1, axis=0)
        down = np.roll(phi, 1, axis=0)
        left = np.roll(phi, 1, axis=1)
        right = np.roll(phi, -1, axis=1)
        up = np.where(np.roll(solid, -1, axis=0), phi, up)
        down = np.where(np.roll(solid, 1, axis=0), phi, down)
        left = np.where(np.roll(solid, 1, axis=1), phi, left)
        right = np.where(np.roll(solid, -1, axis=1), phi, right)
        new = 0.25 * (up + down + left + right)
        phi[cells] = (1 - omega) * phi[cells] + omega * new[cells]

    for it in range(iterations):
        phi_old = phi.copy()
        _sweep(red)     # update red cells using current (black) values
        _sweep(black)   # then black cells using freshly-updated red values
        if it % 25 == 0:
            change = np.max(np.abs(phi - phi_old)[interior]) if interior.any() else 0.0
            if change < tol:
                break

    # Velocity = gradient of phi (central differences).
    v_grad, u_grad = np.gradient(phi)  # returns d/dy, d/dx
    u = u_grad
    v = v_grad

    # Zero velocity inside buildings.
    u = np.where(solid, 0.0, u)
    v = np.where(solid, 0.0, v)

    # Rescale so the mean fluid speed matches the intended free-stream speed
    # (relaxation preserves shape; this fixes the magnitude).
    target = np.hypot(u_inf, v_inf)
    if fluid.any():
        cur = np.mean(np.hypot(u[fluid], v[fluid]))
        if cur > 1e-6:
            scale = target / cur
            u *= scale
            v *= scale

    return u, v
