"""One-off cleanup: remove Stanford tree canopies that mostly overlap a building
footprint (likely rooftop false positives). A tree is removed if more than
OVERLAP_THRESHOLD of its canopy disk area falls inside any building polygon.

Uses a local-meter projection, a coarse spatial bin index over buildings for
speed, and a vectorized ray-casting point-in-polygon test on sample points
distributed over each tree disk (area-weighted via sqrt radial sampling).
"""
import json
import math
import numpy as np

CAMPUS = "stanford"
OVERLAP_THRESHOLD = 0.5   # remove if >50% of canopy area is inside a building
N_SAMPLES = 60            # sample points per tree disk
BIN_M = 100.0             # spatial bin size (meters) for the building index

path = f"static/{CAMPUS}/detect_cache.json"
data = json.load(open(path))
trees = data["trees"]
buildings = data["buildings"]

# Reference origin for the local-meter projection.
lat0 = float(np.mean([t["lat"] for t in trees]))
lon0 = float(np.mean([t["lng"] for t in trees]))
MPLAT = 111320.0
mplon = 111320.0 * math.cos(math.radians(lat0))


def to_xy(lat, lng):
    return ((lng - lon0) * mplon, (lat - lat0) * MPLAT)


# Precompute building polygons in local meters + bounding boxes.
bpolys = []   # list of (xs, ys, xmin, xmax, ymin, ymax)
for b in buildings:
    poly = b.get("polygon")
    if not poly or len(poly) < 3:
        continue
    xs = np.array([(pt[1] - lon0) * mplon for pt in poly])
    ys = np.array([(pt[0] - lat0) * MPLAT for pt in poly])
    bpolys.append((xs, ys, xs.min(), xs.max(), ys.min(), ys.max()))

# Coarse spatial bin index: map each bin cell -> list of building indices whose
# bbox touches that cell.
from collections import defaultdict
bin_index = defaultdict(list)
for bi, (xs, ys, xmin, xmax, ymin, ymax) in enumerate(bpolys):
    for cx in range(int(math.floor(xmin / BIN_M)), int(math.floor(xmax / BIN_M)) + 1):
        for cy in range(int(math.floor(ymin / BIN_M)), int(math.floor(ymax / BIN_M)) + 1):
            bin_index[(cx, cy)].append(bi)


def point_in_poly_vec(px, py, xs, ys):
    """Vectorized ray casting: fraction of (px,py) points inside polygon."""
    n = len(xs)
    inside = np.zeros(px.shape, dtype=bool)
    j = n - 1
    for i in range(n):
        xi, yi, xj, yj = xs[i], ys[i], xs[j], ys[j]
        cond = ((yi > py) != (yj > py)) & (
            px < (xj - xi) * (py - yi) / (yj - yi + 1e-12) + xi)
        inside ^= cond
        j = i
    return inside


# Pre-generate a unit-disk sample pattern (area-uniform via sqrt radius).
rng = np.random.default_rng(0)
ang = rng.uniform(0, 2 * math.pi, N_SAMPLES)
rad = np.sqrt(rng.uniform(0, 1, N_SAMPLES))
unit_x = rad * np.cos(ang)
unit_y = rad * np.sin(ang)

kept, removed = [], 0
for t in trees:
    r = float(t.get("radius_m") or 4.0)
    cx, cy = to_xy(t["lat"], t["lng"])
    sx = cx + unit_x * r
    sy = cy + unit_y * r

    # Candidate buildings: those in the tree-center bin and neighbors.
    bx, by = int(math.floor(cx / BIN_M)), int(math.floor(cy / BIN_M))
    cand = set()
    for dx in (-1, 0, 1):
        for dy in (-1, 0, 1):
            cand.update(bin_index.get((bx + dx, by + dy), ()))

    inside_any = np.zeros(N_SAMPLES, dtype=bool)
    for bi in cand:
        xs, ys, xmin, xmax, ymin, ymax = bpolys[bi]
        # Quick reject if the tree disk bbox doesn't touch the building bbox.
        if cx + r < xmin or cx - r > xmax or cy + r < ymin or cy - r > ymax:
            continue
        inside_any |= point_in_poly_vec(sx, sy, xs, ys)

    frac = inside_any.mean()
    if frac > OVERLAP_THRESHOLD:
        removed += 1
    else:
        kept.append(t)

data["trees"] = kept
json.dump(data, open(path, "w"))
print(f"trees before={len(trees)} removed={removed} kept={len(kept)} "
      f"(threshold={OVERLAP_THRESHOLD:.0%})")
from collections import Counter
print(dict(Counter(t.get("species_key") for t in kept)))
