"""
Additive rooftop re-detection for a campus.

Runs the (improved) SAM detector, then ADDS only newly-detected rooftops that
do not overlap the campus's current corrected building set. Existing buildings
(including manual additions) are preserved exactly; deleted areas are not
re-populated because we never re-detect over what already exists.

Usage: python merge_sam_buildings.py <campus>
"""
import os
import sys
import json
import math
import numpy as np
from PIL import Image

BACKEND = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BACKEND)


def centroid_m(b, center_lat, center_lon, mplat, mplon):
    return ((b["lng"] - center_lon) * mplon, (b["lat"] - center_lat) * mplat)


def main(campus_key):
    from data.campus_data import get_campus
    from detect_buildings_sam import load_generator, looks_like_roof
    import cv2

    campus = get_campus(campus_key)
    bounds = campus["bounds"]
    cache_path = os.path.join(BACKEND, "static", campus_key, "detect_cache.json")
    with open(cache_path) as f:
        cache = json.load(f)
    existing = cache.get("buildings", [])

    center_lat = campus["center_lat"]
    center_lon = campus["center_lon"]
    mplat = 111320.0
    mplon = abs(bounds["east"] - bounds["west"]) * 111320.0 * math.cos(
        math.radians((bounds["north"] + bounds["south"]) / 2)) / abs(bounds["east"] - bounds["west"])

    existing_centroids = [centroid_m(b, center_lat, center_lon, mplat, mplon) for b in existing]

    img = np.array(Image.open(os.path.join(BACKEND, "static", campus_key, "satellite.png")).convert("RGB"))
    h, w = img.shape[:2]
    span_lat = bounds["north"] - bounds["south"]
    mppx = abs(bounds["east"] - bounds["west"]) * 111320.0 * math.cos(
        math.radians((bounds["north"] + bounds["south"]) / 2)) / w

    gen = load_generator()
    print("Generating masks...")
    masks = gen.generate(img)
    print(f"SAM proposed {len(masks)} masks")

    added = 0
    for m in masks:
        seg = m["segmentation"]
        area = int(seg.sum())
        x0, y0, bw, bh = m["bbox"]
        width_m = bw * mppx
        length_m = bh * span_lat * 111320.0 / h
        long_side = max(width_m, length_m)
        short_side = max(min(width_m, length_m), 1.0)
        if width_m < 6 or length_m < 6 or width_m > 210 or length_m > 210:
            continue
        if long_side / short_side > 8.0:
            continue
        if area / max(bw * bh, 1) < 0.40:
            continue
        if not looks_like_roof(img, seg):
            continue

        ys, xs = np.where(seg)
        pts = np.column_stack([xs, ys]).astype(np.float32)
        (rcx, rcy), (rw, rh), angle = cv2.minAreaRect(pts)
        # Centroid in local meters
        clng = bounds["west"] + (rcx / w) * (bounds["east"] - bounds["west"])
        clat = bounds["north"] - (rcy / h) * (bounds["north"] - bounds["south"])
        cx_m = (clng - center_lon) * mplon
        cy_m = (clat - center_lat) * mplat

        # Skip if this detection overlaps an existing building (within ~15 m).
        too_close = any(
            (cx_m - ex) ** 2 + (cy_m - ey) ** 2 < 15.0 ** 2
            for ex, ey in existing_centroids
        )
        if too_close:
            continue

        box = cv2.boxPoints(((rcx, rcy), (rw, rh), angle))
        polygon = []
        for px, py in box:
            plng = bounds["west"] + (float(px) / w) * (bounds["east"] - bounds["west"])
            plat = bounds["north"] - (float(py) / h) * (bounds["north"] - bounds["south"])
            polygon.append([round(plat, 6), round(plng, 6)])
        polygon.append(polygon[0])

        existing.append({
            "lat": round(clat, 6), "lng": round(clng, 6),
            "area_px": area,
            "width_m": round(rw * mppx, 1),
            "length_m": round(rh * mppx, 1),
            "angle_deg": round(float(angle), 1),
            "polygon": polygon,
            "type": "building",
            "source": "sam_vit_b",
        })
        existing_centroids.append((cx_m, cy_m))
        added += 1

    cache["buildings"] = existing
    with open(cache_path, "w") as f:
        json.dump(cache, f)
    print(f"Added {added} new rooftops. Total now: {len(existing)}")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "gunn")
