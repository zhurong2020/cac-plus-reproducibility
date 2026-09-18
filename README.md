# CAC Plus — reproducibility package

Reproduces the quantitative results of **"CAC Plus: An open-source calcium-scoring engine
for opportunistic coronary artery calcium quantification on non-gated multi-format chest
CT"**, submitted to *Computer Methods and Programs in Biomedicine*.

This is the **scoring engine and its validation analyses**. The wider CAC Plus deployment
toolkit — adaptive-router internals, PACS/worklist integration, licensing — is maintained
separately and is **not** part of this release, which is what the manuscript's title means
by scoping "open-source" to the scoring engine.

## Install

```bash
pip install -r requirements.txt
git config core.hooksPath .githooks      # PHI/PII pre-commit hook; per-clone, not pushed
```

## Reproduce the paper

Every script asserts its published values and **exits non-zero if a number disagrees with
the manuscript**. An expected value written only in a comment is not a check.

```bash
# Self-contained — no data, no weights, no network. Start here.
python benchmarks/byte_identity_synthetic.py     # C1  -> 100/100 byte-identical Agatston

# From the shipped result tables — no images needed.
python analysis/spacing_audit.py                 # C5  -> 274 at ratio exactly 2.0 (266 SIEMENS + 8 GE)
python scripts/build_cohort_manifests.py         # Table 1 -> asserts n = 2,231

# Needs the NLST images (see data/README.md).
python benchmarks/speedup_realct.py              # C2  -> median 1.97x real-CT, 50/50 identical

# Needs your own COCA download, both files (see data/README.md).
python analysis/agreement_panel.py --scores yours.csv --reference your_coca_gt.csv
                                                 # 3.1 -> zero-CAC 52.4% scored vs 42.7% reference
                                                 # 3.7 -> CCC 0.856, ICC 0.857, kappa 0.734,
                                                 #        CAC>0 sensitivity 72.0%
```

## What reproduces what

| Script | Manuscript | Reproduces |
|---|---|---|
| `benchmarks/byte_identity_synthetic.py` | §3.2 (C1), Fig 3a | vectorised == vendor-reference Agatston, byte for byte |
| `benchmarks/speedup_realct.py` | §3.3 (C2), Fig 3b/c | real-CT speedup distribution + per-stratum medians |
| `analysis/spacing_audit.py` | §3.6 (C5) | the `ImagePositionPatient` overlap-reconstruction audit |
| `analysis/agreement_panel.py` | §3.1, **§3.7** | zero-CAC rates; agreement against the COCA expert reference, either arm |
| `scripts/build_cohort_manifests.py` | §2.3 / Table 1 | the NLST manifest; asserts the published denominator |
| `src/agatston_vectorised.py`, `src/agatston_vendor_ref.py` | Table 2 | the two Agatston implementations proven identical |
| `src/risk_categories.py` | §2.4 | the SCCT four strata — the single definition used everywhere |

`results_expected/_INVALID_transposed_ct_*.csv` is kept on purpose. It is the superseded C2
measurement that produced the withdrawn 5.87× median, retained so a reader can see the
difference the correction made rather than take it on trust; `benchmarks/speedup_realct.py`
documents both defects behind it.

**Not reproducible from this repository, and stated as such in the paper**: §3.4 (C3,
multi-format identity) needs the three-format input pipeline from the deployment toolkit;
§3.5 (C4) is a retrospective audit of our own deployment incident records, which the
manuscript labels non-independent for that reason.

## Why the COCA analysis needs two files from you

Nothing COCA-derived ships here. Stanford's Research Use Agreement for the AIMI datasets
grants use "for personal, non-commercial research purposes only" and states that **"YOU MAY
NOT DISTRIBUTE, PUBLISH, OR REPRODUCE A COPY of any portion"** of the Dataset without
written permission, with no research or reproducibility exception. The dataset page
describes the non-gated release as *"chest CT DICOM images with coronary artery calcium
scores"* — so the expert scores are the Dataset, not a derivative of it. That rules out
publishing COCA case identifiers, the expert reference, and our own per-case scores keyed
to those identifiers.

Reproducibility is unaffected, because the scoring engine is here: anyone registered for
COCA scores their own copy and passes both files to `agreement_panel.py`. You would have had
to download the images yourself in any case.

NLST is under different terms — participant identifiers and SeriesInstanceUIDs may be
published — which is why `results_expected/nlst_cohort_manifest.csv` ships in full, with the
series UIDs that make the exact subset re-downloadable from TCIA/IDC.

## Data

Patient CT data are **not** included, and `results_expected/` contains no patient
identifier of any kind.

- **NLST** — ClinicalTrials.gov NCT00047385, via the National Cancer Institute's data-use
  agreement. The 2,231-acquisition subset is specified by `selected_series_uid` in the
  manifest.
- **COCA** — Stanford AIMI public release accompanying Eng et al. 2021, under its Research
  Use Agreement.
- **Vendor weights** — `Raffi-Hagopian/AI-CAC` release `v1.0.0` (MIT). Not redistributed
  here; fetch into `weights/` if re-scoring from images.

See [`data/README.md`](data/README.md) for the expected layout.

## License

Apache-2.0 (`LICENSE`). CAC Plus wraps the VA AI-CAC algorithm of Hagopian et al. (MIT)
**unchanged**; no invention is claimed over that algorithm, the Agatston formula, or nnU-Net.

## Change log

See [`CHANGELOG.md`](CHANGELOG.md). Most recently (2026-09-18), the package was audited
against the current manuscript before being made public, which found a stale journal name,
a retracted speedup figure in this README, analyses belonging to a section the manuscript no
longer contains, and internal case identifiers in a shipped result table. The same audit
found and corrected an inaccuracy in the manuscript — see `analysis/spacing_audit.py`.
