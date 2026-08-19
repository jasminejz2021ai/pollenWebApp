"""
Campus AeroAllergen Mapping (CAM) - Tree Classifier

Remote sensing classification engine using temporal NDVI signatures
to identify tree genus from satellite time-series data.
"""

import numpy as np
from typing import Dict, List, Optional, Tuple


class CampusTreeClassifier:
    """
    Classifies tree genus from multi-month NDVI time-series profiles
    using Euclidean distance matching against known phenological signatures.
    """

    def __init__(self):
        # Bimonthly NDVI reference signatures (6 periods):
        # [Jan-Feb, Mar-Apr, May-Jun, Jul-Aug, Sep-Oct, Nov-Dec]
        self.reference_signatures: Dict[str, np.ndarray] = {
            "coast_live_oak": np.array([0.35, 0.75, 0.65, 0.60, 0.50, 0.40]),
            "redwood": np.array([0.65, 0.68, 0.70, 0.69, 0.66, 0.64]),
            "olive": np.array([0.40, 0.45, 0.78, 0.70, 0.55, 0.45]),
            "ginkgo": np.array([0.20, 0.60, 0.70, 0.65, 0.50, 0.25]),
            "california_black_walnut": np.array([0.25, 0.50, 0.72, 0.68, 0.45, 0.30]),
            "perennial_grass": np.array([0.30, 0.55, 0.75, 0.50, 0.35, 0.30]),
            "modesto_ash": np.array([0.22, 0.55, 0.72, 0.70, 0.48, 0.25]),
        }

        # Rule-based constraints for Palo Alto region
        self.regional_rules = {
            "high_temporal_volatility_spring": "coast_live_oak",
            "constant_high_baseline": "redwood",
            "late_spring_nir_shift": "olive",
        }

    def classify_coordinate_cluster(
        self, raw_ndvi_timeseries: List[float]
    ) -> Tuple[str, float]:
        """
        Classify a pixel cluster by computing Euclidean distance against
        all reference phenological signatures.

        Returns (genus_key, confidence_score).
        """
        observed = np.array(raw_ndvi_timeseries)
        best_match = "unknown"
        min_distance = float("inf")

        for genus, profile in self.reference_signatures.items():
            distance = np.linalg.norm(observed - profile)
            if distance < min_distance:
                min_distance = distance
                best_match = genus

        # Confidence: inverse normalized distance (0-1 scale)
        max_possible_dist = np.sqrt(6.0)  # max distance for unit vectors
        confidence = max(0.0, 1.0 - (min_distance / max_possible_dist))

        return best_match, round(confidence, 4)

    def classify_with_rules(
        self, raw_ndvi_timeseries: List[float]
    ) -> Tuple[str, float, str]:
        """
        Enhanced classification using both Euclidean matching and
        regional phenological rules.

        Returns (genus_key, confidence, rule_applied).
        """
        observed = np.array(raw_ndvi_timeseries)

        # Rule 1: High temporal volatility in March/April
        spring_delta = observed[1] - observed[0]  # Mar-Apr vs Jan-Feb
        if spring_delta > 0.35:
            return "coast_live_oak", 0.92, "high_temporal_volatility_spring"

        # Rule 2: High constant baseline (evergreen)
        std_dev = np.std(observed)
        mean_val = np.mean(observed)
        if std_dev < 0.04 and mean_val > 0.60:
            return "redwood", 0.95, "constant_high_baseline"

        # Rule 3: Late spring NIR shift (peak in May-Jun)
        if observed[2] > observed[1] and observed[2] - observed[0] > 0.30:
            return "olive", 0.85, "late_spring_nir_shift"

        # Fall back to Euclidean classification
        genus, confidence = self.classify_coordinate_cluster(raw_ndvi_timeseries)
        return genus, confidence, "euclidean_fallback"

    def batch_classify(
        self, pixel_clusters: List[Dict]
    ) -> List[Dict]:
        """
        Classify multiple coordinate clusters.

        pixel_clusters: list of dicts with keys:
            lat, lon, ndvi_timeseries (6-element list)

        Returns enriched list with classification results.
        """
        results = []
        for cluster in pixel_clusters:
            genus, confidence, rule = self.classify_with_rules(
                cluster["ndvi_timeseries"]
            )
            results.append({
                "lat": cluster["lat"],
                "lon": cluster["lon"],
                "genus_key": genus,
                "confidence": confidence,
                "classification_rule": rule,
                "ndvi_timeseries": cluster["ndvi_timeseries"],
            })
        return results
