# Changelog

All notable changes to this reproducibility package.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).
Versions track the CAC Plus engine release they reproduce, suffixed `-repro`.

## [v2.5.2-repro] — public, and corrected by three rounds of external review (2026-09-19)

The repository went public on 2026-09-19. Four external reviewers then read the manuscript with
this package in hand and recomputed from it, which found more here than the pre-publication
audit had.

### Fixed

- **The benchmark stratified on a superseded release.** `speedup_realct.py` binned cases by the
  CSV's `stratum` column, which derives from `ref_agatston` — the December 2025 release's score
  for the same case, i.e. a previous version of the engine being benchmarked. It moves nine
  cases: 30/20 zero/positive under that column, 21/29 under the scores the paper reports, and a
  calcium-positive median of 4.80x against 3.30x. Both the benchmark and `reproduce_all.py` now
  stratify on `cac_plus_score` and assert 1.01 / 2.28 / 5.07 / 4.69 / 5.53.
- **A retracted number was still advertised.** `agatston_vectorised.py` gave the real-CT speedup
  as 5.87x, withdrawn in manuscript v1.1.0 after the transposed/F-contiguous benchmark defect.
- **`agatston_vendor_ref.py` described itself wrongly, twice.** It said it mirrors the vendor's
  *per-voxel* reference logic: the vendor's loop is per connected object, and this file is **our
  re-implementation, not the vendor's code**. The docstring now says so, because it bounds what
  the package's byte-identity benchmark shows — it establishes agreement with this transcription,
  not with the vendor's own file, and the manuscript's C1 was produced against the latter.
- **`agreement_panel.py` quoted text the manuscript had retracted** ("statistically
  indistinguishable on every measure") along with the pre-correction denominator and sensitivity.
- **The tag pointed at the wrong commit — twice.** `v2.5.2-repro` was at a commit predating the
  fixes above, so a reader checking it out got no interval function and a benchmark asserting
  superseded medians, **and it returned PASS on them**. Re-pointed, and verified from a fresh
  anonymous clone at the tag.

### Added

- `analysis/speedup_intervals.py` — one documented function for every speedup interval the paper
  reports, stating the convention in full and asserting the published values. Written because the
  paper's all-50 interval could not be reproduced from the package: it read 1.26–3.01x and two
  independent implementations of the stated convention both return 1.25–3.01x. The paper now
  reports what this function returns.
- **`nlst_batch` in the cohort manifest**, with assertions in `spacing_audit.py`. The manuscript
  says the 274 exact-2.0 cases are "all in NLST batch 3" and that the 50 at ratio 1.25 split
  48/2; neither was checkable from the shipped manifest, which had study dates and no batch. Both
  hold exactly.
- `patches/monai_1.5.1_compatibility.patch`, `requirements-vendor-frozen-cu116.txt` and
  `TROUBLESHOOTING.md` — three artifacts Online Methods M9 promised and this package did not
  contain. The troubleshooting guide is written for this package rather than copied from the
  internal one, which is in Chinese and points at scripts a reader here does not have.

### Note on the vendor's pinned CUDA build

The vendor pins `torch==1.12.1+cu113` at release v1.0.0. The cross-stack environment here uses
cu116, because cu113 wheels do not run on this host's driver. Same PyTorch and MONAI versions,
different CUDA build; the manuscript's M9 no longer claims a match.

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

- **`analysis/agreement_panel.py`** — §3.1 and §3.7, the manuscript's headline result, which this
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
- **Windows console support in `scripts/reproduce_all.py`**, after a native-Windows run on
  2026-09-18 exposed two defects the Linux CI could not see. Windows PowerShell 5.1 -- the
  default shell on a stock install -- does not process VT sequences, so every status line
  printed a literal `[32m` before it. And under a GBK console, the default in a Chinese
  Windows install, the runner **crashed with UnicodeDecodeError before printing anything**,
  because the parent decoded child output with its locale while the child encoded with its
  own. A reviewer would have seen a traceback instead of a result. Colour is now conditional
  (NO_COLOR, then isatty, then an attempt to enable VT on Windows), statuses read `[PASS]` /
  `[FAIL]` / `[SKIP]` without it, child processes are pinned to UTF-8 on both sides, and this
  runner's own output is ASCII only -- the workspace convention, for exactly this reason.
- **Python 3.11 added to the CI matrix.** It was the gap: the same Windows run used 3.11 with
  numpy 2.4.6 and scipy 1.17.1 and passed, on an interpreter and a dependency pair the matrix
  had never covered.
- **`scripts/reproduce_all.py`** — one command that runs every available check and
  verifies the values the manuscript reports, rather than exit codes. Exit zero is not
  reproduction: `speedup_realct.py` prints a median and exits zero whether that median is
  1.97 or the withdrawn 5.87, which this README advertised for ten weeks. CI now runs this
  same entry point, so the documented command cannot drift from the tested one. Verified to
  fail when fed the wrong arm's scores.
- **`scripts/verify_cohort_manifest.py`** — checks the *shipped* manifest using nothing but
  this repository. CI's first run failed because it tried to run the *builder*, which reads
  private source tables from a sibling repo. A reader cloning this package is in CI's
  position: able to verify the artefact, not to rebuild it.
- **CI** — the checks needing no cohort access (C1 byte-identity, C5 spacing audit) plus
  the manifest denominators, on Python 3.10/3.12/3.13, with guards against a COCA-derived
  file or an internal identifier becoming tracked.
- **`SECURITY.md`**, **`CONTRIBUTING.md`**, this file.

### Changed

- **Four of the five checks need no data at all**, which the README had wrong: it labelled
  `speedup_realct.py` as needing the NLST images. It does not — it summarises the shipped
  50-case per-case timings. Re-*measuring* those timings needs images and a GPU;
  reproducing the published statistics from them needs neither.
- `matplotlib` dropped from `requirements.txt`. It was only needed by the figure generator
  removed with §3.6, leaving numpy and scipy — and scipy is not optional, since
  `scipy.ndimage.label` is the connected-component pass at the core of both Agatston
  implementations.

### Removed

- `analysis/coca_vs_reference.py`, folded into `analysis/agreement_panel.py`. Two scripts
  both reading the reader's COCA download and both reporting r was an invitation to update
  one and not the other; the panel now carries §3.1's zero-CAC rates alongside §3.7's
  agreement measures, and reproduces both (52.4% vs 42.7%; CCC 0.856).
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
