#!/usr/bin/env python3
"""§3.1 and §3.7: agreement against the COCA expert reference, for any scoring arm.

The manuscript's headline result. Correlation is deliberately *not* the headline
here: it measures association, is inflated by a wide dynamic range, and is blind
to systematic bias. On this cohort Pearson r on raw scores is 0.957 while Lin's
CCC is 0.856 and the mean difference is about -106 Agatston -- the same data,
and only the second pair describes agreement. Both are printed so the gap is
visible rather than asserted.

Run it twice, once per arm, to reproduce §3.7's finding that CAC Plus and the
unmodified vendor are statistically indistinguishable on every measure:

    python analysis/agreement_panel.py --scores my_cacplus.csv  --reference my_coca_gt.csv
    python analysis/agreement_panel.py --scores my_vendor.csv   --reference my_coca_gt.csv

Nothing COCA-derived ships in this repository: Stanford's Research Use Agreement
forbids publishing any portion of the Dataset, and its dataset page describes the
expert scores as part of the Dataset rather than a derivative of it. Both inputs
therefore come from your own COCA download -- see data/README.md. The scoring
engine is here, so anyone registered for COCA can score their own copy and
reproduce these numbers end to end.

Published values for CAC Plus v2.5.2 (n = 206), for comparison:
    CCC 0.856 (95% CI 0.766-0.904) · ICC(A,1) 0.857 · quadratic-weighted kappa
    0.734 (0.640-0.808) · CAC>0 sensitivity 72.0% · mean difference -106.1
    (95% LoA -870.6 to 658.4) · Pearson r 0.957 raw / 0.769 log / Spearman 0.754
"""
from __future__ import annotations

import argparse
import csv
import pathlib
import sys

import numpy as np

# SCCT 2024 four strata, as used throughout the manuscript.
STRATA = ("None (0)", "Mild (1-99)", "Moderate (100-399)", "Severe (>=400)")


def stratum(value: float) -> int:
    return 0 if value <= 0 else 1 if value < 100 else 2 if value < 400 else 3


def load(path: pathlib.Path, column: str) -> dict[str, float]:
    with path.open() as fh:
        reader = csv.DictReader(fh)
        for needed in ("patient_id", column):
            if needed not in (reader.fieldnames or []):
                sys.exit(f"{path.name}: needs a '{needed}' column, has {reader.fieldnames}")
        out = {}
        for row in reader:
            try:
                out[row["patient_id"].strip()] = float(row[column])
            except (TypeError, ValueError):
                continue
    if not out:
        sys.exit(f"{path.name}: no usable rows.")
    return out


def ccc(x: np.ndarray, y: np.ndarray) -> float:
    """Lin's concordance correlation coefficient."""
    mx, my = x.mean(), y.mean()
    sxy = ((x - mx) * (y - my)).mean()
    return 2 * sxy / (x.var(ddof=0) + y.var(ddof=0) + (mx - my) ** 2)


def icc_a1(x: np.ndarray, y: np.ndarray) -> float:
    """ICC(A,1): two-way, absolute agreement, single measurement (McGraw & Wong)."""
    m = np.column_stack([x, y])
    n, k = m.shape
    gm = m.mean()
    ms_r = k * ((m.mean(1) - gm) ** 2).sum() / (n - 1)
    ms_c = n * ((m.mean(0) - gm) ** 2).sum() / (k - 1)
    ms_e = ((m - m.mean(1, keepdims=True) - m.mean(0, keepdims=True) + gm) ** 2).sum() / (
        (n - 1) * (k - 1))
    return (ms_r - ms_e) / (ms_r + (k - 1) * ms_e + k * (ms_c - ms_e) / n)


def quadratic_weighted_kappa(a: list[int], b: list[int], k: int = 4) -> float:
    observed = np.zeros((k, k))
    for i, j in zip(a, b):
        observed[i, j] += 1
    weights = np.array([[(i - j) ** 2 / (k - 1) ** 2 for j in range(k)] for i in range(k)])
    expected = np.outer(np.bincount(a, minlength=k), np.bincount(b, minlength=k)).astype(float)
    expected *= observed.sum() / expected.sum()
    return 1 - (weights * observed).sum() / (weights * expected).sum()


def bootstrap_ci(fn, x, y, n=10000, seed=42):
    """Percentile CI. Seed fixed so the interval is reproducible, not merely stable."""
    rng = np.random.default_rng(seed)
    idx = np.arange(len(x))
    vals = [fn(x[s], y[s]) for s in (rng.choice(idx, len(idx), True) for _ in range(n))]
    return np.percentile(vals, [2.5, 97.5])


def pearson(x: np.ndarray, y: np.ndarray) -> float:
    return float(np.corrcoef(x, y)[0, 1])


