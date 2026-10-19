"""Precompute the Navier-Stokes wind field for every 10-degree direction bin.

Writes static/<campus>/ns_fields.npz, which app.py loads at startup so no
request has to run the NS march (~25 s each on Render's free CPU). Re-run this
after editing a campus's buildings in detect_cache.json; until then the server
falls back to solving a direction on first use.

Usage:
  python precompute_ns_fields.py [campus ...]
"""

import json
import os
import sys
import time

import numpy as np

import app as A
from engine.navier_stokes import precompute_ns_fields


def main(keys):
    dx = 2.0 * A.GRID_EXTENT_X / (A.GRID_SIZE - 1)
    dy = 2.0 * A.GRID_EXTENT_Y / (A.GRID_SIZE - 1)
    for key in keys:
        campus = A.get_campus(key)
        cache_path = A.campus_static_path(key, "detect_cache.json")
        if not os.path.exists(cache_path):
            print(f"{key}: no detect_cache.json, skipped")
            continue
        with open(cache_path) as f:
            buildings = json.load(f).get("buildings", [])
        if not buildings:
            print(f"{key}: no buildings, skipped")
            continue
        mplon = 111320.0 * np.cos(np.radians(campus["center_lat"]))
        mask = A._rasterize_buildings(buildings, campus["center_lat"], campus["center_lon"],
                                      A.METERS_PER_DEG_LAT, mplon)
        out_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static", key)
        os.makedirs(out_dir, exist_ok=True)
        out = os.path.join(out_dir, A.NS_FIELDS_FILE)
        t0 = time.time()
        precompute_ns_fields(mask, dx, dy, out)
        print(f"{key}: wrote {out} ({os.path.getsize(out) / 1e6:.1f} MB, {time.time() - t0:.0f} s)")


if __name__ == "__main__":
    main(sys.argv[1:] or list(A.CAMPUSES))
