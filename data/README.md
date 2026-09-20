# Data — pointers only (no patient data in this repository)

This repository contains **no images and no protected health information**. The analyses in
`../analysis/` and `../benchmarks/speedup_realct.py` run entirely on the de-identified,
patient-level result tables in `../results_expected/`.

You only need raw CT if you want to re-run scoring from images (not required to reproduce the
reported numbers).

## Cohorts

| Cohort | Access | Used for |
|---|---|---|
| **NLST** | ClinicalTrials.gov **NCT00047385**; obtain via the NCI data-use agreement (Cancer Data Access System). | paired thin/thick (§3.6), speedup (§3.3) |
| **COCA** | **Stanford AIMI** public release accompanying Eng et al. 2021; register and download from the AIMI shared datasets portal. | non-gated validation (§3.1) |

## Vendor weights

The VA AI-CAC segmentation weights are **not** redistributed here. Fetch them from
`Raffi-Hagopian/AI-CAC` **release v1.0.0** (MIT licence):

- file: `va_non_gated_ai_cac_model.pth`
- MD5: `2c73044dc3017b585826db9704536c79`

Place them under `../weights/` if re-running inference from raw CT.

## Expected layout (only if re-scoring from images)

```
data/
├── nlst/            # NLST DICOM or NIfTI per patient (from the NCI DUA)
└── coca/            # COCA non-gated chest CT (from Stanford AIMI)
weights/
└── va_non_gated_ai_cac_model.pth
```

## Checked-in result tables (`../results_expected/`)

| File | Rows | Contents |
|---|---|---|
| `nlst_cohort_manifest.csv` | 4,455 | **cohort manifest** — one row per scored acquisition (2,231 thin + 2,224 thick) with `selected_series_uid`, study date, manufacturer, kernel, thickness, slice count, and our Agatston score |
| `speedup_nlst_b3_50case.csv` | 50 | per-case vendor-naive vs CAC-Plus timings + byte-identity flag |
| `byte_identity_synthetic.csv` | 100 | synthetic-CT byte-identity benchmark (vendor vs optimised score) |

All rows are de-identified: dataset-native case identifiers (numeric for NLST, e.g. `100029`;
alphanumeric for COCA, e.g. `1A`), acquisition parameters, and derived scores. No images, no PHI,
and no local filesystem paths — the manifest builder fails if one appears.

### Why a manifest as well as a results table

The manifest says *what we measured on*: NLST is a
three-round annual screening trial, so a participant id alone does not identify which screening round
or which reconstruction produced a number. `selected_series_uid` does, which is what makes this exact
subset re-downloadable from TCIA / NCI Imaging Data Commons. Regenerate both with
`python scripts/build_cohort_manifests.py`; it asserts the 2,231 / 2,224 / 206 denominators against
the manuscript and refuses to write a manifest that disagrees with the paper.

### The NLST full-cohort identity table ships with this package

`results_expected/identity_nlst_full_n2231.csv` holds one row per NLST thin-slice acquisition,
2,231 of them, with both implementations' Agatston scores, the published v2.5.2 score, the
per-case alignment check and provenance columns. `analysis/full_cohort_identity.py` checks every
number section 3.2 and Online Methods M3a state against it, and runs with no download.

**What that check establishes, and what it does not.** It confirms the manuscript's arithmetic
over our measurement -- the denominator, the agreement count, the exact binomial interval, the
strata, the alignment minimum. It does not re-measure. Re-measuring needs the NLST images under
the NCI data-use agreement and the segmentation masks; with both, the scoring core in `src/`
regenerates the table and it can be compared row by row, which is why the table ships at all.

The identifiers are NLST's own numeric case identifiers, as elsewhere in this package.

### Which COCA file is the reference standard

Use the release's own score table, `nongated_chest_ct/scores.xlsx`: 213 non-gated acquisitions
with per-vessel LCA / LAD / LCX / RCA values and a total. Build your `--reference` CSV from its
`filename` and `total` columns (the identifier is a number followed by `A`). On a handful of rows the four vessel
values do not sum to the released total by a few Agatston; that is rounding in the release, and
`total` is the column to use.

**Do not build it from a derived comparison table.** Working through external review of this
package we used two intermediate tables as the reference; one was missing two acquisitions and
the other carried five extra. Both agreed with the release on every acquisition they held, so
nothing looked wrong — the disagreement was entirely about which rows a file happens to contain.
Reading one absent row as "this acquisition has no expert reference" moved the accuracy
denominator from 206 to 205 and produced four wrong numbers in a manuscript revision. The release
table is identifiable at a glance because it carries the per-vessel breakdown.

The manuscript reports 207 of those 213: the other six were not in the scoring manifest assembled
for that work (Online Methods M12b names them and shows the omission cannot move a stratum-level
result). If you score all 213 your denominators will differ from the paper's, legitimately.

### What is deliberately not here: anything COCA-derived

This repository publishes **no COCA data of any kind** — no case list, no reference values, and none of
our own scores for those cases. The Stanford University School of Medicine COCA Research Use Agreement
grants "personal, non-commercial research" use only and states:

> YOU MAY NOT DISTRIBUTE, PUBLISH, OR REPRODUCE A COPY of any portion or all of the COCA- Coronary
> Calcium and chest CT's Dataset to others without specific prior written permission from the School
> of Medicine.

It carries no research or reproducibility exception. The dataset page describes the non-gated release
as "chest CT DICOM images *with coronary artery calcium scores*", so the expert scores are the Dataset
rather than a derivative of it; case identifiers and per-case header values are arguably "a portion"
as well. Earlier revisions of this repository shipped the expert reference (until 2026-08-31) and then
a COCA case manifest (briefly, the same day); both were withdrawn.

**Reproducing §3.1 costs nothing extra**, because this repository ships the scoring engine itself:
register for COCA, download the non-gated release, score it with CAC Plus v2.5.2, build the expert
reference from the annotations in your own download, and run
`analysis/agreement_panel.py --scores <yours> --reference <yours>`. The script prints the
manuscript's expected values alongside yours.

If Stanford grants written permission, restoring the case manifest is a one-commit change.
