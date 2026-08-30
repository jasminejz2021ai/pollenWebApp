"""Results and Discussion sections for the JEI manuscript."""


def add_results(doc, heading, para, title_line):
    # ---------------- Results ----------------
    heading(doc, "RESULTS")

    para(doc,
        "To test whether campus pollen exposure could be predicted from physical "
        "modeling, we first needed the locations of the pollen sources. We detected "
        "trees from high-resolution satellite imagery using color-based segmentation "
        "with watershed splitting, followed by three rounds of human verification to "
        "remove false positives (see Materials and Methods). This process identified "
        "1,018 trees across six allergenic genera: 414 Coast Live Oak, 239 Coast "
        "Redwood, 159 Valley Oak, 110 Pine, 76 Western Sycamore, and 20 Chinese Elm. "
        "Automated detection alone achieved approximately 75% precision; after three "
        "interactive correction rounds, the false-positive rate fell below 5%, "
        "indicating that the source map used as input to the physical model was "
        "reliable.")

    para(doc,
        "We then computed the pollen concentration field by modeling each detected "
        "tree as a Gaussian plume source and summing the contributions at a student "
        "breathing height of 1.5 m. The resulting fields displayed the spatial "
        "structure predicted by advection-diffusion physics (Figure 1). "
        "Concentration was highest immediately downwind of dense tree clusters and "
        "fell off as a bell-shaped curve to either side of the plume centerline; "
        "stronger modeled winds elongated and diluted the plumes, while more stable "
        "atmospheric conditions confined them into narrow, concentrated bands. These "
        "patterns match the behavior the Gaussian plume solution predicts.")

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
        "species-specific temporal gate function (Figure 3). Using a fixed annual "
        "concentration scale (500 grains/m^3 defined as the spring peak) to enable "
        "seasonal comparison, the modeled maximum concentration was 273 grains/m^3 "
        "on April 1 (day 91), with eight species actively emitting; 30 grains/m^3 "
        "on June 25 (day 176), when only Pine remained weakly active; and "
        "effectively zero in mid-January, when all species were dormant. Summer "
        "concentrations were therefore approximately 6% of the spring peak, "
        "quantifying how strongly exposure depends on the time of year.")

    para(doc,
        "We also incorporated relative humidity, which suppresses pollen emission as "
        "anthers require drying to release grains and increases grain settling "
        "through hygroscopic swelling (Figure 4). Under the modeled humidity "
        "response, emission dropped to as little as 10% of its dry-air value at 90% "
        "relative humidity, consistent with the common observation that pollen loads "
        "are lowest during humid marine-layer mornings and highest on dry "
        "afternoons.")

    para(doc,
        "Finally, the complete concentration field over the campus showed four "
        "consistent features: plume elongation along the prevailing wind, near-zero "
        "concentration over building footprints (where outdoor air is excluded), "
        "enhanced accumulation in the low-wind wake zones behind buildings, and "
        "elevated concentrations in oak-dense corridors. Each full-campus field was "
        "computed in under 500 ms on a standard server, fast enough for interactive, "
        "real-time use.")
    para(doc, "")

    # ---------------- Discussion ----------------
    heading(doc, "DISCUSSION")

    para(doc,
        "Our results support the hypothesis that the pollen exposure experienced "
        "while walking across a campus can be predicted at meter scale from the "
        "physics of atmospheric transport, rather than requiring a dense network of "
        "physical sensors. By modeling each of 1,018 detected trees as a Gaussian "
        "plume source, the system reproduced the concentration gradients that "
        "regional, city-scale monitoring inherently averages away: sharp downwind "
        "plumes, species-dependent hot spots, building exclusion zones, and wake "
        "accumulation. The sub-second computation time makes the approach practical "
        "as an interactive tool that a student could consult before choosing a route "
        "to class.")

    para(doc,
        "Several limitations should temper interpretation of these results. First, "
        "and most importantly, the model has not yet been validated against "
        "ground-truth pollen measurements; our results demonstrate that the system "
        "reproduces the qualitative spatial structure predicted by dispersion theory, "
        "but they do not establish quantitative accuracy of the predicted "
        "concentrations. Direct comparison against co-located pollen samplers is the "
        "essential next step. Second, the model assumes a spatially uniform wind "
        "field; real airflow is channeled and deflected by buildings in ways that "
        "would require computational fluid dynamics to capture fully, and our "
        "Schulman-Scire wake correction is only an empirical approximation. Third, "
        "species were classified from RGB satellite imagery and a size-based "
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
