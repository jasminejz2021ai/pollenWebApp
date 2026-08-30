"""Materials and Methods, Acknowledgments, References, and Figures."""

import os


def add_methods(doc, docs_dir, heading, para, title_line):
    heading(doc, "MATERIALS AND METHODS")

    para(doc, "Atmospheric dispersion model", italic=True)
    para(doc,
        "Pollen transport was modeled with the steady-state solution of the "
        "atmospheric advection-diffusion equation, the Gaussian plume model (3, 4). "
        "For a single source, the concentration at a receptor is "
        "C(x',y',z) = [Q / (2 pi U sigma_y sigma_z)] * exp(-y'^2 / 2 sigma_y^2) * V(z), "
        "where Q is the source emission rate (grains/s), U is the mean wind speed "
        "(m/s), x' and y' are downwind and crosswind distances in a wind-aligned "
        "coordinate frame, and sigma_y and sigma_z are the crosswind and vertical "
        "plume spreads. The vertical term V(z) includes a ground-reflection image "
        "source so that no pollen is lost through the ground. Receptor height was "
        "fixed at z = 1.5 m (student breathing height) and effective source height "
        "at H = 6.0 m (mean campus canopy).")

    para(doc,
        "Plume spreads followed Pasquill-Gifford power laws, sigma_y = a_y (x')^b_y "
        "and sigma_z = a_z (x')^b_z, with coefficients tabulated for atmospheric "
        "stability classes A-F (Table 1). Stability was estimated from wind speed "
        "and cloud cover using Turner's method (5). Species-dependent gravitational "
        "settling was included via Stokes' law, tilting the plume centerline "
        "downward with distance, and building wakes were represented using the "
        "Schulman-Scire downwash model (6), which inflates the dispersion "
        "coefficients near structures and imposes a uniform cavity concentration "
        "within the near-wake recirculation zone. Because the governing equation is "
        "linear, the total field from all N sources was obtained by superposition, "
        "C_total = sum of C_i, evaluated with vectorized array operations over a "
        "120 x 120 spatial grid (5.3 m resolution). Concentration over detected "
        "building footprints was set to zero to represent indoor exclusion.")

    para(doc, "Phenological emission model", italic=True)
    para(doc,
        "Each species' time-varying emission was modeled as Q_i(t) = Q_base,i * W_i "
        "* Gamma_i(t), where Q_base,i is the peak base emission rate (grains/s), W_i "
        "is a dimensionless allergen potency weight (0-5), and Gamma_i(t) is a "
        "truncated Gaussian temporal gate, Gamma_i(t) = exp(-(t - t_peak)^2 / "
        "(2 sigma_t^2)) within the pollination window [t_start, t_end] and zero "
        "otherwise, with t the Julian day of year. Base emission rates, potency "
        "weights, and phenological windows for the six campus genera were taken from "
        "aerobiological literature and Bay Area regional data (7) (Table 2). "
        "Relative humidity, obtained from the weather service, further suppressed "
        "emission (anthers require drying to dehisce) and increased grain settling "
        "through hygroscopic swelling.")

    para(doc, "Satellite-based vegetation detection", italic=True)
    para(doc,
        "Campus satellite imagery (approximately 0.5 m/pixel) was obtained from the "
        "Esri World Imagery REST export service for the campus bounding box "
        "(557 m x 637 m; 1600 x 1398 pixels). Tree-canopy pixels were classified "
        "with color thresholds calibrated on human-verified samples using green "
        "excess g_e = g - (r + b)/2 and mean brightness. Adjacent canopies were "
        "separated using marker-controlled watershed segmentation (8): the binary "
        "canopy mask was eroded to form seed markers, a Euclidean distance transform "
        "was computed, and the watershed algorithm segmented individual canopies. "
        "Each detected canopy was assigned a species using a size- and "
        "position-based heuristic. Detected canopies were converted from pixel "
        "coordinates to latitude/longitude and then to local meters relative to the "
        "campus center for use as plume sources. Building rooftops were detected as "
        "low-saturation, high-brightness connected regions and used to define the "
        "indoor exclusion mask.")

    para(doc, "Human-in-the-loop calibration", italic=True)
    para(doc,
        "Detection was refined iteratively: automated detection proposed candidate "
        "trees, a reviewer removed false positives through an interactive map "
        "interface, and the verified positions were persisted and used to update the "
        "detection thresholds. Three rounds reduced the false-positive rate from "
        "approximately 25% to below 5%.")

    para(doc, "Exposure assessment", italic=True)
    para(doc,
        "Cumulative exposure (dose) along a walking path was computed by numerically "
        "integrating the concentration field along the route at a walking speed of "
        "1.4 m/s, D = sum over path segments of C(x_k) * delta t_k. Dose was mapped "
        "to interpretable risk levels (Low, Moderate, High, Very High) using fixed "
        "thresholds.")

    para(doc, "Implementation and availability", italic=True)
    para(doc,
        "The computational engine was implemented in Python (NumPy, SciPy, "
        "scikit-image) behind a Flask web service, with a React/TypeScript front end "
        "rendering an interactive campus map and pollen heatmap. Weather inputs were "
        "obtained from a public weather API, with mock data used when no API key was "
        "configured. The complete source code and campus data are available at "
        "https://github.com/jasminejz2021ai/pollenWebApp, and a live deployment is "
        "available at https://pollen-web-app-seven.vercel.app/.")

    para(doc, "")

    # ---------------- Acknowledgments ----------------
    heading(doc, "ACKNOWLEDGMENTS")
    para(doc,
        "The author thanks the Palo Alto Unified School District for access to "
        "campus tree inventory records. [Add any mentors, teachers, or advisors who "
        "assisted but are not authors. Per JEI policy, disclose any assistance here.]")
    para(doc, "")

    # ---------------- References ----------------
    heading(doc, "REFERENCES")
    refs = [
        "Bousquet, J., Khaltaev, N., Cruz, A. A., et al. Allergic rhinitis and its "
        "impact on asthma (ARIA) 2008 update. Allergy 63 (Suppl. 86), 8-160 (2008).",
        "Sofiev, M., Siljamo, P., Ranta, H., Linkosalo, T., et al. A numerical model "
        "of birch pollen emission and dispersion in the atmosphere. International "
        "Journal of Biometeorology 57, 45-58 (2013).",
        "Pasquill, F. The estimation of the dispersion of windborne material. "
        "Meteorological Magazine 90, 33-49 (1961).",
        "Gifford, F. A. Use of routine meteorological observations for estimating "
        "atmospheric dispersion. Nuclear Safety 2, 47-51 (1961).",
        "Turner, D. B. A diffusion model for an urban area. Journal of Applied "
        "Meteorology 3, 83-91 (1964).",
        "Schulman, L. L. and Scire, J. S. Buoyant line and point source (BLP) "
        "dispersion model user's guide. Technical report, Environmental Research and "
        "Technology (1980).",
        "Bastl, K., Kmenta, M. and Berger, U. Defining pollen seasons: background and "
        "recommendations. Current Allergy and Asthma Reports 18, 73 (2016).",
        "Beucher, S. and Meyer, F. The morphological approach to segmentation: the "
        "watershed transformation. In Mathematical Morphology in Image Processing, "
        "433-481 (1992).",
    ]
    for i, r in enumerate(refs, 1):
        para(doc, f"{i}. {r}")
    para(doc, "")

    # ---------------- Figures ----------------
    heading(doc, "FIGURES")
    figs = [
        ("fig1_wind_stability.png",
         "Figure 1. Modeled Gaussian plume concentration fields under varying "
         "conditions. Top row: effect of wind speed at neutral stability (class D); "
         "stronger winds dilute and elongate the plume. Bottom row: effect of "
         "atmospheric stability at fixed wind speed (3.5 m/s); unstable conditions "
         "(A) spread pollen rapidly, while stable conditions (F) confine it in a "
         "narrow, concentrated plume."),
        ("fig2_species_comparison.png",
         "Figure 2. Species-dependent plume shapes resulting from different grain "
         "settling velocities. Small, light Oak grains produce wide, far-reaching "
         "plumes, whereas large, heavy Pine grains produce intense but localized "
         "concentrations near the source tree."),
        ("fig3_phenology.png",
         "Figure 3. Phenological emission model. (a) Temporal gate functions "
         "Gamma_i(t) showing blooming intensity across the year for each species. "
         "(b) Effective allergenic emission Q_eff(t) = Q_base x W x Gamma(t). The "
         "dashed line marks June 25, when most tree species are dormant and only "
         "Pine retains weak late-season emission."),
        ("fig4_humidity.png",
         "Figure 4. Modeled humidity effects on pollen behavior. (a) Emission "
         "suppression factor: pollen release drops sharply above 50% relative "
         "humidity. (b) Hygroscopic swelling increases grain diameter at high "
         "humidity. (c) Resulting increase in gravitational settling velocity."),
    ]
    from docx.shared import Inches
    for fname, caption in figs:
        path = os.path.join(docs_dir, fname)
        if os.path.exists(path):
            doc.add_picture(path, width=Inches(6.0))
        para(doc, caption)
        para(doc, "")
