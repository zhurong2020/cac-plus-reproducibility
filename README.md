# CAC Plus — reproducibility package

Reproduces the quantitative results of **"CAC Plus: Open-source engineering toolkit for
opportunistic AI coronary calcium screening across multi-format chest CT pipelines"**
(*Radiology: Artificial Intelligence*, 2026).

This is the **reproducibility subset** — the scoring-engine equivalence, the validation
analyses, and the figure scripts. The full CAC Plus deployment toolkit (adaptive-router
internals, PACS/worklist integration, product/licensing features) is maintained separately
and is **not** part of this release.

> **Status:** private during peer review; provided to the editor on request; made public at
> acceptance. Tag `v2.5.2-repro` is the exact revision cited in the manuscript.

## Install

```bash
pip install -r requirements.txt
# vendor weights (MIT, not redistributed here): fetch Raffi-Hagopian/AI-CAC release
# v1.0.0 into weights/ if you want to re-run inference from raw CT (not required for the
# analyses below, which run on the checked-in patient-level result tables).
```

## Reproduce the paper numbers

Every script prints its result to stdout; the expected values (from the manuscript) are in
the comment header of each file.

```bash
python analysis/paired_thin_thick.py      # §3.6  -> n=2224, r=0.974, ratio=0.934, kappa=0.639, RESCUE 327/2224 (14.70%)
python analysis/coca_vs_reference.py --scores <yours> --reference <yours>
                                           # §3.1  -> n=206, r=0.957, zero-CAC 52.4% vs 42.7%
                                           # (nothing COCA-derived is redistributed here; you supply
                                           #  both files from your own COCA download -- data/README.md)
python benchmarks/speedup_realct.py        # §3.3  -> median 5.87x, 50/50 identical, per-stratum 2.00..16.57x
python benchmarks/byte_identity_synthetic.py  # §3.2 -> 100/100 byte-identical (self-contained, no patient data)
python figures/generate_figures.py         # Figures 4 & 5 from the paired table
```

## What reproduces what

| Script | Manuscript | Reproduces |
|---|---|---|
| `analysis/paired_thin_thick.py` | §3.6, Fig 4/5 | Pearson r, thick/thin ratio, Bland-Altman, Cohen κ, RESCUE rate |
| `analysis/coca_vs_reference.py` | §3.1 | COCA non-gated AI-vs-expert correlation + zero-CAC rates (needs `--scores` and `--reference`, both yours — see `data/README.md`) |
| `scripts/build_cohort_manifests.py` | §2.3 / Table 1 | Rebuilds the NLST and COCA cohort manifests; asserts the published denominators |
| `benchmarks/speedup_realct.py` | §3.3, Fig 3b/c | real-CT speedup distribution + per-stratum medians |
| `benchmarks/byte_identity_synthetic.py` | §3.2, Fig 3a | vectorised == naive Agatston (byte-identity) |
| `figures/generate_figures.py` | Fig 4, Fig 5 | scatter + Bland-Altman; RESCUE heatmap + rate bars |
| `src/agatston_vectorised.py` / `agatston_vendor_ref.py` | Table 2 row 2 | the two Agatston implementations proven identical |
| `src/risk_categories.py` | Methods / legends | None / Mild / Moderate / Severe thresholds — the single definition; `build_cohort_manifests.py` now derives the manifest's `risk_category` column from it rather than copying an upstream label |

### 2026-09-05 — three corrections, so that running this package reproduces the paper

1. `analysis/paired_thin_thick.py` computed the aggregate thick-to-thin ratio over patients
   non-zero on **both** reconstructions and printed **0.934**, while the manuscript reports
   **0.929** over *all* 2,224 paired patients. 0.934 is a value an upstream audit identified as an
   inadvertent denominator switch and retired on 2026-07-12; this script had kept it, and its
   docstring listed it as the expected result. Restricting to both-non-zero also drops the
   thick-slice zeros that are the RESCUE phenomenon the paper is about. Fixed to all-pairs.
2. Every printed quantity in that script — n, r, ratio, Bland-Altman mean and limits, agreement,
   κ, RESCUE count, **and the full 4×4 reclassification matrix** — is now asserted against the
   published value, so the script fails instead of reporting a number that disagrees with the
   paper. An expected value written only in a docstring is not a check.
3. `results_expected/nlst_cohort_manifest.csv` carried a **five**-category `risk_category`
   column (`None / Minimal ≤10 / Mild ≤100 / Moderate ≤400 / Severe`) copied verbatim from the
   upstream scoring CSV — a scheme this paper never defines, on boundaries it does not use, and
   one that `src/risk_categories.py` was never asked to produce. The column is now derived with
   `classify_cac_risk()`, and the builder fails if a category outside `RISK_ORDER` ever appears.

## Data

Patient CT data are **not** included. The two validation cohorts are public and obtained by
qualified researchers from their respective processes:

- **NLST** — ClinicalTrials.gov NCT00047385 (National Cancer Institute data-use agreement).
- **COCA** — Stanford AIMI public release accompanying Eng et al. 2021.

`results_expected/` ships the **de-identified, patient-level result tables** (Agatston scores,
risk categories, timings) that the analyses above operate on — no images, no PHI. See
[`data/README.md`](data/README.md) for how to obtain the raw CT and the expected layout if you
want to re-run scoring from images.

## License

Apache-2.0 (`LICENSE`). CAC Plus wraps the VA AI-CAC algorithm of Hagopian et al. (MIT licence)
**unchanged**; no invention is claimed over that algorithm, the Agatston formula, or nnU-Net.
