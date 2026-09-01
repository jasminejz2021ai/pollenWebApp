"""Manuscript content for the JEI submission, in JEI section order."""

import os


def build(doc, docs_dir, heading, para, title_line):
    # ---------------- Title page ----------------
    title_line(doc,
        "Physics-Based Mapping of Hyperlocal Campus Pollen Exposure Using "
        "Gaussian Plume Modeling",
        size=14, bold=True)
    para(doc, "")
    title_line(doc, "Jasmine J. Zhang^1 and [Senior Author Name]^2", size=11, bold=True)
    para(doc, "^1 Henry M. Gunn High School, Palo Alto, CA 94306, USA")
    para(doc, "^2 [Senior author affiliation - Department, Institution, City, State]")
    para(doc, "")
    para(doc, "[SENIOR AUTHOR REQUIRED: JEI requires an adult senior author who "
              "supervised the research. Replace the placeholder above with their "
              "name and affiliation before submitting.]", italic=True)
    para(doc, "")

    # ---------------- Summary ----------------
    heading(doc, "SUMMARY")
    para(doc,
        "Allergic rhinitis affects 10-30% of people, and airborne pollen is its "
        "leading environmental trigger. Regional pollen forecasts report a single "
        "value for an entire city, so they cannot explain why symptoms differ "
        "between one campus walkway and another only tens of meters away. We asked "
        "whether the pollen exposure a student experiences while walking across a "
        "school campus can be predicted at meter scale from the physics of how "
        "pollen travels through air. We hypothesized that coupling a two-dimensional "
        "potential-flow wind field, which deflects and channels the wind around "
        "buildings, with a steady-state Gaussian plume solution of the atmospheric "
        "advection-diffusion equation, driven by the measured positions of "
        "individual trees, would reproduce the sharp, building- and wind-dependent "
        "concentration gradients that regional monitors miss. To test this, we built "
        "Campus AeroAllergen Mapping (CAM), a web system that locates individual "
        "trees from satellite imagery and detects building rooftops with a "
        "deep-learning segmentation model, models each tree as a pollen source, and "
        "superposes their plumes along the local wind at a student breathing height "
        "of 1.5 m. We applied CAM to two campuses of contrasting scale: Henry M. "
        "Gunn High School (about 900 trees across seven allergenic genera) and the "
        "Stanford University core (thousands of trees and building rooftops). The "
        "model produced meter-scale concentration fields in a few seconds, showing "
        "plumes bending along the flow diverted around buildings, near-zero "
        "concentration over building footprints, and elevated pollen in tree-dense "
        "corridors. Anchoring the species mix to published campus tree inventories "
        "reproduced a spring oak peak and, on Gunn, a secondary autumn peak driven "
        "by fall-pollinating cedar. These results support the hypothesis that "
        "hyperlocal pollen exposure is predictable from physical modeling. The "
        "system reports lower-exposure walking routes, though we have not yet "
        "validated its predictions against measured pollen counts.")
    para(doc, "")

    # ---------------- Introduction ----------------
    heading(doc, "INTRODUCTION")
    para(doc,
        "Allergic rhinitis affects an estimated 10-30% of the global population, "
        "with airborne pollen constituting the dominant environmental trigger (1). "
        "For students with pollen allergies, the school day involves repeated "
        "outdoor transits between buildings, often along walkways lined with "
        "allergenic trees. Anecdotally, symptoms can change dramatically over very "
        "short distances, suggesting that pollen concentration is not uniform across "
        "a campus but varies sharply with the position of individual trees, the "
        "direction of the wind, and the layout of buildings.")
    para(doc,
        "Existing pollen monitoring relies on regional stations that report "
        "area-averaged counts at temporal resolutions of hours to days (2). A single "
        "citywide number cannot resolve the concentration gradients that determine "
        "what an individual actually breathes during a five-minute walk between "
        "classes. The physics governing how pollen moves through air, however, is "
        "well established: pollen released from a source is carried by wind "
        "(advection) and spread by turbulence (diffusion), a process described by "
        "the advection-diffusion equation whose steady-state solution is the "
        "Gaussian plume model (3, 4). This model is widely used for industrial "
        "emissions but is rarely applied at the meter scale of a single campus, and "
        "rarely with the true positions of hundreds of individual biological "
        "sources.")
    para(doc,
        "We therefore asked whether the hyperlocal pollen exposure experienced by a "
        "student walking across a campus can be predicted from first-principles "
        "atmospheric physics. We hypothesized that a steady-state Gaussian plume "
        "model, driven by the measured positions of individual trees, real-time "
        "wind, species-specific bloom timing, and a wind field that flows around "
        "campus buildings, would reproduce the sharp spatial concentration gradients "
        "that regional monitoring cannot capture, and would do so quickly enough for "
        "interactive daily use. To test this, we developed Campus AeroAllergen "
        "Mapping (CAM), a system that (i) identifies pollen sources (tree canopies) "
        "and building rooftops from satellite imagery, the latter using a pretrained "
        "deep-learning segmentation model, (ii) computes a two-dimensional "
        "potential-flow wind field that deflects and channels the wind around the "
        "buildings, (iii) solves the advection-diffusion equation analytically at "
        "each source using the local wind, (iv) modulates emission by "
        "species-specific phenology, and (v) integrates exposure along student "
        "walking paths. We deployed and evaluated the system on two campuses of "
        "contrasting scale and layout: Henry M. Gunn High School (Palo Alto, CA), a "
        "25-hectare campus with about 900 mapped trees, and the core of Stanford "
        "University, with thousands of trees and buildings.")
    para(doc, "")

    # results, discussion, methods, etc. are added by the other content modules
    from content_results import add_results
    from content_methods import add_methods
    add_results(doc, heading, para, title_line)
    add_methods(doc, docs_dir, heading, para, title_line)
