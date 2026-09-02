"""Materials and Methods, Acknowledgments, References, and Figures."""

import os


def add_methods(doc, docs_dir, heading, para, title_line):
    heading(doc, "MATERIALS AND METHODS")

    para(doc, "Micro-environment wind field", italic=True)
    para(doc,
        "The central methodological choice in this work is to resolve the "
        "building-scale wind field before dispersing any pollen, because a school "
        "campus is a micro-environment in which clusters of buildings continuously "
        "divert, channel, and locally accelerate the wind that carries pollen "
        "between them. A single uniform wind vector cannot represent a plume bending "
        "around a building or pooling in a sheltered alley. We therefore modeled the "
        "horizontal near-surface wind as an incompressible, irrotational (potential) "
        "flow, so the velocity is the gradient of a scalar potential phi that "
        "satisfies Laplace's equation, del^2 phi = 0. The ambient wind was imposed "
        "on the domain boundary (phi = u_inf x + v_inf y), and a no-penetration "
        "condition (zero normal velocity, d phi/dn = 0) was applied on every "
        "detected building face, which forces the flow to go around rather than "
        "through each footprint. Laplace's equation was solved on the same 120 x 120 "
        "grid used for concentration (covering the full campus, cell size about 5 m) "
        "by red-black Gauss-Seidel successive over-relaxation; red-black ordering is "
        "required for the over-relaxation to remain numerically stable, and the "
        "relaxation factor was set to its theoretical optimum, so a full-campus solve "
        "converges in about one second. The resulting field stagnates against "
        "windward walls, accelerates around corners, and is channeled through the "
        "gaps between buildings (Figures 5 and 6). Because potential flow is "
        "inviscid, it captures this diversion and channeling but not the turbulent "
        "wake or recirculation behind a building; that lee-side pollen trapping would "
        "require a viscous (CFD) treatment and is left to future work.")

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
        "downward with distance. Rather than assuming a spatially uniform wind, each "
        "tree's plume was driven by the local wind sampled at its own grid cell from "
        "the potential-flow field described above, so plumes bend and stretch with "
        "the flow around nearby buildings. "
        "Because the governing equation is linear, the total field from all N "
        "sources was obtained by superposition, C_total = sum of C_i, evaluated with "
        "vectorized array operations over a 120 x 120 spatial grid. Concentration "
        "over detected building footprints was set to zero to represent indoor "
        "exclusion. The model uses wind speed, wind direction, and stability class "
        "as its meteorological inputs; humidity and temperature are displayed but do "
        "not currently enter the calculation (see Results and Discussion).")

    para(doc, "Phenological emission model", italic=True)
    para(doc,
        "Each species' time-varying emission was modeled as Q_i(t) = Q_base,i * W_i "
        "* Gamma_i(t), where Q_base,i is the peak base emission rate (grains/s), W_i "
        "is a dimensionless allergen potency weight (0-5), and Gamma_i(t) is a "
        "truncated Gaussian temporal gate, Gamma_i(t) = exp(-(t - t_peak)^2 / "
        "(2 sigma_t^2)) within the pollination window [t_start, t_end] and zero "
        "otherwise, with t the Julian day of year. Base emission rates, potency "
        "weights, and phenological windows for the campus genera were taken from "
        "aerobiological literature and Bay Area regional data (7) (Table 2). "
        "Trees not confidently assigned to a modeled genus were placed in a generic "
        "Other class, modeled as a prevalence-weighted blend of each campus's "
        "unmodeled tail genera so that unclassified canopies still contribute a "
        "realistic, inventory-grounded background. Relative humidity and temperature "
        "are retrieved from the weather service and displayed, but do not currently "
        "modify emission or transport; a humidity coupling (emission suppression, "
        "hygroscopic swelling, and rainfall washout) is described as future work.")

    para(doc, "Satellite-based vegetation detection", italic=True)
    para(doc,
        "Campus satellite imagery (approximately 0.5 m/pixel) was obtained from "
        "public sources per campus (Esri World Imagery for Gunn; USGS NAIP, stitched "
        "seam-free from Web-Mercator tiles, for the Stanford core). Tree-canopy "
        "pixels were classified with color thresholds calibrated on human-verified "
        "samples using green excess g_e = g - (r + b)/2 and mean brightness. "
        "Adjacent canopies were separated using marker-controlled watershed "
        "segmentation (8): the binary canopy mask was eroded to form seed markers, a "
        "Euclidean distance transform was computed, and the watershed algorithm "
        "segmented individual canopies. Each detected canopy was assigned a species; "
        "to keep labels faithful to each campus, species proportions were anchored "
        "to published tree inventories, and canopies not confidently identified were "
        "placed in the Other class. Building rooftops, which are hard to separate "
        "from pavement and dry ground by color alone, were detected with the Segment "
        "Anything Model (SAM) (9), a pretrained deep-learning segmentation network, "
        "run on overlapping image tiles so small rooftops resolve at higher "
        "effective resolution and then merged; retained masks were filtered by "
        "rooftop color, size, and compactness and reduced to oriented rectangles. "
        "On the dense Stanford core, tree candidates whose canopy disk overlapped a "
        "detected building footprint by more than 50 percent were removed as rooftop "
        "false positives. Detected footprints define the indoor exclusion mask and "
        "the obstacles for the potential-flow wind field. SAM was run once at "
        "cache-generation time; the deployed server runs no machine-learning model.")

    para(doc, "Human-in-the-loop calibration", italic=True)
    para(doc,
        "Detection was refined iteratively through an interactive map editor: "
        "automated detection proposed candidates, and a reviewer corrected them "
        "directly on the satellite basemap. For trees this included deleting false "
        "positives, relocating a canopy, resizing its radius (which rescales that "
        "tree's emission by canopy area), and reclassifying its species; for "
        "buildings it included editing each footprint's name, floor count, position, "
        "and shape, including non-rectangular (parallelogram or trapezoid) "
        "footprints. Corrections were persisted to the per-campus detection cache "
        "the server serves, so the physical model always reflects the reviewed "
        "geometry. Automated detection alone reached roughly 75 percent precision; "
        "targeted human correction raised it above 95 percent.")

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
        "Kirillov, A., Mintun, E., Ravi, N., et al. Segment Anything. In Proceedings "
        "of the IEEE/CVF International Conference on Computer Vision (ICCV) (2023).",
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
         "Figure 4. Proposed humidity coupling (future work; not part of the "
         "current model). (a) Emission suppression factor: pollen release drops "
         "sharply above 50% relative humidity. (b) Hygroscopic swelling increases "
         "grain diameter at high humidity. (c) Resulting increase in gravitational "
         "settling velocity."),
        ("fig_windflow_idealized.png",
         "Figure 5. Wind in a school micro-environment under a 4 m/s westerly "
         "ambient wind. (a) The conventional uniform-wind assumption: an identical "
         "vector everywhere. (b) The computed 2D potential-flow field (background: "
         "wind speed; black curves: streamlines). The wind stagnates against "
         "windward faces (blue), accelerates around corners (red), and is channeled "
         "through the gaps between buildings, structure that a uniform wind cannot "
         "represent. The color scale is clipped at twice the free-stream speed."),
        ("fig_windflow_campus.png",
         "Figure 6. Simulated potential-flow wind field over the real building "
         "footprints of Henry M. Gunn High School (4 m/s ambient), for a "
         "southwesterly wind (left) and a westerly wind (right). Streamlines divert "
         "around building clusters while the flow accelerates in the narrow passages "
         "between them and slows in sheltered zones; the local wind at each tree "
         "drives that tree's pollen plume."),
    ]
    from docx.shared import Inches
    for fname, caption in figs:
        path = os.path.join(docs_dir, fname)
        if os.path.exists(path):
            doc.add_picture(path, width=Inches(6.0))
        para(doc, caption)
        para(doc, "")
