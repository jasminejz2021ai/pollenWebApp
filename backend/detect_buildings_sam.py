"""
Deep-learning rooftop detection using Segment Anything (SAM).

Runs LOCALLY at cache-generation time (not on the web server). SAM proposes
class-agnostic masks over a campus satellite image; we then keep only the masks
that look like building rooftops by color, size, and shape, and emit them as
lat/lng polygons compatible with the app's detect_cache.json "buildings" list.

Usage:
    python detect_buildings_sam.py <campus>       # gunn | stanford
It reads backend/static/<campus>/satellite.png and the campus bounds from
data.campus_data, and writes the "buildings" array back into
backend/static/<campus>/detect_cache.json (preserving "trees").
"""

import os
import sys
import json
import math
import numpy as np
from PIL import Image

BACKEND = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BACKEND)

MODEL_PATH = os.path.join(BACKEND, "models", "sam_vit_b_01ec64.pth")
MODEL_TYPE = "vit_b"


def load_generator():
    import torch
    from segment_anything import sam_model_registry, SamAutomaticMaskGenerator
    # Force CPU: SAM's automatic mask generator uses float64 internally, which
    # Apple's MPS backend does not support. CUDA works but is rarely present on
    # a Mac; CPU is correct and portable.
    device = "cuda" if torch.cuda.is_available() else "cpu"
    sam = sam_model_registry[MODEL_TYPE](checkpoint=MODEL_PATH)
    sam.to(device)
    print(f"SAM loaded on {device}")
    # Denser sampling and stricter thresholds improve rooftop recall/precision.
    return SamAutomaticMaskGenerator(
        model=sam,
        points_per_side=64,
        pred_iou_thresh=0.86,
        stability_score_thresh=0.90,
        min_mask_region_area=250,
    )


def pixel_to_latlng(px, py, w, h, bounds):
    lng = bounds["west"] + (px / w) * (bounds["east"] - bounds["west"])
    lat = bounds["north"] - (py / h) * (bounds["north"] - bounds["south"])
    return lat, lng


def looks_like_roof(img, seg):
    """Heuristic: gray/white or tan/tile roof color, not vegetation, in the mask."""
    ys, xs = np.where(seg)
    if len(ys) == 0:
        return False
    r = img[ys, xs, 0].astype(float)
    g = img[ys, xs, 1].astype(float)
    b = img[ys, xs, 2].astype(float)
    brightness = (r + g + b) / 3.0
    sat = np.maximum(np.maximum(r, g), b) - np.minimum(np.minimum(r, g), b)
    green_excess = g - (r + b) / 2.0
    # Gray/white roofs: low saturation, bright.
    gray = (sat < 50) & (brightness > 90) & (brightness < 240)
    # Warm roofs (Gunn/Stanford tan sandstone and red-tile): red dominant,
    # blue lowest. Loosened so pale-tan Quad roofs qualify.
    warm = (r >= g) & (g >= b) & ((r - b) > 8) & (brightness > 70) & (brightness < 220)
    roof_frac = np.mean(gray | warm)
    veg_frac = np.mean(green_excess > 15)
    return roof_frac > 0.55 and veg_frac < 0.30


def detect(campus_key):
    from data.campus_data import get_campus
    campus = get_campus(campus_key)
    bounds = campus["bounds"]

    img_path = os.path.join(BACKEND, "static", campus_key, "satellite.png")
    img = np.array(Image.open(img_path).convert("RGB"))
    h, w = img.shape[:2]
    span_lat = bounds["north"] - bounds["south"]
    mplon = abs(bounds["east"] - bounds["west"]) * 111320.0 * math.cos(
        math.radians((bounds["north"] + bounds["south"]) / 2))

    gen = load_generator()
    print("Generating masks (this can take a few minutes on CPU)...")
    masks = gen.generate(img)
    print(f"SAM proposed {len(masks)} masks")

    buildings = []
    for m in masks:
        seg = m["segmentation"]
        area = int(seg.sum())
        x0, y0, bw, bh = m["bbox"]
        width_m = bw * mplon / w
        length_m = bh * span_lat * 111320.0 / h
        long_side = max(width_m, length_m)
        short_side = max(min(width_m, length_m), 1.0)

        # Building-scale filters. Allow larger footprints for big structures
        # like Stanford's Main Quad wings (which can span ~180 m).
        if width_m < 6 or length_m < 6:
            continue
        if width_m > 210 or length_m > 210:
            continue
        if long_side / short_side > 8.0:
            continue
        # Compactness: mask should fill a good part of its bounding box.
        if area / max(bw * bh, 1) < 0.38:
            continue
        if not looks_like_roof(img, seg):
            continue

        # Rotated min-area rectangle captures angled roofs / parallelograms,
        # instead of an upright axis-aligned box.
        import cv2
        ys, xs = np.where(seg)
        pts = np.column_stack([xs, ys]).astype(np.float32)
        (rcx, rcy), (rw, rh), angle = cv2.minAreaRect(pts)
        box = cv2.boxPoints(((rcx, rcy), (rw, rh), angle))  # 4 corners in pixels
        polygon = []
        for px, py in box:
            plat, plng = pixel_to_latlng(float(px), float(py), w, h, bounds)
            polygon.append([round(plat, 6), round(plng, 6)])
        polygon.append(polygon[0])  # close the ring

        lat, lng = pixel_to_latlng(float(rcx), float(rcy), w, h, bounds)
        # Rotated-rectangle side lengths in meters (metric per pixel).
        m_per_px_x = mplon / w
        m_per_px_y = span_lat * 111320.0 / h
        m_per_px = (m_per_px_x + m_per_px_y) / 2.0
        rect_w_m = round(rw * m_per_px, 1)
        rect_l_m = round(rh * m_per_px, 1)

        buildings.append({
            "lat": round(lat, 6),
            "lng": round(lng, 6),
            "area_px": area,
            "width_m": rect_w_m,
            "length_m": rect_l_m,
            "angle_deg": round(float(angle), 1),
            "polygon": polygon,
            "type": "building",
            "source": "sam_vit_b",
        })

    print(f"Kept {len(buildings)} rooftop masks after filtering")

    cache_path = os.path.join(BACKEND, "static", campus_key, "detect_cache.json")
    data = {"trees": [], "buildings": [], "image_size": [h, w]}
    if os.path.exists(cache_path):
        with open(cache_path) as f:
            data = json.load(f)
    data["buildings"] = buildings
    with open(cache_path, "w") as f:
        json.dump(data, f)
    print(f"Wrote {len(buildings)} buildings into {cache_path}")


if __name__ == "__main__":
    campus = sys.argv[1] if len(sys.argv) > 1 else "gunn"
    detect(campus)
