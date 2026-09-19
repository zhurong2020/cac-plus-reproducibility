#!/usr/bin/env python3
"""Online Result R8: what the `min_calc_object_pixels` parameter changes.

The manuscript's R8 reports this benchmark and, until 2026-09-19, said the per-case
CSV was "included as Supplementary Material". It never was, and a first attempt to
correct that pointed at the wrong file -- the 50-case speedup CSV, which is a
different benchmark. The data is here now, and this script recomputes every number
R8 prints and asserts it.

Intervals are exact (Clopper-Pearson), matching the rest of the paper. R8's earlier
intervals were Wald, which is why they differed: for 11/100, Wald gives 4.9-17.1 and
the exact interval gives 5.6-18.8.
"""
from __future__ import annotations

import csv
import pathlib
import statistics
import sys

CSV = pathlib.Path(__file__).resolve().parents[1] / "results_expected" / "min_sensitivity_nlst_n100.csv"
MIN1, MIN3 = "score_min1_vendor_batch", "score_min3_v236"


def clopper_pearson(k: int, n: int) -> tuple[float, float]:
    """Exact binomial 95% CI, the same method the manuscript uses elsewhere."""
    from scipy.stats import beta
    lo = 0.0 if k == 0 else float(beta.ppf(0.025, k, n - k + 1))
    hi = 1.0 if k == n else float(beta.ppf(0.975, k + 1, n - k))
    return 100 * lo, 100 * hi


def main() -> int:
    rows = list(csv.DictReader(CSV.open()))
    n = len(rows)
    d = [abs(float(r[MIN1]) - float(r[MIN3])) for r in rows]
    differ = sum(1 for x in d if x != 0)
    recat = sum(1 for r in rows if r["band_min1"] != r["band_min3"])
    zero = sum(1 for r in rows if (float(r[MIN1]) == 0) != (float(r[MIN3]) == 0))

    print(f"cases                         : {n}")
    for label, k in (("any score difference", differ), ("risk-category change", recat),
                     ("crosses the CAC = 0 line", zero)):
        lo, hi = clopper_pearson(k, n)
        print(f"{label:<30}: {k}/{n} = {100*k/n:.1f}%  exact 95% CI {lo:.1f}-{hi:.1f}%")
    print(f"absolute difference           : median {statistics.median(d):.0f}  "
          f"mean {statistics.mean(d):.1f}  range {min(d):.0f}-{max(d):.0f}")

    checks = [("cases differing", differ, 58), ("reclassified", recat, 14),
              ("crossing zero", zero, 11), ("median absolute difference", statistics.median(d), 2),
              ("mean absolute difference", round(statistics.mean(d), 1), 4.6),
              ("maximum difference", max(d), 40)]
    bad = [f"{a}: got {b}, R8 says {c}" for a, b, c in checks if b != c]
    if bad:
        print("\nFAIL:\n  " + "\n  ".join(bad)); return 1
    print("\nPASS: every value Online Result R8 prints reproduces from this file.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
