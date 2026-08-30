# JEI Submission Package — Campus AeroAllergen Mapping (CAM)

This folder contains everything prepared for submission to the **Journal of Emerging Investigators (JEI)**.

## Files

| File | Purpose |
|------|---------|
| `CAM_JEI_manuscript.docx` | The manuscript, formatted to JEI specs (Arial 11, 1.5 spacing, line numbers, figures at end). Upload this as the main manuscript. |
| `Figure1.tif` | Plume fields vs. wind speed and stability (upload separately) |
| `Figure2.tif` | Species-dependent plume shapes (upload separately) |
| `Figure3.tif` | Phenological emission model (upload separately) |
| `Figure4.tif` | Humidity effects on pollen (upload separately) |
| `build_jei_docx.py`, `content*.py` | Scripts that generated the manuscript (for regeneration/edits) |

## Before you submit — required actions

1. **ADD A SENIOR (ADULT) AUTHOR.** JEI *requires* an adult senior author who supervised the research (usually a teacher or mentor). The manuscript has a placeholder `[Senior Author Name]` on the title page and in the affiliations — replace it with a real person, or the submission will be returned. This is the single biggest blocker.

2. **Confirm the author list and order.** Largest contributor is listed first. Update names/affiliations as needed. Do not list degrees.

3. **Review the Acknowledgments and disclose assistance.** Add mentors/teachers who helped but are not authors. If AI tools were used in producing the code or manuscript, disclose that here per JEI's honesty expectations.

4. **Read it end-to-end in your own understanding.** Make sure you can explain every method and result. Reviewers (and JEI) expect the work to be substantially the student's own.

## JEI formatting compliance (already done)

- [x] JEI section order: Summary → Introduction → Results → Discussion → Materials and Methods → Acknowledgments → References
- [x] Summary is one paragraph, ≤250 words (currently ~221)
- [x] Hypothesis-driven framing (states the question and hypothesis explicitly)
- [x] Arial 11 pt, 1.5 line spacing, 1-inch margins
- [x] Continuous line numbers left on
- [x] Results written in past tense, referencing figures in context
- [x] Figures placed at the end of the Word file, each above its caption
- [x] Figures also exported as separate image files (`.tif`) for separate upload
- [x] References in numbered, citation-order format (modified MLA-8 style)
- [x] Code availability provided via GitHub link (JEI accepts a repo link for self-generated code)

## Still to verify / likely reviewer requests

- [ ] **Human/animal subjects:** This is a modeling/software study with **no human or animal subjects**, so IRB/SRC approval likely does not apply. Confirm with your reviewing adult; if a science-fair SRC form exists, upload it under "other."
- [ ] **Page limit:** JEI counts Introduction → end of Methods toward the 10-page limit (1–1.5 pages over is tolerated at initial submission). Trim the Methods if needed.
- [ ] **8 figure/table maximum:** Currently 4 figures, 0 tables in the .docx (the original LaTeX tables were folded into the text/Methods to save space). You may re-add up to 4 tables if you want (e.g., Pasquill-Gifford coefficients, species phenology) — keep total ≤8.
- [ ] **Quantitative validation:** The Discussion is explicit that the model is not yet validated against measured pollen counts. Reviewers may ask about this; be ready to frame it as future work.

## How to submit (JEI Editorial Manager)

1. An **adult** (senior author or parent/guardian) creates the Editorial Manager account and submits — the student may **not** submit from their own account.
2. Upload `CAM_JEI_manuscript.docx` as the manuscript.
3. Upload `Figure1.tif`–`Figure4.tif` as separate figure files.
4. Enter the title (the manuscript title is already within JEI's 110-character limit) and paste the Summary into the abstract box.
5. Submit; JEI reviews on a rolling basis.

## To regenerate the manuscript after edits

From this folder, with the project's Python venv active:

```bash
source /Users/hgao/project/backend/venv/bin/activate
python build_jei_docx.py
```

Edit the text in `content.py`, `content_results.py`, and `content_methods.py`, then re-run.
