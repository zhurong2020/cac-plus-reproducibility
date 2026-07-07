"""Reproduce the C2 real-CT speedup summary (manuscript §3.3, Figure 3b/c).

Reads results_expected/speedup_nlst_b3_50case.csv (the 50-case NLST batch 3 benchmark:
per-case vendor-naive vs CAC-Plus timings + byte-identity flag) and reproduces the
headline speedup statistics and per-stratum medians. Expected: median 5.87x, mean 7.48x,
50/50 byte-identical; per-stratum medians 2.00 / 6.97 / 12.54 / 14.21 / 16.57.
"""
from __future__ import annotations

import csv
from collections import defaultdict
from pathlib import Path

import numpy as np

CSV = Path(__file__).resolve().parents[1] / "results_expected" / "speedup_nlst_b3_50case.csv"
STRATA = ["zero", "1-9", "10-99", "100-399", ">=400"]


def main():
    sp, by_stratum, matches, n = [], defaultdict(list), 0, 0
    for r in csv.DictReader(open(CSV)):
        try:
            ratio = float(r["speedup_ratio_min1"])
        except (ValueError, KeyError):
            continue
        n += 1
        sp.append(ratio)
        by_stratum[r["stratum"]].append(ratio)
        if r["scores_match_min1"].strip().lower() == "true":
            matches += 1
    sp = np.array(sp)
    print(f"n cases          : {n}")
    print(f"byte-identity    : {matches}/{n}")
    print(f"speedup (real CT): median {np.median(sp):.2f}x  mean {sp.mean():.2f}x  max {sp.max():.2f}x")
    print("per-stratum median speedup:")
    for k in STRATA:
        vals = by_stratum.get(k, [])
        if vals:
            print(f"  {k:>8} (n={len(vals):>2}): {np.median(vals):.2f}x")


if __name__ == "__main__":
    main()