def _average_ranks(v: np.ndarray) -> np.ndarray:
    """Ranks with ties averaged, as Spearman's rho requires.

    Ties are not an edge case on this cohort: 88 of 206 acquisitions have an
    expert reference of exactly zero. Ranking them arbitrarily instead of
    averaging gives rho = 0.734 where the correct value is 0.754 -- close enough
    to look right, which is why this is a function and not one line inline.
    """
    order = np.argsort(v, kind="mergesort")
    ranks = np.empty(len(v), dtype=float)
    sorted_v = v[order]
    i = 0
    while i < len(v):
        j = i
        while j + 1 < len(v) and sorted_v[j + 1] == sorted_v[i]:
            j += 1
        ranks[order[i:j + 1]] = (i + j) / 2.0 + 1.0
        i = j + 1
    return ranks


def spearman(x: np.ndarray, y: np.ndarray) -> float:
    return pearson(_average_ranks(x), _average_ranks(y))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--scores", required=True, type=pathlib.Path,
                    help="your scores: patient_id + the column named by --score-column")
    ap.add_argument("--reference", required=True, type=pathlib.Path,
                    help="your COCA expert reference: patient_id + gt_total")
    ap.add_argument("--score-column", default="agatston_score")
    ap.add_argument("--reference-column", default="gt_total")
    a = ap.parse_args()

    scores = load(a.scores, a.score_column)
    reference = load(a.reference, a.reference_column)
    ids = sorted(set(scores) & set(reference))
    if not ids:
        sys.exit("No patient_id is present in both files. COCA ids look like '1A', '100A'.")
    x = np.array([scores[i] for i in ids])
    g = np.array([reference[i] for i in ids])
    d = x - g

    print(f"n = {len(ids)} acquisitions present in both files")
    if len(ids) < len(scores) or len(ids) < len(reference):
        print(f"  ({len(scores)} in --scores, {len(reference)} in --reference; "
              f"intersection used)")

    print("\nAssociation -- NOT agreement, and not the headline:")
    print(f"  Pearson r, raw scores        {pearson(x, g):6.3f}   <- inflated by dynamic range")
    print(f"  Pearson r, log(1+x)          {pearson(np.log1p(x), np.log1p(g)):6.3f}")
    print(f"  Spearman rho                 {spearman(x, g):6.3f}")

    clo, chi = bootstrap_ci(ccc, x, g)
    ilo, ihi = bootstrap_ci(icc_a1, x, g)
    print("\nAgreement -- what a method-comparison study should report:")
    print(f"  Lin CCC                      {ccc(x, g):6.3f}   (95% CI {clo:.3f}-{chi:.3f})")
    print(f"  ICC(A,1), absolute           {icc_a1(x, g):6.3f}   (95% CI {ilo:.3f}-{ihi:.3f})")
    print(f"  Bland-Altman mean difference {d.mean():6.1f}   "
          f"(95% LoA {d.mean() - 1.96 * d.std(ddof=1):.1f} to "
          f"{d.mean() + 1.96 * d.std(ddof=1):.1f})")
    print(f"  Median / mean absolute error {np.median(np.abs(d)):6.1f} / {np.abs(d).mean():.1f}")

    sg = [stratum(v) for v in g]
    sx = [stratum(v) for v in x]
    print("\nClinical decision layer (SCCT 2024 four strata):")
    print(f"  Quadratic-weighted kappa     {quadratic_weighted_kappa(sg, sx):6.3f}")
    print(f"  Exact stratum agreement      {100 * np.mean(np.equal(sg, sx)):6.1f}%")
    print(f"  Within one stratum           {100 * np.mean(np.abs(np.array(sg) - np.array(sx)) <= 1):6.1f}%")
    sens = 100 * ((g > 0) & (x > 0)).sum() / max((g > 0).sum(), 1)
    spec = 100 * ((g == 0) & (x == 0)).sum() / max((g == 0).sum(), 1)
    print(f"  CAC>0 sensitivity / spec.    {sens:6.1f}% / {spec:.1f}%")
    # Section 3.1's separate claim: the automated zero rate exceeds the expert's,
    # which is the low-burden sensitivity gap stated there and referred back to
    # from 3.7. Published for COCA non-gated: 52.4% scored vs 42.7% reference.
    print(f"  Zero-CAC rate, scored        {100 * (x == 0).mean():6.1f}%"
          f"   (\u00a73.1)")
    print(f"  Zero-CAC rate, reference     {100 * (g == 0).mean():6.1f}%")
    missed = [i for i in ids if reference[i] > 0 and scores[i] == 0]
    if missed:
        burden = np.array([reference[i] for i in missed])
        print(f"  Expert-positive, scored 0    {len(missed)} of {int((g > 0).sum())}"
              f"   (missed burden: median {np.median(burden):.0f}, max {burden.max():.0f})")

    print("\nReciprocal table (rows = reference stratum, columns = scored stratum):")
    table = np.zeros((4, 4), dtype=int)
    for i, j in zip(sg, sx):
        table[i, j] += 1
    print("    " + "".join(f"{s.split()[0]:>10}" for s in STRATA))
    for i, name in enumerate(STRATA):
        print(f"  {name.split()[0]:<10}" + "".join(f"{v:>10}" for v in table[i]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
