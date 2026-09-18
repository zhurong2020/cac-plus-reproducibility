# Changelog

All notable changes to this reproducibility package.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).
Versions track the CAC Plus engine release they reproduce, suffixed `-repro`.

## [Unreleased] — audit before going public (2026-09-18)

The package had drifted about ten weeks behind the manuscript, through two revisions and two
changes of target journal. None of the drift was catchable by a test, which is why
`CONTRIBUTING.md` now carries a manuscript-sync checklist.

### Fixed

- **Internal hospital case identifiers removed** from
  `results_expected/byte_identity_synthetic.csv` — 100 of 100 rows. The file is called
  "synthetic" because the Hounsfield values are; the segmentation masks came from real cases
  and their identifiers rode along into the results table, two sections above a README
  sentence promising "no images, no PHI". Replaced with `case_001..case_100`; nothing reads
  the column.
- **A retracted number removed from the README.** It advertised a real-CT median speedup of
  **5.87×** for about ten weeks after that figure was withdrawn. The benchmark behind it had
  passed the two implementations a transposed, F-contiguous volume where production receives
  a C-contiguous one, and the vendor per-region loop is strongly layout-sensitive, inflating
  the measurement roughly threefold. The correct value, **1.97×**, was in the shipped data
  file the whole time — `speedup_nlst_b3_50case.csv` — so only the prose was wrong.
- **Stale journal name** in `README.md` and `CITATION.cff`, both of which cited a journal
  that had already declined the paper.
- **Section numbers** throughout, after §3.6 was cut from the manuscript and the claims
  renumbered C1–C5.

### Added

- **`analysis/agreement_panel.py`** — §3.7, the manuscript's headline result, which this
  package previously had no script for at all: the vendor arm was run after the package was
  last touched. Reports association and agreement side by side, because correlation is not
  agreement and the gap on this cohort is large (Pearson r 0.957 against Lin's CCC 0.856 and
  a mean difference of −106 Agatston). Verified to reproduce every published §3.7 value for
  both arms.
- **`analysis/spacing_audit.py`** — §3.6 (C5), the `ImagePositionPatient` overlap-
  reconstruction audit. **This script found an inaccuracy in the manuscript**: it counted 280
  acquisitions at a ratio near 2.0 where the paper said 274. The paper's 274 was right (it
  counts ratio *exactly* 2.0, 266 Siemens + 8 GE, and the GE count matches to the case), but
  the sentence after it — that every remaining acquisition was a no-op — was wrong for six
  Siemens acquisitions measuring 0.9967–1.0031 mm. The manuscript was corrected.
- **Pre-commit hook** (`.githooks/pre-commit`), from `cardiac-shared`, plus the COCA
  expert-score column names that the Stanford Research Use Agreement forbids redistributing.
  Per-clone: `git config core.hooksPath .githooks`.
- **CI** — the two checks needing no cohort access (C1 byte-identity, C5 spacing audit) plus
  the manifest denominators, on Python 3.10/3.12/3.13, with guards against a COCA-derived
  file or an internal identifier becoming tracked.
- **`SECURITY.md`**, **`CONTRIBUTING.md`**, this file.

### Removed

- `analysis/paired_thin_thick.py`, `figures/generate_figures.py` and Figures 4–5 — the thin-
  versus-thick RESCUE analysis of the former §3.6, cut from the manuscript in the CMPB
  restructure. That work continues in a companion paper; reproducing an analysis this paper
  does not contain only invites the question of why it was removed.
- Tracked `__pycache__` bytecode (5 files).

## [v2.5.2-repro] — 2026-09-05

Three corrections so that running the package reproduces the paper: the aggregate thick-to-
thin ratio computed over all pairs rather than both-non-zero pairs; every printed quantity
asserted against its published value rather than merely documented in a docstring; and the
manifest's `risk_category` derived from `src/risk_categories.py` instead of copied from an
upstream five-category scheme this paper never defines.

## [Earlier] — 2026-08-31

Per-acquisition cohort manifests added, carrying the `selected_series_uid` that makes the
NLST subset re-downloadable. COCA expert annotations withdrawn from the package after the
Stanford Research Use Agreement was read in full: it permits "personal, non-commercial
research purposes only" and forbids publishing "any portion" of the Dataset, with no
research exception, and Stanford describes the expert scores as part of the Dataset.
