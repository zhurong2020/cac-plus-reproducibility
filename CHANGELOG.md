# Changelog

All notable changes to this reproducibility package.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).
Versions track the CAC Plus engine release they reproduce, suffixed `-repro`.

## [v2.5.2-repro.7] — the package says what the manuscript says (2026-09-20)

Round six of external review found the package still asserting three things the manuscript had
withdrawn or corrected, and the runner asserting less than the manuscript publishes.

### Fixed

- **`data/README.md`** no longer says the six omitted COCA acquisitions "cannot move a
  stratum-level result". That was withdrawn: four are reference-positive and two reference-zero,
  their predictions were never computed, so performance on them is **unmeasured** — a different
  statement from unaffected. A low reference does not constrain a prediction.
- **`analysis/agreement_panel.py`**: `earlier_panel()` no longer claims the three arms share one
  case set. The earlier-release arm is a **205-of-206 subset**; one acquisition was scored only
  after that release. The panel now reports subset membership and says an accuracy-only
  acquisition is expected rather than a defect.
- **The selftest fixture was handing `earlier_panel()` all 206**, so the subset branch had never
  executed. It now withholds one acquisition — deliberately not the differing one, or the
  direction check would pass on an empty set — and asserts both properties.

### Changed

- **The COCA acceptance criteria now include the ΔCCC upper bound and the published
  specificity.** Both are published values that nothing asserted; the interval width was
  unchecked. Both were verified against the real COCA arms **before** being added, not copied
  from the manuscript. That run also settled a value our own records disagreed about: the
  released panel returns a lower bound of −0.00053, not the −0.00054 one internal ledger
  claimed. All eleven checks now pass together with real data for the first time.
- **`README.md`** gains the three-level verifiability summary mirrored from Online Methods M17
  (re-measured / recomputed / restricted), and states that level-2 checks need **no additional
  download** rather than "no data" — they read de-identified NLST per-acquisition tables this
  repository ships on purpose.

## [v2.5.2-repro.6] — tests for the tests, and provenance that names the callee (2026-09-20)

Nothing had ever asked whether a check notices a wrong table. External review perturbed
`identity_nlst_full_n2231.csv` four ways and the checker returned success on **three**.

### Added

- **`tests/mutate.py`** — a shared injection-test fixture, so adding one to a new check costs a
  few lines. Two properties are enforced rather than remembered, because the first attempt to
  reproduce that report got the wrong answer by writing a mutated file without closing it: the
  **unmutated control must pass** before any mutation result is read, and a mutation that does
  not change the bytes is reported as **vacuous**, not as caught.
- **`tests/test_analysis_mutations.py`** — the four reported perturbations kept verbatim plus
  ten more across the other three checks. All 14 caught. Run by `scripts/reproduce_all.py`, so
  CI enforces them.
- **`src/callee_provenance.py`** — a `script_version` column names the caller. This records the
  **callee**: qualified name, module path, source SHA-256, file SHA-256, repository commit and
  worktree state. C1's two arms called different comparators while both tables recorded the same
  driver version, truthfully.
- **`scripts/record_callee_provenance.py`** + `results_expected/identity_nlst_full_n2231.provenance.md`
  — the full-cohort table predates that recording, so its provenance is reconstructed, says so
  in its own text, and is anchored on a fact the script re-verifies every run: the last commit
  touching either comparator predates the first row's timestamp. A later edit makes it fail
  rather than print a stale digest.

### Fixed

- **`analysis/full_cohort_identity.py`** recomputed one predicate from the numeric columns and
  then trusted a recorded flag for the other — half the lesson applied. It now recomputes both,
  asserts zero failed rows, identifier uniqueness and non-blankness, and the alignment median
  with its denominator.
- **`analysis/speedup_intervals.py`** — found by the new suite, same defect class: it read a
  stored `speedup_ratio` column instead of recomputing it from the two timings. It now
  recomputes, rejects non-positive durations, and checks itself against the stored column. Its
  header also promised *every* speedup interval; it reads only the real-CT benchmark.
- **`README.md`** said "All 4 runnable checks" and listed a fraction of the scripts.

## [v2.5.2-repro.5] — the identity claim's real-CT arm, in full (2026-09-20)

Section 3.2's real-CT arm was a 50-case subset. It is now the **entire NLST thin-slice cohort**,
and the table it rests on ships here.

### Added

- **`results_expected/identity_nlst_full_n2231.csv`** — 2,231 rows, one per acquisition: both
  implementations' Agatston scores, the published v2.5.2 score, the per-case fraction of mask
  voxels at or above 130 HU, and provenance columns (script version, processing date, spacing
  source, series identifier). **2,231 of 2,231 bit-identical**, exact binomial 95% CI
  **99.83–100%**; the paper previously claimed 50/50, lower bound 92.9%.
- **`analysis/full_cohort_identity.py`** — check 7 of 9, no download needed. It **recomputes
  equality from the two score columns rather than trusting the recorded flag**, which is not
  pedantry: an injection test that corrupted one score left the flag reading 1 and was caught
  only by the recomputation. It also checks the denominator, the interval, the four strata, the
  maximum and the alignment minimum.

### Why the table is worth shipping

The claim it supports was previously verifiable only by us. A reader can now confirm the
arithmetic in seconds, and a reader with NLST access under the NCI agreement can regenerate the
table with the scoring core here and compare row by row. What the shipped check does **not** do
is re-measure — `data/README` says so in the same words.

### Changed

- The runner is 9 checks, 8 of which need no data.

## [v2.5.2-repro.3] — the 206 denominator restored (2026-09-19)

