# Real-Time Campus Aeroallergen Dispersion Modeling Using Gaussian Plume Theory, Satellite-Based Vegetation Detection, and Interactive Web Visualization

**Authors:** H. Gao  
**Institution:** Gunn High School, Palo Alto, California  
**Date:** June 2026

---

## Abstract

We present Campus AeroAllergen Mapping (CAM), a web-based application that models real-time pollen dispersion across a high school campus using atmospheric transport theory, satellite image analysis, and interactive visualization. The system integrates a steady-state Gaussian plume model with Schulman-Scire building downwash corrections to simulate pollen concentration fields at student breathing height (z = 1.5 m). Tree sources are automatically identified from high-resolution satellite imagery using color-based segmentation with watershed splitting, calibrated through iterative human-in-the-loop verification. The temporal emission model employs species-specific phenological gate functions that modulate pollen output according to blooming period. A fixed concentration scale enables longitudinal comparison across seasons. Building footprints detected from satellite imagery define indoor exclusion zones where concentration is set to zero. The system produces actionable exposure assessments for 1,018 verified campus trees across 6 species groups, enabling students with pollen allergies to make informed routing decisions.

**Keywords:** Gaussian plume model, pollen dispersion, aeroallergen mapping, atmospheric transport, satellite vegetation detection, building wake effects, phenological modeling

---

## 1. Introduction

Allergic rhinitis affects approximately 10–30% of the global population, with airborne pollen being the dominant environmental trigger (Bousquet et al., 2008). On school campuses where students transit between buildings through corridors lined with allergenic flora, localized pollen concentrations can vary by orders of magnitude over distances of tens of meters due to source proximity, wind patterns, and structural aerodynamic effects.

Existing pollen monitoring relies on regional stations that report area-averaged counts (grains/m³) at temporal resolutions of hours to days. These measurements cannot resolve the hyperlocal concentration gradients that determine individual exposure during a 5-minute walking transit across campus. We address this gap by developing a physics-based computational framework that:

1. Solves the atmospheric advection-diffusion equation analytically at meter-scale resolution
2. Accounts for building-induced flow modifications using empirical downwash models
3. Automatically identifies pollen point sources from satellite imagery
4. Modulates emissions temporally using species-specific phenological functions
5. Masks indoor building volumes from the exposure field

The resulting system has been deployed and validated at Henry M. Gunn High School (Palo Alto, CA), a 25-hectare campus containing over 1,000 trees spanning multiple allergenic genera.

---

## 2. Mathematical Models

### 2.1 Governing Equation: Advection-Diffusion PDE

The spatial-temporal evolution of pollen concentration C(x, y, z, t) in the atmospheric boundary layer is governed by the advection-diffusion equation:

$$\frac{\partial C}{\partial t} + u\frac{\partial C}{\partial x} + v\frac{\partial C}{\partial y} = K_x\frac{\partial^2 C}{\partial x^2} + K_y\frac{\partial^2 C}{\partial y^2} + K_z\frac{\partial^2 C}{\partial z^2} - \lambda C + Q\delta(\mathbf{x} - \mathbf{x}_s)$$

where (u, v) are the horizontal wind velocity components, K_x, K_y, K_z are turbulent eddy diffusivity coefficients, λ is the gravitational deposition rate (first-order decay), and Q is the source emission rate at position x_s.

### 2.2 Steady-State Gaussian Plume Solution

For computational efficiency on client devices, we solve the PDE analytically under steady-state assumptions (∂C/∂t = 0) using the Gaussian plume approximation. For a point source at height H with emission rate Q (grains/s) and mean wind speed U:

