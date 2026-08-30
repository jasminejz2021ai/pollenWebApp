"""
SAM-based tree canopy detection (preview / comparison).

Runs Segment Anything on a campus image and keeps masks that look like tree
canopy (green vegetation) by color, size, and shape. Assigns a species with
the same size heuristic used elsewhere. Writes to a SEPARATE preview file so it
can be compared before replacing the existing trees.

Usage: python detect_trees_sam.py <campus>   ->  static/<campus>/trees_sam_preview.json
"""
import os
import sys
import json
import math
import numpy as np
from PIL import Image

BACKEND = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BACKEND)


def looks_like_canopy(img, seg):
    ys, xs = np.where(seg)
    if len(ys) == 0:
        return False
    r = img[ys, xs, 0].astype(float)
    g = img[ys, xs, 1].astype(float)
    b = img[ys, xs, 2].astype(float)
    green_excess = g - (r + b) / 2.0
    brightness = (r + g + b) / 3.0
    veg = (green_excess > 4) & (brightness > 30) & (brightness < 165)
    return np.mean(veg) > 0.6


def main(campus_key):
    from data.campus_data import get_campus
    from detect_buildings_sam import load_generator
    from engine.detect import classify_tree_generic

    campus = get_campus(campus_key)
    bounds = campus["bounds"]
    img = np.array(Image.open(os.path.join(BACKEND, "static", campus_key, "satellite.png")).convert("RGB"))
    h, w = img.shape[:2]
    span_lat = bounds["north"] - bounds["south"]
    mppx = abs(bounds["east"] - bounds["west"]) * 111320.0 * math.cos(
        math.radians((bounds["north"] + bounds["south"]) / 2)) / w

    gen = load_generator()
    print("Generating masks...", flush=True)
    masks = gen.generate(img)
    print(f"SAM proposed {len(masks)} masks", flush=True)

    trees = []
    for m in masks:
        seg = m["segmentation"]
        area = int(seg.sum())
        x0, y0, bw, bh = m["bbox"]
        radius_px = math.sqrt(area / math.pi)
        radius_m = radius_px * span_lat * 111320.0 / h
        if radius_m < 2 or radius_m > 40:
            continue
        if not looks_like_canopy(img, seg):
            continue
        ys, xs = np.where(seg)
        cy, cx = float(np.mean(ys)), float(np.mean(xs))
        lat = bounds["north"] - (cy / h) * (bounds["north"] - bounds["south"])
        lng = bounds["west"] + (cx / w) * (bounds["east"] - bounds["west"])
        r_lat = radius_px * (bounds["north"] - bounds["south"]) / h
        r_lng = radius_px * (bounds["east"] - bounds["west"]) / w
        poly = []
        for k in range(21):
            th = 2 * math.pi * k / 20
            poly.append([round(lat + r_lat * math.sin(th), 6), round(lng + r_lng * math.cos(th), 6)])
        trees.append({
            "lat": round(lat, 6), "lng": round(lng, 6),
            "area_px": area, "radius_m": round(radius_m, 1),
            "polygon": poly, "type": "tree",
            "species_key": classify_tree_generic(radius_m),
            "source": "sam_vit_b",
        })

    print(f"Kept {len(trees)} canopy masks", flush=True)
    out = os.path.join(BACKEND, "static", campus_key, "trees_sam_preview.json")
    json.dump({"trees": trees}, open(out, "w"))
    print(f"Wrote preview to {out}")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "stanford")
