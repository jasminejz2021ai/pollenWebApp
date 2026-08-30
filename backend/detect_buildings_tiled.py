"""
Tiled SAM rooftop detection.

Splits the campus image into an NxN grid and runs SAM on each tile. Because SAM
downscales its input to ~1024px internally, tiling gives each tile much higher
effective resolution, so small rooftops that are lost in a single whole-image
pass get detected. Detections are converted to lat/lng, filtered by relaxed
roof color/size/shape criteria, then merged with de-duplication.

Usage: python detect_buildings_tiled.py <campus> [grid]   (grid default 3)
Preserves the existing "trees" in the cache; replaces "buildings".
"""
import os
import sys
import json
import math
import numpy as np
from PIL import Image

BACKEND = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BACKEND)


def looks_like_roof(tile, seg):
    ys, xs = np.where(seg)
    if len(ys) == 0:
        return False
    r = tile[ys, xs, 0].astype(float)
    g = tile[ys, xs, 1].astype(float)
    b = tile[ys, xs, 2].astype(float)
    brightness = (r + g + b) / 3.0
    sat = np.maximum(np.maximum(r, g), b) - np.minimum(np.minimum(r, g), b)
    green_excess = g - (r + b) / 2.0
    gray = (sat < 55) & (brightness > 85) & (brightness < 245)
    warm = (r >= g - 5) & ((r - b) > 6) & (brightness > 65) & (brightness < 225)
    roof_frac = np.mean(gray | warm)
    veg_frac = np.mean(green_excess > 18)
    return roof_frac > 0.5 and veg_frac < 0.35


def main(campus_key, grid=3):
    import cv2
    from data.campus_data import get_campus
    from detect_buildings_sam import load_generator

    campus = get_campus(campus_key)
    bounds = campus["bounds"]
    img = np.array(Image.open(os.path.join(BACKEND, "static", campus_key, "satellite.png")).convert("RGB"))
    H, W = img.shape[:2]
    span_lat = bounds["north"] - bounds["south"]
    span_lng = bounds["east"] - bounds["west"]
    mppx = abs(span_lng) * 111320.0 * math.cos(
        math.radians((bounds["north"] + bounds["south"]) / 2)) / W

    gen = load_generator()

    def px_to_latlng(px, py):
        lng = bounds["west"] + (px / W) * span_lng
        lat = bounds["north"] - (py / H) * span_lat
        return lat, lng

    tile_h = H // grid
    tile_w = W // grid
    overlap = 60  # px overlap so buildings on seams aren't cut
    raw = []
    for gy in range(grid):
        for gx in range(grid):
            y0 = max(0, gy * tile_h - overlap)
            y1 = min(H, (gy + 1) * tile_h + overlap)
            x0 = max(0, gx * tile_w - overlap)
            x1 = min(W, (gx + 1) * tile_w + overlap)
            tile = img[y0:y1, x0:x1]
            print(f"tile ({gy},{gx}) {tile.shape} ...", flush=True)
            masks = gen.generate(tile)
            for m in masks:
                seg = m["segmentation"]
                area = int(seg.sum())
                bx, by, bw, bh = m["bbox"]
                width_m = bw * mppx
                length_m = bh * mppx
                long_side = max(width_m, length_m)
                short_side = max(min(width_m, length_m), 1.0)
                if width_m < 5 or length_m < 5 or width_m > 220 or length_m > 220:
                    continue
                if long_side / short_side > 9.0:
                    continue
                if area / max(bw * bh, 1) < 0.35:
                    continue
                if not looks_like_roof(tile, seg):
                    continue
                ys, xs = np.where(seg)
                pts = np.column_stack([xs + x0, ys + y0]).astype(np.float32)
                (rcx, rcy), (rw, rh), angle = cv2.minAreaRect(pts)
                lat, lng = px_to_latlng(float(rcx), float(rcy))
                raw.append({
                    "lat": float(lat), "lng": float(lng),
                    "rw": float(rw), "rh": float(rh), "angle": float(angle),
                    "area": int(area),
                })
            print(f"  running total raw: {len(raw)}", flush=True)

    # De-duplicate: drop detections whose centers are within ~10 m of a kept one.
    kept = []
    mLat = 111320.0
    for d in sorted(raw, key=lambda z: -z["area"]):
        cy_m = d["lat"] * mLat
        cx_m = d["lng"] * mLat * math.cos(math.radians(d["lat"]))
        dup = False
        for k in kept:
            ky = k["lat"] * mLat
            kx = k["lng"] * mLat * math.cos(math.radians(k["lat"]))
            if (cx_m - kx) ** 2 + (cy_m - ky) ** 2 < 10.0 ** 2:
                dup = True
                break
        if not dup:
            kept.append(d)

    buildings = []
    for d in kept:
        # Rebuild polygon from center + rotated rect size in pixels -> latlng.
        (rcx_dummy) = 0
        # Convert size back to pixels for boxPoints
        rw_px = d["rw"]
        rh_px = d["rh"]
        # center in pixels
        cx_px = (d["lng"] - bounds["west"]) / span_lng * W
        cy_px = (bounds["north"] - d["lat"]) / span_lat * H
        box = cv2.boxPoints(((cx_px, cy_px), (rw_px, rh_px), d["angle"]))
        poly = []
        for px, py in box:
            poly.append([round(bounds["north"] - (float(py) / H) * span_lat, 6),
                         round(bounds["west"] + (float(px) / W) * span_lng, 6)])
        poly.append(poly[0])
        buildings.append({
            "lat": round(float(d["lat"]), 6), "lng": round(float(d["lng"]), 6),
            "area_px": int(d["area"]),
            "width_m": round(float(rw_px) * mppx, 1),
            "length_m": round(float(rh_px) * mppx, 1),
            "angle_deg": round(float(d["angle"]), 1),
            "polygon": poly,
            "type": "building",
            "source": "sam_vit_b_tiled",
        })

    print(f"Total unique rooftops: {len(buildings)} (raw {len(raw)})")
    cache_path = os.path.join(BACKEND, "static", campus_key, "detect_cache.json")
    data = {"trees": [], "buildings": [], "image_size": [H, W]}
    if os.path.exists(cache_path):
        with open(cache_path) as f:
            data = json.load(f)
    data["buildings"] = buildings
    # Atomic write: serialize fully to a temp file, then replace, so a crash
    # mid-write can never corrupt the real cache.
    tmp_path = cache_path + ".tmp"
    with open(tmp_path, "w") as f:
        json.dump(data, f)
    os.replace(tmp_path, cache_path)
    print(f"Wrote {len(buildings)} buildings (trees preserved: {len(data.get('trees', []))})")


if __name__ == "__main__":
    campus = sys.argv[1] if len(sys.argv) > 1 else "stanford"
    grid = int(sys.argv[2]) if len(sys.argv) > 2 else 3
    main(campus, grid)
