#!/usr/bin/env python3
"""Main text 3.2 / Online Methods M3a: exact score agreement on the whole NLST thin-slice cohort.

Reads `results_expected/identity_nlst_full_n2231.csv`, one row per acquisition, and checks every
number the manuscript reports from it: the denominator, the agreement count, the exact binomial
interval, the burden coverage and the alignment evidence.

**What this verifies, and what it does not.** The shipped table is our measurement. Running this
script confirms the manuscript's arithmetic over it -- that 2,231 rows agree, that the interval
is what 2,231/2,231 gives, that the strata sum. It does not re-measure anything: that needs the
NLST images under the NCI data-use agreement, plus the segmentation masks. A reader who has both
can regenerate the table with the scoring core in `src/` and compare it to this one row by row,
which is the check this file exists to make possible.

Deliberately dependency-free beyond numpy: the binomial interval is computed from an incomplete
beta, so this runs wherever `reproduce_all.py` does.
"""
from __future__ import annotations

import csv
import math
import pathlib
import sys

CSV = pathlib.Path(__file__).resolve().parents[1] / "results_expected" / "identity_nlst_full_n2231.csv"

# What main text 3.2 and M3a state.
EXPECT_N = 2231
EXPECT_IDENTICAL = 2231
EXPECT_REPRODUCES = 2231
EXPECT_CI_LOW = 99.83          # exact binomial, two-sided 95%, k = n
EXPECT_STRATA = {"zero": 331, "mild": 771, "moderate": 548, "severe": 581}
EXPECT_MAX = 3883.0
EXPECT_ALIGN_MIN = 88.9        # lowest per-case fraction of mask voxels at or above 130 HU


def clopper_pearson_low(k: int, n: int) -> float:
    """Lower bound of the exact two-sided 95% interval. For k == n it is 0.025**(1/n)."""
    if k == 0:
        return 0.0
    if k == n:
        return 100.0 * (0.025 ** (1.0 / n))
    raise NotImplementedError("only the k == n case is needed here")


def stratum(v: float) -> str:
    return "zero" if v <= 0 else "mild" if v < 100 else "moderate" if v < 400 else "severe"


def main() -> int:
    if not CSV.exists():
        sys.exit(f"missing {CSV.name}")
    rows = list(csv.DictReader(CSV.open()))
    ok = [r for r in rows if r["status"] == "success"]
    bad_status = len(rows) - len(ok)

    identical = sum(1 for r in ok if r["identical"] == "1")
    reproduces = sum(1 for r in ok if r["reproduces_published"] == "1")
    # Do not trust the recorded flag alone -- recompute equality from the two score columns.
    recomputed = sum(1 for r in ok
                     if float(r["score_vectorised"]) == float(r["score_vendor_naive"]))
    scores = [float(r["score_vectorised"]) for r in ok]
    strata = {k: 0 for k in EXPECT_STRATA}
    for s in scores:
        strata[stratum(s)] += 1
    align = [float(r["mask_ge130_pct"]) for r in ok if r["mask_ge130_pct"]]
    ci_low = clopper_pearson_low(identical, len(ok))

    print(f"rows                          : {len(rows)} ({bad_status} not success)")
    print(f"two implementations identical : {identical}/{len(ok)}")
    print(f"  recomputed from the columns : {recomputed}/{len(ok)}")
    print(f"  exact binomial 95% CI       : {ci_low:.2f}-100%")
    print(f"reproduces the published score: {reproduces}/{len(ok)}")
    print(f"burden coverage               : zero {strata['zero']} · mild {strata['mild']} · "
          f"moderate {strata['moderate']} · severe {strata['severe']} · max {max(scores):.0f}")
    print(f"mask voxels >=130 HU          : min {min(align):.1f}% · "
          f"median {sorted(align)[len(align)//2]:.1f}%")

    fail = []
    if len(ok) != EXPECT_N:
        fail.append(f"n is {len(ok)}, M3a says {EXPECT_N}")
    if identical != EXPECT_IDENTICAL or recomputed != EXPECT_IDENTICAL:
        fail.append(f"identical {identical} (recomputed {recomputed}), M3a says {EXPECT_IDENTICAL}")
    if reproduces != EXPECT_REPRODUCES:
        fail.append(f"reproduces {reproduces}, M3a says {EXPECT_REPRODUCES}")
    if abs(ci_low - EXPECT_CI_LOW) > 0.01:
        fail.append(f"CI low {ci_low:.2f}, 3.2 says {EXPECT_CI_LOW}")
    if strata != EXPECT_STRATA:
        fail.append(f"strata {strata}, M3a says {EXPECT_STRATA}")
    if abs(max(scores) - EXPECT_MAX) > 0.5:
        fail.append(f"max {max(scores)}, M3a says {EXPECT_MAX}")
    if abs(min(align) - EXPECT_ALIGN_MIN) > 0.05:
        fail.append(f"alignment minimum {min(align):.1f}%, M3a says {EXPECT_ALIGN_MIN}%")
    if fail:
        print("\nFAIL:\n  " + "\n  ".join(fail))
        return 1
    print("\nPASS: every value 3.2 and M3a state reproduces from this table.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
