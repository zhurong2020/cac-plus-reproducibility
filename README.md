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
python analysis/coca_vs_reference.py --reference <your_coca_reference.csv>
                                           # §3.1  -> n=206, r=0.957, zero-CAC 52.4% vs 42.7%
                                           # (the expert reference is Stanford's, not redistributed
                                           #  here -- see data/README.md)
python benchmarks/speedup_realct.py        # §3.3  -> median 5.87x, 50/50 identical, per-stratum 2.00..16.57x
python benchmarks/byte_identity_synthetic.py  # §3.2 -> 100/100 byte-identical (self-contained, no patient data)
python figures/generate_figures.py         # Figures 4 & 5 from the paired table
```

## What reproduces what

| Script | Manuscript | Reproduces |
|---|---|---|
| `analysis/paired_thin_thick.py` | §3.6, Fig 4/5 | Pearson r, thick/thin ratio, Bland-Altman, Cohen κ, RESCUE rate |
| `analysis/coca_vs_reference.py` | §3.1 | COCA non-gated AI-vs-expert correlation + zero-CAC rates (needs `--reference`, see `data/README.md`) |
| `scripts/build_cohort_manifests.py` | §2.3 / Table 1 | Rebuilds the NLST and COCA cohort manifests; asserts the published denominators |
| `benchmarks/speedup_realct.py` | §3.3, Fig 3b/c | real-CT speedup distribution + per-stratum medians |
| `benchmarks/byte_identity_synthetic.py` | §3.2, Fig 3a | vectorised == naive Agatston (byte-identity) |
| `figures/generate_figures.py` | Fig 4, Fig 5 | scatter + Bland-Altman; RESCUE heatmap + rate bars |
| `src/agatston_vectorised.py` / `agatston_vendor_ref.py` | Table 2 row 2 | the two Agatston implementations proven identical |
| `src/risk_categories.py` | Methods / legends | None / Mild / Moderate / Severe thresholds |

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