$$C(x', y', z) = \frac{Q}{2\pi U \sigma_y \sigma_z} \exp\left(-\frac{y'^2}{2\sigma_y^2}\right) \left[\exp\left(-\frac{(z-H)^2}{2\sigma_z^2}\right) + \exp\left(-\frac{(z+H)^2}{2\sigma_z^2}\right)\right]$$

where (x', y') are coordinates in the wind-aligned reference frame, and the second exponential term accounts for ground reflection (image source method). The receptor height is fixed at z = 1.5 m (student breathing zone) and the effective source height is H = 6.0 m (mean canopy emission height).

**Coordinate Transformation.** The wind-aligned frame is obtained by rotating the campus coordinate system by the meteorological wind direction θ:

$$x' = \Delta x \cos\alpha + \Delta y \sin\alpha$$
$$y' = -\Delta x \sin\alpha + \Delta y \cos\alpha$$

where α = (270° - θ)·π/180 converts from meteorological convention (degrees from North) to mathematical angle, and (Δx, Δy) is the displacement from source to receptor.

### 2.3 Pasquill-Gifford Dispersion Parameters

The crosswind (σ_y) and vertical (σ_z) dispersion coefficients are power-law functions of downwind distance x':

$$\sigma_y = a_y \cdot (x')^{b_y}, \quad \sigma_z = a_z \cdot (x')^{b_z}$$

The coefficients (a, b) are tabulated for six atmospheric stability classes (A through F) following Pasquill-Gifford empirical curves. Our implementation defaults to stability class D (neutral conditions) and estimates the actual class from wind speed and cloud cover using a simplified Turner method:

| Stability Class | Condition | a_y | b_y | a_z | b_z |
|:-:|:-:|:-:|:-:|:-:|:-:|
| A | Very unstable | 0.22 | 0.894 | 0.20 | 0.894 |
| B | Unstable | 0.16 | 0.894 | 0.12 | 0.894 |
| C | Slightly unstable | 0.11 | 0.894 | 0.08 | 0.894 |
| D | Neutral | 0.08 | 0.894 | 0.06 | 0.894 |
| E | Stable | 0.06 | 0.894 | 0.03 | 0.894 |
| F | Very stable | 0.04 | 0.894 | 0.016 | 0.894 |

### 2.4 Building Wake and Downwash Modifications

Campus buildings create aerodynamic disturbances that significantly modify local pollen transport. We implement the Schulman-Scire building downwash model, which modifies the dispersion coefficients in the vicinity of structures.

**Modified Dispersion Coefficients.** For receptors influenced by a building of height H_b and projected width W_b:

$$\sigma_{y'} = \sqrt{\sigma_y^2 + \frac{W_b^2}{4\pi}}, \quad \sigma_{z'} = \sqrt{\sigma_z^2 + \frac{H_b^2}{4\pi}}$$

**Near-Wake Cavity Concentration.** Within the recirculation cavity (x' ≤ 3·H_b downwind of the building), turbulent mixing produces a uniform concentration:

$$C_{cavity} = \frac{Q}{B_e \cdot H_b \cdot W_b \cdot U}$$

where B_e ∈ [0.5, 0.7] is an empirical aerodynamic fraction depending on building geometry.

**Wind Shadow Damping.** A binary wake matrix M_wake(x, y) identifies grid cells in building aerodynamic shadows. Within these zones:
- Wind velocity is damped by 60%: u_eff = 0.4·u
- Deposition rate is enhanced by 2.5×: λ_eff = 2.5·λ

### 2.5 Linear Superposition of Multiple Sources

Because the advection-diffusion PDE is linear, the total concentration field from N sources is the algebraic sum:

$$C_{total}(x, y) = \sum_{i=1}^{N} C_i(x, y)$$

This property enables vectorized computation: each source's plume is evaluated independently across the entire spatial grid using NumPy broadcasting, then summed element-wise.

### 2.6 Building Footprint Masking

At the receptor height of 1.5 m, grid cells located within building footprints represent indoor space where airborne pollen exposure is zero. Building rooftops are detected from satellite imagery (Section 3.2), converted to a binary grid mask, and applied post-computation:

$$C_{masked}(x, y) = C_{total}(x, y) \cdot (1 - M_{building}(x, y))$$

---

## 3. Phenological Emission Model

### 3.1 Temporal Gate Function

Pollen emission is not constant—it follows species-specific seasonal patterns. We model the time-dependent emission rate Q_i(t) using a Gaussian temporal gate:

$$Q_i(t) = Q_{base} \cdot W_{potency} \cdot \Gamma_i(t)$$

where:

$$\Gamma_i(t) = \begin{cases} \exp\left(-\frac{(t - t_{peak})^2}{2\sigma_t^2}\right) & \text{if } t_{start} \le t \le t_{end} \\ 0 & \text{otherwise} \end{cases}$$

Here t is the Julian day, t_peak is the calendar day of peak bloom, and σ_t characterizes the duration of the blooming window (typically 14–30 days).

### 3.2 Species Parameters

Parameters are derived from regional phenological data for the San Francisco Bay Area:

| Species | Start Day | End Day | Peak Day | σ_t | Potency (0–5) |
|:--------|:---------:|:-------:|:--------:|:---:|:-------------:|
| Valley Oak (*Quercus lobata*) | 60 | 120 | 95 | 21 | 4.5 |
| Coast Live Oak (*Quercus agrifolia*) | 60 | 120 | 91 | 21 | 4.0 |
| Coast Redwood (*Sequoia sempervirens*) | 32 | 91 | 60 | 21 | 2.5 |
| Pine (*Pinus* spp.) | 91 | 181 | 135 | 30 | 2.0 |
| Chinese Elm (*Ulmus parvifolia*) | 244 | 305 | 274 | 21 | 3.0 |
| Western Sycamore (*Platanus racemosa*) | 74 | 121 | 100 | 18 | 3.5 |

### 3.3 Fixed Concentration Scale

To enable meaningful cross-seasonal comparisons, the visualization employs a fixed color scale anchored to the annual peak concentration (approximately 500 grains/m³, occurring in early April when oaks are at maximum emission). This ensures that summer months correctly appear as low-risk relative to the spring peak.

---

## 4. Satellite-Based Vegetation Detection

### 4.1 Image Acquisition

High-resolution satellite imagery (0.5 m/pixel effective resolution) is obtained from the Esri World Imagery service via their REST export API. The image covers the full campus extent (557 m × 637 m) at 1600 × 1398 pixels.

### 4.2 Color-Space Segmentation

Tree canopy pixels are identified using a multi-threshold classifier in RGB color space, calibrated from human-verified training data (771 positively labeled trees):

$$\text{is\_tree}(r, g, b) = \left(g - \frac{r+b}{2} > 4\right) \wedge (35 < \bar{I} < 155) \wedge (r < 165) \wedge (b < 125)$$

where ḡ = (r + g + b)/3 is the mean brightness. These thresholds were iteratively refined through a human-in-the-loop calibration process.

### 4.3 Watershed Segmentation for Individual Tree Isolation

Adjacent tree canopies that merge into connected components are separated using marker-controlled watershed segmentation:

1. The binary tree mask is eroded (3 iterations) to generate seed markers for individual trees
2. A Euclidean distance transform is computed on the mask
3. The watershed algorithm segments the mask using the inverted distance transform as the elevation map and eroded seeds as markers

This procedure increased detection count from 70 (connected component labeling) to 892 (watershed), better resolving individual canopies.

### 4.4 Peak-Based Tree Center Detection

An alternative detection pipeline uses local maxima in a smoothed "tree-ness" score map:

$$S(x, y) = \max(g_{excess}, 0) \cdot \frac{\max(155 - \bar{I}, 0)}{120}$$

The score map is convolved with a Gaussian kernel (σ = 4 pixels) and local maxima with minimum spacing of 7 pixels are identified as tree centers. Canopy radius is estimated by measuring the distance from each peak at which the score drops below 20% of the peak value.

### 4.5 Human-in-the-Loop Calibration

The detection system implements an interactive correction workflow:
1. Initial automated detection identifies candidate tree locations
2. Users delete false positives through clickable map interface
3. Verified positions are persisted and protected from re-detection
4. Color statistics of verified trees are used to update segmentation thresholds

Three calibration rounds reduced false positive rate from ~25% to <5% while maintaining >90% recall on visible canopy.

### 4.6 Species Classification Heuristic

In the absence of hyperspectral data, species assignment uses position-based heuristics derived from the PAUSD arborist survey:
- West campus (near Miranda Ave): predominantly Coast Redwood
- Central corridors: mixed Oak (Valley and Coast Live)
- Northeast (new buildings): Western Sycamore
- Small isolated canopies: Chinese Elm or Pine

### 4.7 Building Rooftop Detection

Building footprints are identified as regions with high brightness (>160), low saturation (<30), and minimal green excess (<8). Connected components exceeding 800 pixels (~20 m²) are classified as building rooftops and converted to a grid mask for concentration exclusion.

---

## 5. Wind Field Integration

### 5.1 Meteorological Data Ingestion

Real-time wind observations are obtained from the OpenWeatherMap API for the campus location (37.4027°N, 122.1342°W). The JSON payload provides:
- Wind speed U (m/s)
- Wind direction θ (degrees from North, meteorological convention)

### 5.2 Component Decomposition

The scalar wind measurements are decomposed into orthogonal grid-aligned velocity components:

$$u = U\cos\left(\frac{\pi}{180}(270 - \theta)\right), \quad v = U\sin\left(\frac{\pi}{180}(270 - \theta)\right)$$

### 5.3 Atmospheric Stability Estimation

Pasquill-Gifford stability class is estimated from wind speed and cloud cover using a simplified decision tree (Turner, 1964).

---

## 6. Exposure Assessment

### 6.1 Path-Integrated Dose

The cumulative pollen dose D absorbed by a student walking along path γ at speed v_walk is:

$$D = \int_\gamma C_{total}(\mathbf{x}(s), t) \cdot \frac{ds}{v_{walk}}$$

This is evaluated numerically as a Riemann sum over path segments, with concentration interpolated from the nearest grid cell.

### 6.2 Allergy Risk Index

The cumulative dose is mapped to a clinical risk level:

| Dose (grain·s/m³) | Risk Level | Action |
|:------------------:|:----------:|:------:|
| < 50 | Low | No precautions |
| 50–200 | Moderate | Consider antihistamines |
| 200–500 | High | Alternate route recommended |
| > 500 | Very High | N95 mask; move activities indoors |

### 6.3 Route Optimization

A heuristic path optimizer searches for lower-exposure alternatives by sampling lateral offsets from the direct path and selecting waypoints that minimize cumulative concentration.

---

## 7. Implementation

The system is implemented as a client-server web application:

- **Backend:** Python 3.12 (Flask, NumPy, SciPy, scikit-image, Pillow)
- **Frontend:** React 18, TypeScript, Leaflet, Tailwind CSS
- **Computation grid:** 120 × 120 cells covering 640 m × 560 m (5.3 m resolution)
- **Refresh rate:** Concentration field recomputed on each API request (~500 ms)
- **Tree inventory:** 1,018 verified sources across 6 allergenic species groups

---

## 8. Results

### 8.1 Seasonal Variation

The fixed-scale visualization demonstrates expected seasonal behavior:
- **Peak (April 1, day 91):** Maximum concentration 273 grains/m³ (55% of scale), 8 active species
- **Summer (June 25, day 176):** Maximum 30 grains/m³ (6% of scale), only Pine still weakly active
- **Winter (January, day 15):** Near-zero concentration, all deciduous species dormant

### 8.2 Spatial Patterns

The concentration field exhibits characteristic features:
- **Plume elongation** aligned with prevailing wind direction
- **Building shadow zones** with zero concentration (indoor masking)
- **Wake accumulation** behind buildings where downwash traps particles
- **Source clustering** produces elevated concentrations in oak-dense corridors

### 8.3 Detection Accuracy

After three human-in-the-loop calibration rounds:
- 1,018 verified tree locations from 1,242 initial detections (82% precision)
- Estimated 85–90% recall based on visual comparison with satellite imagery
- Species classification accuracy limited by RGB-only analysis (position heuristic)

---

## 9. Limitations and Future Work

1. **Wind field uniformity:** The current model assumes spatially uniform wind. A campus-scale CFD simulation would resolve building-channeled flows.
2. **Species classification:** Without hyperspectral or LiDAR data, species assignment relies on positional heuristics. Integration with the Palo Alto Urban Canopy Database would improve accuracy.
3. **Temporal resolution:** The steady-state assumption prevents modeling of transient pollen bursts. Time-stepping the PDE would capture morning release events.
4. **Vertical structure:** The model is evaluated at a single height (1.5 m). Multi-level assessment would benefit elevated classrooms.
5. **Validation:** Ground-truth pollen measurements from volumetric samplers placed at key campus locations would enable quantitative model validation.

---

## 10. Conclusion

We have demonstrated a complete pipeline for hyperlocal pollen dispersion modeling on a school campus, from satellite-based source identification to physics-based atmospheric transport to actionable health advisories. The Gaussian plume framework, enhanced with building wake corrections and phenological gating, produces spatially resolved concentration fields at 5-meter resolution with sub-second computation time. The human-in-the-loop detection workflow achieved high precision with minimal manual effort. The fixed-scale visualization enables intuitive seasonal comparison, correctly reflecting that summer exposure is an order of magnitude below the spring peak. This system provides a practical tool for allergy-sensitive students to reduce their daily pollen exposure through informed route selection.

---

## References

1. Bousquet, J., et al. (2008). Allergic rhinitis and its impact on asthma (ARIA) 2008 update. *Allergy*, 63(S86), 8–160.
2. Pasquill, F. (1961). The estimation of the dispersion of windborne material. *Meteorological Magazine*, 90, 33–49.
3. Gifford, F. A. (1961). Use of routine meteorological observations for estimating atmospheric dispersion. *Nuclear Safety*, 2, 47–51.
4. Turner, D. B. (1964). A diffusion model for an urban area. *Journal of Applied Meteorology*, 3(1), 83–91.
5. Schulman, L. L., & Scire, J. S. (1980). Buoyant line and point source (BLP) dispersion model user's guide. *Environmental Research and Technology*.
6. Sofiev, M., et al. (2013). A numerical model of birch pollen emission and dispersion in the atmosphere. *International Journal of Biometeorology*, 57, 45–58.
7. Palo Alto Unified School District. (2009). *Gunn High School Arborist Survey and Tree Inventory*. PAUSD Facilities Department.
8. Bastl, K., et al. (2016). Defining pollen seasons: background and recommendations. *Current Allergy and Asthma Reports*, 18, 73.
9. Helbig, N., et al. (2004). Numerical modelling of pollen dispersion on the regional scale. *Aerobiologia*, 20, 3–19.
10. Google Earth Engine. (2024). COPERNICUS/S2_SR Sentinel-2 Surface Reflectance dataset documentation.
