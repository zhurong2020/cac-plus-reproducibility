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
| `nlst_v252_paired.csv` | 2,224 | per-patient thin & thick Agatston, risk, RESCUE flag |
| `coca_nongated_vs_reference.csv` | 206 | per-patient AI Agatston (v2.5.2) + expert reference `gt_total` |
| `speedup_nlst_b3_50case.csv` | 50 | per-case vendor-naive vs CAC-Plus timings + byte-identity flag |
| `byte_identity_synthetic.csv` | 100 | synthetic-CT byte-identity benchmark (vendor vs optimised score) |

All rows are de-identified (numeric patient identifiers only; no dates, no PHI).
