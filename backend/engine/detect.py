"""
Campus AeroAllergen Mapping (CAM) - Satellite Image Detection

Downloads satellite tile and uses color-based segmentation to detect:
- Buildings (gray/white/brown rooftops)
- Trees (green canopy areas)

Returns detected regions as lat/lng polygons for map overlay.
"""

import numpy as np
from PIL import Image
import requests
from io import BytesIO
from scipy import ndimage
from skimage import measure
from typing import List, Dict, Tuple
import math

# Campus bounds
NORTH = 37.4038
SOUTH = 37.3988
WEST = -122.1372
EAST = -122.1300

# Species classification based on canopy size and campus position
# Based on PAUSD arborist survey data
SPECIES_INFO = {
    "valley_oak": {"name": "Valley Oak", "scientific": "Quercus lobata", "family": "Fagaceae", "potency": 4.5},
    "coast_live_oak": {"name": "Coast Live Oak", "scientific": "Quercus agrifolia", "family": "Fagaceae", "potency": 4.0},
    "redwood": {"name": "Coast Redwood", "scientific": "Sequoia sempervirens", "family": "Cupressaceae", "potency": 2.5},
    "eucalyptus": {"name": "Eucalyptus", "scientific": "Eucalyptus spp.", "family": "Myrtaceae", "potency": 2.0},
    "pine": {"name": "Pine", "scientific": "Pinus spp.", "family": "Pinaceae", "potency": 2.0},
    "chinese_elm": {"name": "Chinese Elm", "scientific": "Ulmus parvifolia", "family": "Ulmaceae", "potency": 3.0},
    "sycamore": {"name": "Western Sycamore", "scientific": "Platanus racemosa", "family": "Platanaceae", "potency": 3.5},
    "perennial_grass": {"name": "Turf Grass", "scientific": "Poaceae spp.", "family": "Poaceae", "potency": 4.0},
}


def classify_tree_by_size_and_position(radius_m: float, lat: float, lng: float) -> str:
    """
    Classify tree species based on canopy radius and position on campus.
    Uses heuristics from the PAUSD arborist survey distribution.
    """
    # Athletic fields (south) - grass
    if lat < 37.4005:
        if radius_m > 15:
            return "perennial_grass"
    
    # West side near Spangenberg (-122.136+) - redwood grove
    if lng < -122.1358:
        if radius_m > 8:
            return "redwood"
        return "redwood"
    
    # Large canopy (>12m radius) - likely mature oak
    if radius_m > 12:
        if lng < -122.135:
            return "valley_oak"
        return "coast_live_oak"
    
    # Medium canopy (6-12m)
    if radius_m > 6:
        # NE area - sycamores (near new A/B buildings)
        if lat > 37.403 and lng > -122.133:
            return "sycamore"
        # Central - oaks
        if lng > -122.134:
            return "coast_live_oak"
        return "valley_oak"
    
    # Small canopy (<6m)
    if lat > 37.403:
        return "chinese_elm"
    if lng > -122.133:
        return "pine"
    return "coast_live_oak"


def fetch_satellite_tile(zoom: int = 17) -> np.ndarray:
    """
    Fetch satellite imagery from Esri World Imagery for the campus area.
    Returns RGB numpy array with correct geographic proportions.
    """
    # Calculate proper aspect ratio from geographic extent
    lat_span = NORTH - SOUTH  # degrees
    lng_span = EAST - WEST    # degrees
    # Convert to meters for aspect ratio
    height_m = lat_span * 111320
    width_m = abs(lng_span) * 111320 * math.cos(math.radians((NORTH + SOUTH) / 2))
    
    # Image dimensions matching geographic aspect ratio
    base_size = 1600
    if width_m > height_m:
        width = base_size
        height = int(base_size * height_m / width_m)
    else:
        height = base_size
        width = int(base_size * width_m / height_m)

    bbox = f"{WEST},{SOUTH},{EAST},{NORTH}"
    url = (
        f"https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/export"
        f"?bbox={bbox}&bboxSR=4326&size={width},{height}"
        f"&imageSR=4326&format=png&f=image"
    )

    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        img = Image.open(BytesIO(response.content)).convert("RGB")
        return np.array(img)
    except Exception as e:
        print(f"Failed to fetch satellite tile: {e}")
        return np.zeros((height, width, 3), dtype=np.uint8)


def pixel_to_latlng(px: int, py: int, img_width: int, img_height: int) -> Tuple[float, float]:
    """Convert pixel coordinates to lat/lng."""
    lng = WEST + (px / img_width) * (EAST - WEST)
    lat = NORTH - (py / img_height) * (NORTH - SOUTH)
    return lat, lng


