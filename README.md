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

## Reproduce the paper — one command

```bash
python scripts/reproduce_all.py
```

**Eight of the nine checks need no data at all** — no images, no model weights, no
network. They run from the per-case result tables in `results_expected/`. The runner
prints a verdict per check and exits non-zero if any published value fails to reproduce.

The fifth needs two CSVs from your own COCA download (see below):

```bash
python scripts/reproduce_all.py --coca-scores yours.csv --coca-reference your_coca_gt.csv
```

### First-clone test, from scratch

```bash
git clone https://github.com/zhurong2020/cac-plus-reproducibility && cd cac-plus-reproducibility
python3 -m venv venv && . venv/bin/activate     # Windows: venv\Scripts\activate
pip install -r requirements.txt
python scripts/reproduce_all.py
```

Expected last line: `All 4 runnable checks reproduce the manuscript.`

Verified on native Windows (PowerShell, Python 3.11, numpy 2.4.6, scipy 1.17.1), on Linux,
and in CI across Python 3.10–3.13. Output is ASCII and colour is used only when the terminal
supports it, so a Windows PowerShell 5.1 or GBK console gets plain readable text rather than
escape codes or a traceback.

### Why a runner and not a list of commands

Exit code zero is not the same as reproducing a published number. A script that reads a
table and prints a median exits zero whether that median is 1.97 or 5.87 — and this README
advertised 5.87 for ten weeks after it was withdrawn. So each check carries the values the
manuscript reports and the runner fails if the output does not contain them.

Each script also still runs on its own, and prints more than the runner shows:

```bash
python benchmarks/byte_identity_synthetic.py   # C1  -> 100/100 byte-identical Agatston
python benchmarks/speedup_realct.py            # C2  -> median 1.97x, 50/50 identical
python analysis/spacing_audit.py               # C5  -> 274 at ratio exactly 2.0
python scripts/verify_cohort_manifest.py       # Table 1 -> n = 2,231
python analysis/agreement_panel.py --scores yours.csv --reference your_coca_gt.csv
                                               # 3.1 -> zero-CAC 52.4% vs 42.7%
                                               # 3.7 -> CCC 0.856, ICC 0.857, kappa 0.734
```

## What reproduces what

| Script | Manuscript | Reproduces |
|---|---|---|
| `benchmarks/byte_identity_synthetic.py` | §3.2 (C1), Fig 3a | vectorised == vendor-reference Agatston, byte for byte |
| `benchmarks/speedup_realct.py` | §3.3 (C2), Fig 3b/c | the speedup statistics, from the shipped 50-case per-case timings. Re-*measuring* the timings would need the images and a GPU; this reproduces the published summary from the measurements |
| `analysis/spacing_audit.py` | §3.6 (C5) | the `ImagePositionPatient` overlap-reconstruction audit |
| `analysis/agreement_panel.py` | §3.1, **§3.7** | zero-CAC rates; agreement against the COCA expert reference, either arm |
| `scripts/reproduce_all.py` | all of the above | runs every available check and verifies the published values |
| `scripts/verify_cohort_manifest.py` | §2.3 / Table 1 | checks the shipped manifest: denominator, one row per series UID, no leak |
| `scripts/build_cohort_manifests.py` | — | **maintainer only**; rebuilds the manifest from private source tables, so neither CI nor a reader can run it |
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

## Environments and troubleshooting

- `requirements.txt` — **the analysis stack for this package only**: numpy and scipy, with
  lower bounds rather than pins. Everything in `analysis/`, `benchmarks/` and `scripts/` runs
  on it. It is *not* the stack the reported scores were produced on, and until 2026-09-19 this
  line said it was. Scoring needs PyTorch, MONAI and the vendor weights; that environment is
  `venv_py313` (Python 3.13.11, PyTorch 2.9.1+cu128, MONAI 1.5.1), described in Online
  Methods M9, and it is part of the deployment toolkit this package does not distribute.
- `requirements-vendor-frozen-cu116.txt` — the stack used for the cross-stack identity
  check (Online Methods M9). It matches the vendor's pinned PyTorch and MONAI versions
  but not its CUDA build; the reason is in `TROUBLESHOOTING.md`.
- `patches/monai_1.5.1_compatibility.patch` — **documentation of a change made inside the
  private toolkit, not a patch you can apply here.** Its target path,
  `external/cac_plus_reference/ai_cac_inference_lib.py`, is not in this package, and applying
  it will fail. It is included because M9 refers to it: `SwinUNETR` dropped `img_size` in MONAI
  1.5, so the code branches on the installed version and **omits** the argument on 1.5+ while
  still passing it on 1.4. Earlier wording here and in M9 said it "restores" the argument,
  which is the opposite of what the diff does.
- `TROUBLESHOOTING.md` — the failures that actually occurred during this work.
