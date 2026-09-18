# Contributing

## What this repository is for

Reproducing the numbers in one manuscript. That purpose sets the rules below, and they are
stricter than a typical research repository's in one specific way: **a change that makes a
script print a number different from the published one must fail the script, not update the
expectation.**

## The one rule that matters

Every analysis script asserts its published values. If you change an implementation and an
assertion trips, the assertion is the finding. Do not relax it to match new output.

That rule exists because of a real case. `analysis/spacing_audit.py` recomputes the count of
overlap-reconstruction acquisitions in §3.6 and got 280 where the manuscript said 274. The
manuscript's 274 turned out to be right — it counts acquisitions at a ratio of *exactly* 2.0
— but the sentence after it, claiming every other acquisition was a no-op, was wrong for six
of them. The manuscript was corrected, not the script. Had the script been adjusted to
print 274 and move on, the error in the paper would still be there.

## Manuscript-sync checklist

This package drifted behind the manuscript for about ten weeks, through two revisions and
two changes of target journal, and none of it was catchable by a test. If you touch the
manuscript, walk this list:

- [ ] **Section numbers.** Cutting a section renumbers the ones after it. The README's
      script-to-section table and every script docstring cite section numbers.
- [ ] **Retracted or corrected numbers.** The README once advertised a median speedup of
      5.87x for four months after that figure was withdrawn and replaced by 1.97x. The data
      file was right the whole time; only the prose was wrong.
- [ ] **Removed sections.** Scripts, figures and result tables belonging to a cut section
      should go with it. A reproducibility package that reproduces an analysis the paper does
      not contain invites the question of why it was removed.
- [ ] **Journal name.** In `README.md` and `CITATION.cff`, both of which named a journal that
      had already declined the paper.
- [ ] **Published values in assertions.** If a number in the paper changes, the assertion
      changes with it, in the same commit.

## Data, and what must never be committed

Patient data is never committed. Beyond that, the two cohorts are governed differently and
the difference is load-bearing:

- **NLST** permits publishing participant identifiers and SeriesInstanceUIDs, which is why
  the manifest ships in full.
- **COCA** does not. Stanford's Research Use Agreement forbids publishing "any portion" of
  the Dataset, and the expert calcium scores are described by Stanford as part of the
  Dataset. Nothing COCA-derived belongs here — not case identifiers, not the expert
  reference, and not our own scores keyed to COCA identifiers.

The pre-commit hook blocks the obvious shapes. Enable it:

```bash
git config core.hooksPath .githooks
```

## Style

Match the surrounding code. Scripts are standard-library plus NumPy where possible, print
their results to stdout, and carry their expected values as assertions.
