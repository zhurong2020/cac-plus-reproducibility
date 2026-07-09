"""Reproduce the C2 real-CT speedup summary (manuscript §3.3, Figure 3b/c).

Reads results_expected/speedup_nlst_b3_50case.csv (the 50-case NLST batch 3 benchmark:
per-case vendor-naive vs CAC-Plus timings + byte-identity flag) and reproduces the
headline speedup statistics and per-stratum medians.

Expected: **median 1.97x, mean 2.67x, 50/50 byte-identical**; per-stratum medians
1.09 / 2.48 / 5.07 / 4.69 / 5.53 (zero / 1-9 / 10-99 / 100-399 / >=400).

The 50-case cohort is deliberately stratified with 30 zero-CAC scans, whose masks hold
~2 voxels; the Agatston step has almost nothing to do there (1.09x). The vectorised path
earns its keep on the calcium-bearing strata (2.5-5.5x). Report the strata, not one median.

⚠️ Corrected 2026-07-09. The previous expected values (median 5.87x, per-stratum
2.00/6.97/12.54/14.21/16.57) came from a run with two defects:
  * the CT was read raw while the mask came from the LPS-transposing loader, so the two
    were transposed relative to each other and every density weight was sampled from the
    wrong voxels (e.g. 116842 scored 0; the correct score is 2);
  * `nibabel.get_fdata()` returns an F-contiguous array and `.astype()` preserves that
    layout. The vendor's per-region loop is layout-sensitive (38.6 s F-contiguous vs
    12.8 s C-contiguous on case 127367); the vectorised path is not. Roughly 3x of the
    old speedup was Fortran memory order, not optimisation.
Production reaches the scorer via torch->numpy, i.e. C-contiguous. Both implementations
now receive the identical C-contiguous buffer. The superseded CSV is retained as
results_expected/_INVALID_transposed_ct_*.csv.
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
