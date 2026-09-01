"""Results and Discussion sections for the JEI manuscript."""


def add_results(doc, heading, para, title_line):
    # ---------------- Results ----------------
    heading(doc, "RESULTS")

    para(doc,
        "To test whether campus pollen exposure could be predicted from physical "
        "modeling, we first needed the locations of the pollen sources. We detected "
        "tree canopies from high-resolution satellite imagery using color-based "
        "segmentation with watershed splitting, and building rooftops using the "
        "Segment Anything Model (SAM), a pretrained deep-learning segmentation "
        "network, followed by human verification through an interactive map editor "
        "(see Materials and Methods). To keep the labeling faithful to each real "
        "campus, we anchored the species mix to published tree inventories. For "
        "Gunn, the 2009 Palo Alto Unified School District arborist survey of 455 "
        "numbered trees is dominated by Valley Oak (25.5%), Coast Redwood (20.2%), "
        "and Coast Live Oak (15.4%), with Cedar, Western Sycamore, and Chinese Elm "
        "following; all oaks together make up about 42%. We labeled the roughly 900 "
        "mapped Gunn canopies against these seven allergenic genera and assigned the "
        "long tail of unmodeled ornamental genera to a generic 'Other' class. For "
        "the much larger Stanford core, tiled SAM detection identified on the order "
        "of 3,000 building rooftops and about 9,900 raw tree canopies; after "
        "geometrically removing canopies that fell mostly on rooftops (about 43% of "
        "the raw detections, likely false positives), about 5,650 trees remained, "
        "which we labeled against Stanford's six most abundant genera reported in "
        "its campus inventory (Coast Live Oak, the single most numerous species at "
        "about 40%, plus Canary Island Palm, Eucalyptus, Coast Redwood, Valley Oak, "
        "and Olive).")

    para(doc,
        "We then computed the pollen concentration field by first solving a "
        "two-dimensional potential-flow wind field that deflects and channels the "
        "ambient wind around the detected building footprints, and then modeling "
        "each detected tree as a Gaussian plume driven by the local wind at its "
        "location, summing the contributions at a student breathing height of 1.5 m. "
        "The resulting fields displayed the spatial structure predicted by "
        "advection-diffusion physics (Figure 1). Concentration was highest "
        "immediately downwind of dense tree clusters and fell off as a bell-shaped "
        "curve to either side of the plume centerline; stronger modeled winds "
        "elongated and diluted the plumes, while more stable atmospheric conditions "
        "confined them into narrow, concentrated bands. These patterns match the "
        "behavior the Gaussian plume solution predicts.")

    para(doc,
        "Because pollen grains differ in size and density, we compared modeled "
        "plumes across species (Figure 2). Small, light Oak grains (settling "
        "velocity approximately 0.5 cm/s) produced wide, far-reaching plumes that "
        "kept concentrations elevated hundreds of meters downwind, whereas large, "
        "heavy Pine grains (approximately 3.1 cm/s) produced intense but localized "
        "concentrations that decayed sharply within 20-50 m of the source. This "
        "species dependence means the model predicts distinct exposure hot spots "
        "near pines but broad background exposure from oaks.")

    para(doc,
        "Pollen emission is strongly seasonal, so we modulated each source by a "
        "species-specific temporal gate function (Figure 3). Most campus genera "
        "bloom in late winter through spring, but cedar pollinates in the fall, so "
        "the model produces a dominant spring peak driven by oaks and a distinct "
        "secondary autumn peak on the Gunn campus. Using a fixed annual "
        "concentration scale (500 grains/m^3 defined as the spring peak) to enable "
        "seasonal comparison, the modeled spring maximum reached several hundred "
        "grains/m^3 with multiple species actively emitting, fell to a low "
        "background in early summer once the oaks finished, and dropped to "
        "effectively zero in mid-winter when all species were dormant. This "
        "quantifies how strongly exposure depends on the time of year.")

    para(doc,
        "The current model is driven by wind speed, wind direction, and atmospheric "
        "stability class. We retrieve relative humidity and temperature from the "
        "weather service and display them, but they do not yet enter the dispersion "
        "calculation (temperature only informs the stability-class estimate). "
        "Because humidity is known to strongly modulate real pollen loads, we "
        "designed, but have not yet implemented, a humidity coupling in which "
        "emission is suppressed at high relative humidity (anthers require drying to "
        "release grains), hygroscopic swelling increases grain settling, and "
        "rainfall scavenges airborne pollen (Figure 4); the qualitative form of "
        "these responses is shown for reference. Implementing and validating this "
        "coupling against measured pollen and weather data is planned future work.")

    para(doc,
        "Finally, the complete concentration field over each campus showed "
        "consistent features: plumes bending along the potential-flow streamlines as "
        "the wind was diverted around buildings, near-zero concentration over "
        "building footprints (where outdoor air is excluded), locally elevated "
        "concentration where the flow was channeled between closely spaced "
        "buildings, and elevated concentrations in oak-dense corridors. Each "
        "full-campus field was computed in a few seconds on a standard server (well "
        "under one second for Gunn), fast enough for interactive, real-time use even "
        "with the thousands of sources on the Stanford campus.")
    para(doc, "")

    # ---------------- Discussion ----------------
    heading(doc, "DISCUSSION")

    para(doc,
        "Our results support the hypothesis that the pollen exposure experienced "
        "while walking across a campus can be predicted at meter scale from the "
        "physics of atmospheric transport, rather than requiring a dense network of "
        "physical sensors. By modeling each detected tree as a Gaussian plume source "
        "driven by a potential-flow wind field around the buildings, the system "
        "reproduced the concentration gradients that regional, city-scale monitoring "
        "inherently averages away: plumes bending along the flow diverted around "
        "buildings, species-dependent hot spots, building exclusion zones, and "
        "channeling between closely spaced structures. The few-second computation "
        "time makes the approach practical as an interactive tool that a student "
        "could consult before choosing a route to class.")

    para(doc,
        "Several limitations should temper interpretation of these results. First, "
        "and most importantly, the model has not yet been validated against "
        "ground-truth pollen measurements; our results demonstrate that the system "
        "reproduces the qualitative spatial structure predicted by dispersion theory, "
        "but they do not establish quantitative accuracy of the predicted "
        "concentrations. Direct comparison against co-located pollen samplers is the "
        "essential next step. Second, our two-dimensional potential-flow wind field "
        "is inviscid: it captures how wind is diverted and channeled around "
        "buildings but produces no turbulent wake or recirculation zone behind them, "
        "so pollen trapping in lee zones is not represented; a viscous "
        "computational-fluid-dynamics treatment would be required to capture that. "
        "Third, species were classified from RGB satellite imagery and a size-based "
        "heuristic, which is imperfect; hyperspectral imagery or ground surveys would "
        "improve species assignment, which in turn affects emission timing and "
        "potency. Fourth, several physical parameters (base emission rates, potency "
        "weights, phenological windows) are drawn from the literature rather than "
        "measured on site, so absolute concentrations should be treated as modeled "
        "estimates rather than measurements.")

    para(doc,
        "The human-in-the-loop calibration workflow proved important: fully "
        "automated detection reached only about 75% precision, but three rounds of "
        "targeted human correction raised it above 95%. This suggests that for "
        "campus-scale problems, semi-automated pipelines that combine algorithmic "
        "detection with focused human verification are more practical than fully "
        "autonomous detection. It also highlights that the quality of the physical "
        "prediction depends directly on the quality of the source map that feeds it.")

    para(doc,
        "A practical implication concerns risk communication. Because absolute counts "
        "are hard to interpret without context, the fixed annual scale is useful: a "
        "June reading of 30 grains/m^3 could alarm a student if shown in isolation, "
        "but is clearly low when displayed against the 500 grains/m^3 spring peak "
        "that represents the true high-risk period. Future work should focus on "
        "quantitative validation against physical pollen samplers, incorporation of "
        "building-resolved airflow, and prospective testing of whether "
        "model-recommended routes actually reduce measured symptoms. In summary, we "
        "built and deployed a physics-based system that predicts hyperlocal campus "
        "pollen exposure at meter scale in real time, and our findings support its "
        "central hypothesis while clearly defining the validation work still needed.")
    para(doc, "")