def detect_trees(img: np.ndarray, min_area: int = 60) -> List[Dict]:
    """
    Detect tree canopy using calibrated color segmentation.
    Thresholds learned from user-verified trees:
      green_excess 5-36, brightness 40-144, R<160, B<115
    """
    r, g, b = img[:, :, 0].astype(float), img[:, :, 1].astype(float), img[:, :, 2].astype(float)

    green_excess = g - (r + b) / 2
    brightness = (r + g + b) / 3

    # Calibrated thresholds from user feedback
    is_tree = (
        (green_excess > 4) &
        (brightness > 35) &
        (brightness < 155) &
        (r < 165) &
        (b < 125)
    )

    # Clean up
    from scipy.ndimage import binary_opening, binary_closing, binary_erosion
    mask = binary_closing(is_tree, iterations=1)
    mask = binary_opening(mask, iterations=1)

    # Use erosion + re-labeling to split merged canopies
    eroded = binary_erosion(mask, iterations=3)
    seeds, _ = ndimage.label(eroded)
    
    # Watershed from seeds to split touching canopies
    from scipy.ndimage import distance_transform_edt
    dist = distance_transform_edt(mask)
    from skimage.segmentation import watershed
    labeled = watershed(-dist, seeds, mask=mask)
    num_features = labeled.max()
    h, w = img.shape[:2]

    trees = []
    for i in range(1, num_features + 1):
        region = (labeled == i)
        area = np.sum(region)
        if area < min_area:
            continue

        # Get centroid
        ys, xs = np.where(region)
        cy, cx = np.mean(ys), np.mean(xs)
        lat, lng = pixel_to_latlng(cx, cy, w, h)

        # Estimate radius in meters
        radius_px = math.sqrt(area / math.pi)
        radius_m = radius_px * (NORTH - SOUTH) * 111320 / h

        # Skip overly large detections (likely fields, not individual trees)
        if radius_m > 50:
            continue

        # Generate simple circle polygon centered at centroid
        r_lat = radius_px * (NORTH - SOUTH) / h
        r_lng = radius_px * (EAST - WEST) / w

        num_pts = 20
        polygon = []
        for k in range(num_pts + 1):
            theta = 2 * math.pi * k / num_pts
            polygon.append([
                round(lat + r_lat * math.sin(theta), 6),
                round(lng + r_lng * math.cos(theta), 6),
            ])

        trees.append({
            "lat": round(lat, 6),
            "lng": round(lng, 6),
            "area_px": int(area),
            "radius_m": round(radius_m, 1),
            "polygon": polygon,
            "type": "tree",
            "species_key": classify_tree_by_size_and_position(radius_m, lat, lng),
        })

    return trees


def detect_buildings(img: np.ndarray, min_area: int = 200) -> List[Dict]:
    """
    Detect building rooftops using color segmentation.
    Buildings appear as gray, white, or tan flat surfaces.
    """
    r, g, b = img[:, :, 0].astype(float), img[:, :, 1].astype(float), img[:, :, 2].astype(float)

    brightness = (r + g + b) / 3
    saturation = np.max(img, axis=2).astype(float) - np.min(img, axis=2).astype(float)

    # Buildings: low saturation (grayish), medium-to-high brightness
    is_building = (saturation < 50) & (brightness > 90) & (brightness < 230)

    # Exclude strongly green areas (vegetation)
    green_excess = g - (r + b) / 2
    is_building = is_building & (green_excess < 20)

    from scipy.ndimage import binary_opening, binary_closing
    mask = binary_opening(is_building, iterations=2)
    mask = binary_closing(mask, iterations=2)

    labeled, num_features = ndimage.label(mask)
    h, w = img.shape[:2]

    buildings = []
    for i in range(1, num_features + 1):
        region = (labeled == i)
        area = np.sum(region)
        if area < min_area or area > 40000:
            continue

        ys, xs = np.where(region)
        cy, cx = np.mean(ys), np.mean(xs)
        lat, lng = pixel_to_latlng(cx, cy, w, h)

        min_y, max_y = np.min(ys), np.max(ys)
        min_x, max_x = np.min(xs), np.max(xs)

        width_m = (max_x - min_x) * abs(EAST - WEST) * 88000 / w
        height_m = (max_y - min_y) * (NORTH - SOUTH) * 111320 / h

        # Skip if too large (merged regions)
        if width_m > 120 or height_m > 120:
            continue

        contours = measure.find_contours(region.astype(float), 0.5)
        if not contours:
            continue

        # Fit a minimum bounding rectangle instead of using raw contour
        contour = max(contours, key=len)
        # Get the 4 corners of a bounding rectangle
        min_lat, min_lng = pixel_to_latlng(min_x, max_y, w, h)
        max_lat, max_lng = pixel_to_latlng(max_x, min_y, w, h)
        
        polygon = [
            [min_lat, min_lng],
            [min_lat, max_lng],
            [max_lat, max_lng],
            [max_lat, min_lng],
            [min_lat, min_lng],
        ]

        buildings.append({
            "lat": round(lat, 6),
            "lng": round(lng, 6),
            "area_px": int(area),
            "width_m": round(abs(width_m), 1),
            "height_m": round(abs(height_m), 1),
            "polygon": polygon,
            "type": "building",
        })

    return buildings


def run_detection() -> Dict:
    """Run full detection pipeline and return results."""
    print("Fetching satellite imagery...")
    img = fetch_satellite_tile()

    if img.max() == 0:
        return {"trees": [], "buildings": [], "error": "Failed to fetch imagery"}

    print(f"Image shape: {img.shape}")
    print("Detecting trees...")
    trees = detect_trees(img)
    print(f"Found {len(trees)} tree canopy regions")

    print("Detecting buildings...")
    buildings = detect_buildings(img)
    print(f"Found {len(buildings)} building regions")

    return {
        "trees": trees,
        "buildings": buildings,
        "image_size": list(img.shape[:2]),
        "bounds": {"north": NORTH, "south": SOUTH, "east": EAST, "west": WEST},
    }


if __name__ == "__main__":
    results = run_detection()
    print(f"\nDetection complete:")
    print(f"  Trees: {len(results['trees'])}")
    print(f"  Buildings: {len(results['buildings'])}")
