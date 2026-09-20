#!/usr/bin/env python3
"""The real-CT speedup intervals the paper reports, from one documented function.

Scope, stated first because an earlier version of this line did not: this reads the 50-case
real-CT benchmark only. The synthetic-cohort intervals in M12a are not computed here.

The manuscript states its convention once -- "bootstrap 95% CIs of the median
(10,000 resamples, seed 42)" -- and then prints intervals computed by a script that
was never released. External review found the consequence: the published all-50
interval is 1.26-3.01x, and two independent implementations of the stated convention
both give 1.25-3.01x. A 0.01 discrepancy is not important in itself; a reader who
cannot reproduce a stated interval from the released package has no way to know that,
which is.

So the function lives here, the paper reports what it returns, and this script
asserts the values the paper prints.

Convention, stated in full so it is not ambiguous:
  * resample acquisitions with replacement, n out of n, 10,000 times;
  * take the median of each resample;
  * report the 2.5th and 97.5th percentiles of those medians (percentile method,
    not BCa, no bias correction);
  * numpy.random.RandomState(42), drawn once and reused for every replicate.

Paired differences use the SAME resampled indices for both arms, which is what makes
them paired; see the manuscript's Online Methods M13.
"""
from __future__ import annotations

import csv
import pathlib
import sys

import numpy as np

CSV = pathlib.Path(__file__).resolve().parents[1] / "results_expected" / "speedup_nlst_b3_50case.csv"
SEED, REPLICATES = 42, 10_000


def median_ci(x: np.ndarray, seed: int = SEED, replicates: int = REPLICATES):
    """Bootstrap 95% CI of the median, percentile method."""
    if len(x) == 0:
        return (float("nan"), float("nan"))
    rs = np.random.RandomState(seed)
    medians = [np.median(rs.choice(x, len(x), replace=True)) for _ in range(replicates)]
    lo, hi = np.percentile(medians, [2.5, 97.5])
    return float(lo), float(hi)


def stratum(score: float) -> str:
    if score == 0: return "zero"
    if score < 10: return "1-9"
    if score < 100: return "10-99"
    if score < 400: return "100-399"
    return ">=400"


def main() -> int:
    with CSV.open(newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))

    # Recompute the ratio from the two timings rather than reading the stored column. An
    # injection test (tests/test_analysis_mutations.py) zeroed the optimised durations and this
    # script still passed, because it believed a derived column -- the same defect the
    # full-cohort checker had. A duration of zero or less is not a fast run; it is a broken row.
    vendor_s = np.array([float(r["vendor_naive_min1_s"]) for r in rows])
    ours_s = np.array([float(r["cac_plus_optimized_s"]) for r in rows])
    if (ours_s <= 0).any() or (vendor_s <= 0).any():
        n = int((ours_s <= 0).sum() + (vendor_s <= 0).sum())
        print(f"FAIL: {n} non-positive duration(s); a timing table cannot contain one")
        return 1
    sp = vendor_s / ours_s
    stored = np.array([float(r["speedup_ratio_min1"]) for r in rows])
    drift = np.abs(sp - stored)
    if drift.max() > 0.005:
        print(f"FAIL: recomputed speedup differs from the stored column by up to "
              f"{drift.max():.4f} on {int((drift > 0.005).sum())} row(s)")
        return 1
    cur = np.array([float(r["cac_plus_score"]) for r in rows])

    lo, hi = median_ci(sp)
    print(f"all {len(sp)}           median {np.median(sp):.2f}x  95% CI {lo:.2f}-{hi:.2f}x")
    pos = cur > 0
    plo, phi = median_ci(sp[pos])
    print(f"calcium-positive {pos.sum():>2}  median {np.median(sp[pos]):.2f}x  95% CI {plo:.2f}-{phi:.2f}x")
    print(f"zero             {(~pos).sum():>2}  median {np.median(sp[~pos]):.2f}x")
    print("per stratum, on the CAC Plus v2.5.2 score:")
    for k in ("zero", "1-9", "10-99", "100-399", ">=400"):
        v = sp[np.array([stratum(s) == k for s in cur])]
        if len(v):
            print(f"  {k:>8} (n={len(v):>2}): {np.median(v):.2f}x")

    # Assert what the manuscript prints, so this fails rather than reporting a number
    # that disagrees with it.
    checks = [
        ("all-50 median", round(float(np.median(sp)), 2), 1.97),
        ("all-50 CI low", round(lo, 2), 1.25),
        ("all-50 CI high", round(hi, 2), 3.01),
        ("calcium-positive n", int(pos.sum()), 29),
        ("calcium-positive median", round(float(np.median(sp[pos])), 2), 3.30),
        ("calcium-positive CI low", round(plo, 2), 2.65),
        ("calcium-positive CI high", round(phi, 2), 4.91),
        ("zero-stratum median", round(float(np.median(sp[~pos])), 2), 1.01),
    ]
    bad = [f"{n}: got {g}, manuscript says {w}" for n, g, w in checks if g != w]
    if bad:
        print("\nFAIL:\n  " + "\n  ".join(bad))
        return 1
    print("\nPASS: every real-CT interval matches the value the manuscript reports.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