**Cite this tag, not `.2`.** `.2`'s acceptance criteria carry a denominator that was withdrawn
hours after it was tagged, so a reader who clones `.2` and reproduces the corrected results is
told the check failed. `.2` is left in place because an immutable tag that has been published is
not re-pointed; it is simply superseded.

### Fixed

- 🔴 **The 205 denominator was wrong and came from an incomplete file.** `.2` moved the COCA
  acceptance criteria to a 205-acquisition set, on the belief that one of the 206 jointly scored
  acquisitions had no expert reference. It has one. The file used as the reference was a derived
  three-way comparison table missing that row; its absence was read as a missing reference rather
  than a missing row. Verified against the source cohort's own released score table: **207 of 207
  expert values agree exactly, 0 mismatches.** Restored: `n = 206`, `72.0%`, `52.4%`, `42.7%`,
  `-106.1`, Spearman `0.754`.
- **The paired selftest fixture and its identity move to 55/206** = 0.2669903, which the real
  data reproduces to seven decimals.
- **The tie-handling comment was half right and stating its comparison backwards.** It said
  arbitrary ranking gives rho = 0.734 where the correct value is 0.754. 0.754 was right; 0.734
  was not; and arbitrary ranking *inflates* rho here (0.760), it does not deflate it.
- The zero-rate comment still quoted the 206-denominator pair from before the engine rebaseline.

### Added

- **`data/README` now says which COCA file is the reference standard** and why it matters: build
  `--reference` from the release's own score table, not from a derived comparison table. Two
  intermediate tables used during this work hold different row sets — one missing two rows, one
  carrying five extra — and both agree with the release on every row they do hold, so nothing
  looks wrong until you count. The release table is identifiable at a glance because it carries
  the per-vessel breakdown.
- A note that the manuscript scores 207 of the release's 213, so a reader who scores all 213
  knows why their denominators differ.

### Changed

- The README's format example no longer uses literal case identifiers. This package ships no
  COCA content and its documentation should not either.

## [v2.5.2-repro.2] — the verification tooling itself reviewed (2026-09-19)

Round 4's sixth reviewer read this package rather than only the manuscript, and the two findings
it marked Major were both here. They are the reason this release exists.

### Fixed

- 🔴 **The runner's COCA acceptance criteria were three corrections out of date.** The COCA check
  required the panel to print `n = 206`, `72.0%`, `42.7%` and `-106.1` — every one a value the
  manuscript had already superseded. A reader who scored their own COCA copy and **reproduced the
  corrected results** would have been told the check FAILED. An acceptance criterion is a
  published claim as much as a sentence is, and it has to move when the claim does. Now
  `n = 205`, `71.8%`, `52.7%`, `42.9%`, `-106.7`.
- 🔴 **Executing that branch then found two more superseded values in the paper.** Every earlier
  run of `reproduce_all.py`, including reviewers', *skipped* the COCA check, because it needs
  data the reader supplies. Run against real scores it printed a log-Pearson of 0.771 and a
  Spearman ρ of 0.756 where the manuscript said 0.769 and 0.754. Neither published value is
  reproducible from the matched 205 or from the 206 with the missing reference imputed as zero.
  A check that is always skipped verifies nothing; passing 7 of 7 with one skip was not a green
  build.
- **`analysis/speedup_intervals.py` was not called by `reproduce_all.py`** although the manuscript
  cited it as the provenance of every speedup interval. It is now check 5 of 8.
- **The MONAI patch was described backwards.** `patches/monai_1.5.1_compatibility.patch` branches
  on the installed MONAI version and **omits** `SwinUNETR(img_size=...)` on 1.5+; the README and
  Online Methods M9 both said it "restores" the argument. Its target path
  (`external/cac_plus_reference/ai_cac_inference_lib.py`) is not in this package either, so
  `git apply` fails. The file now carries a header saying it is documentation of a change inside
  the private toolkit, not a runnable step.
- **`requirements.txt` was labelled "the modern stack every reported score was produced on".** It
  is numpy and scipy with lower bounds — the analysis stack for this package. The scoring
  environment (PyTorch 2.9.1+cu128, MONAI 1.5.1, vendor weights) is part of the deployment
  toolkit this package does not distribute, and the README now says which is which.

### Added

- **`agreement_panel.py --vendor-scores`** — Online Methods M13's paired comparison, which the
  script could not do: it computed one arm at a time, and two separate confidence intervals are
  not a test of a difference. The paired path prints the explicit identifier intersection, the
  paired ΔCCC (resampling acquisitions once per replicate so the arms stay paired), and asserts
  the identity `mean(A−ref) − mean(B−ref) == sum(A−B)/n`, which fixes the **sign** of the gap
  from the differing cases alone, without trusting either mean. That identity is what proved the
  manuscript's published pair impossible.
- **`agreement_panel.py --earlier-scores`** — M8's set-equality and direction checks.
- **`agreement_panel.py --selftest`** — runs the paired code on a built-in fixture with no data,
  so the COCA-dependent logic is exercised on every run. It reproduces 55/205 = 0.2682927.
- **`reproduce_all.py --coca-vendor-scores`** — threads the second arm through to the panel.

### Changed

- 🔴 **`v2.5.2-repro` stops moving.** It was re-pointed four times during round 4, so it named no
  fixed state — which matters most here, because the round's findings were about the verification
  scripts themselves, and the reviewer had to quote a commit SHA to say what it had read. From
  now the moving tag is frozen and each state gets an immutable identifier: **`v2.5.2-repro.1`**
  at `27495c6` (what round 4 reviewed after its first pass) and **`v2.5.2-repro.2`** at this tip.
  Subsequent repairs get `.3`, and no suffixed tag is ever re-pointed.
- "byte-identical" is reserved for comparisons of arrays or file contents; equality of Agatston
  scores is now called exact score agreement, in the runner's check names as in the manuscript.

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
