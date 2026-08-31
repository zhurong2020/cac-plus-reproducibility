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
| `coca_cohort_manifest.csv` | 206 | **cohort manifest** — one row per scored COCA case with acquisition parameters and our Agatston score |
| `nlst_v252_paired.csv` | 2,224 | per-patient thin & thick Agatston, risk, RESCUE flag |
| `speedup_nlst_b3_50case.csv` | 50 | per-case vendor-naive vs CAC-Plus timings + byte-identity flag |
| `byte_identity_synthetic.csv` | 100 | synthetic-CT byte-identity benchmark (vendor vs optimised score) |

All rows are de-identified: dataset-native case identifiers (numeric for NLST, e.g. `100029`;
alphanumeric for COCA, e.g. `1A`), acquisition parameters, and derived scores. No images, no PHI,
and no local filesystem paths — the manifest builder fails if one appears.

### Why a manifest as well as a results table

`nlst_v252_paired.csv` says *what we measured*; the manifest says *what we measured it on*. NLST is a
three-round annual screening trial, so a participant id alone does not identify which screening round
or which reconstruction produced a number. `selected_series_uid` does, which is what makes this exact
subset re-downloadable from TCIA / NCI Imaging Data Commons. Regenerate both with
`python scripts/build_cohort_manifests.py`; it asserts the 2,231 / 2,224 / 206 denominators against
the manuscript and refuses to write a manifest that disagrees with the paper.

### What is deliberately not here: the COCA expert reference

The COCA per-vessel and total expert Agatston annotations (`gt_total`) are **part of the Stanford AIMI
release, not our output**. Stanford's Research Use Agreement governs redistribution of the dataset and
we have not established that it permits republishing those annotations, so they are not shipped here —
an earlier revision of this repository did include them, and that was corrected on 2026-08-31.

`analysis/coca_vs_reference.py` therefore takes `--reference <csv>`: build it from your own COCA
download (a CSV with `patient_id` and `gt_total`, i.e. the per-case sum of the expert per-vessel
scores) and the script joins it to our scores in `coca_cohort_manifest.csv` to reproduce r = 0.957.
