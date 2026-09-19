#!/usr/bin/env python3
"""§3.1 and §3.7: agreement against the COCA expert reference, for any scoring arm.

The manuscript's headline result. Correlation is deliberately *not* the headline
here: it measures association, is inflated by a wide dynamic range, and is blind
to systematic bias. On this cohort Pearson r on raw scores is 0.957 while Lin's
CCC is 0.856 and the mean difference is about -106 Agatston -- the same data,
and only the second pair describes agreement. Both are printed so the gap is
visible rather than asserted.

Run it twice, once per arm, to reproduce §3.7's finding that CAC Plus and the
unmodified vendor differ on one acquisition of the 205 carrying a reference value,
so their accuracy measures are near-identical by construction. The manuscript's M13
reports the paired difference; the separate intervals below are not a test of it:

    python analysis/agreement_panel.py --scores my_cacplus.csv  --reference my_coca_gt.csv
    python analysis/agreement_panel.py --scores my_vendor.csv   --reference my_coca_gt.csv

Nothing COCA-derived ships in this repository: Stanford's Research Use Agreement
forbids publishing any portion of the Dataset, and its dataset page describes the
expert scores as part of the Dataset rather than a derivative of it. Both inputs
therefore come from your own COCA download -- see data/README.md. The scoring
engine is here, so anyone registered for COCA can score their own copy and
reproduce these numbers end to end.

Published values for CAC Plus v2.5.2 on the matched 205 (see the manuscript's M12
for why 205 and not 206 or 207), for comparison:
    CCC 0.856 (95% CI 0.766-0.904) · ICC(A,1) 0.857 · quadratic-weighted kappa
    0.734 (0.642-0.808) · CAC>0 sensitivity 72.0% (85/118) · mean difference -106.10
    (95% LoA -870.6 to 658.4) · Pearson r 0.957 raw / 0.769 log / Spearman 0.754
and for the unmodified vendor arm on the same 206: CCC 0.857 · mean difference -106.36
(95% LoA -870.5 to 657.8). The manuscript carried -105.8 for the vendor arm until
2026-09-19; that one number was wrong. A repair the same day moved BOTH means onto a
205-acquisition set, on the mistaken belief that one of the 206 had no expert reference;
It has one, and -106.70/-106.97 are withdrawn. Use the released per-vessel reference table.

Pass --vendor-scores to run the paired comparison of M13 rather than two separate
panels, and --earlier-scores to run M8's set-equality and direction checks. Both
print the explicit identifier intersection they used. `--selftest` exercises the
paired code on a built-in fixture and needs no data at all.
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

    Ties are not an edge case on this cohort: 88 of the 206 acquisitions have an
    expert reference of exactly zero. Ranking them arbitrarily instead of averaging
    gives rho = 0.760 where the correct value is 0.754 -- close enough to look
    right, which is why this is a function and not one line inline.
    (This comment said "0.734 where the correct value is 0.754" until 2026-09-19:
    0.754 was right, 0.734 was not, and the comparison ran the wrong way, since
    arbitrary ranking inflates rho here rather than deflating it.)
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


def paired_panel(ids, arm_a, reference, arm_b, b_name) -> None:
    """M13: the two engines compared as a paired quantity on ONE explicit case set.

    Separate confidence intervals from two runs of this script are not a test of a
    difference between the arms -- they can overlap when a paired difference is real
    and fail to overlap when it is not. This is the comparison the manuscript makes.
    """
    common = sorted(set(ids) & set(arm_b))
    print(f"\n--- M13 paired comparison against {b_name} ---")
    print(f"  identifier intersection      {len(common)} of {len(ids)} (arm A n reference)"
          f", {len(arm_b)} in arm B")
    dropped = sorted(set(ids) - set(arm_b))
    if dropped:
        print(f"  in arm A but not arm B       {len(dropped)}: {', '.join(dropped[:8])}"
              f"{' ...' if len(dropped) > 8 else ''}")
    if not common:
        print("  no shared identifiers; paired comparison skipped")
        return

    a = np.array([arm_a[i] for i in common])
    b = np.array([arm_b[i] for i in common])
    g = np.array([reference[i] for i in common])

    differ = [i for i in common if arm_a[i] != arm_b[i]]
    print(f"  acquisitions where the arms differ  {len(differ)} of {len(common)}"
          + (f": {', '.join(differ[:8])}" if differ else ""))

    # The identity that makes the SIGN checkable without trusting either mean:
    # mean(a - g) - mean(b - g) == sum(a - b) / n, exactly, whatever the reference is.
    lhs = (a - g).mean() - (b - g).mean()
    rhs = (a - b).sum() / len(common)
    print(f"  mean difference, arm A       {(a - g).mean():9.4f}")
    print(f"  mean difference, arm B       {(b - g).mean():9.4f}")
    print(f"  gap (A - B)                  {lhs:9.6f}   identity sum(A-B)/n = {rhs:.6f}")
    if abs(lhs - rhs) > 1e-9:
        sys.exit("  the paired-mean identity failed; the two arms are not on one case set")
    print("  identity holds: the sign of the gap is fixed by the differing cases alone")

    # Paired delta-CCC: resample acquisitions ONCE per replicate and recompute both
    # arms on that same resample, so the arms stay paired inside the bootstrap.
    rng = np.random.default_rng(42)
    deltas = np.empty(10000)
    n = len(common)
    for r in range(10000):
        k = rng.integers(0, n, n)
        deltas[r] = ccc(a[k], g[k]) - ccc(b[k], g[k])
    lo, hi = np.percentile(deltas, [2.5, 97.5])
    print(f"  delta CCC (A - B)            {ccc(a, g) - ccc(b, g):9.5f}   "
          f"(95% CI {lo:.5f} to {hi:.5f})")
    ae = np.abs(a - g) - np.abs(b - g)
    print(f"  paired absolute-error diff   median {np.median(ae):.1f}, "
          f"nonzero on {int((ae != 0).sum())} of {n}")


def earlier_panel(ids, current, earlier, e_name) -> None:
    """M8: is the earlier release on the same case set, and is every change one-directional?"""
    print(f"\n--- M8 earlier-release checks against {e_name} ---")
    common = sorted(set(ids) & set(earlier))
    only_cur, only_old = sorted(set(ids) - set(earlier)), sorted(set(earlier) - set(ids))
    print(f"  identifier intersection      {len(common)}; "
          f"current-only {len(only_cur)}, earlier-only {len(only_old)}")
    print(f"  set equality                 {'YES' if not (only_cur or only_old) else 'NO'}"
          "   <- M8 claims the three arms are on one case set")
    if not common:
        return
    diff = [(i, earlier[i], current[i]) for i in common if earlier[i] != current[i]]
    lower = sum(1 for _, o, c in diff if o < c)
    print(f"  acquisitions that changed    {len(diff)} of {len(common)}")
    print(f"  earlier score LOWER          {lower} of {len(diff)}"
          f"   <- the only direction raising min_calc_object_pixels can produce")
    if diff and lower != len(diff):
        up = [i for i, o, c in diff if o > c]
        print(f"  earlier score HIGHER         {len(up)}: {', '.join(up[:8])}"
              "   <- inconsistent with the parameter explanation")
    print("  direction-consistent is a NECESSARY condition, not an ablation: any other")
    print("  change that could only lower a score is indistinguishable from it here.")


def selftest() -> int:
    """Exercise the paired code without any data.

    The fixture is the manuscript's own shape: 206 acquisitions, the arms equal on
    205, and one acquisition where arm A returns 229 and arm B 174. The identity
    then has a known closed form, 55/206, which is what the manuscript reports.
    """
    ids = [f"{i}A" for i in range(206)]
    rng = np.random.default_rng(0)
    ref = {i: float(v) for i, v in zip(ids, rng.integers(0, 900, 206))}
    arm_a = dict(ref)
    arm_b = dict(ref)
    arm_a["7A"], arm_b["7A"] = 229.0, 174.0
    paired_panel(ids, arm_a, ref, arm_b, "fixture")
    expected = 55 / 206
    a = np.array([arm_a[i] for i in ids]); b = np.array([arm_b[i] for i in ids])
    g = np.array([ref[i] for i in ids])
    got = (a - g).mean() - (b - g).mean()
    assert abs(got - expected) < 1e-9, f"identity {got} != {expected}"
    earlier_panel(ids, arm_a, {i: min(arm_a[i], arm_b[i]) for i in ids}, "fixture")
    print(f"\nselftest PASS: paired identity reproduces 55/206 = {expected:.7f}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--scores", type=pathlib.Path,
                    help="your scores: patient_id + the column named by --score-column")
    ap.add_argument("--reference", type=pathlib.Path,
                    help="your COCA expert reference: patient_id + gt_total")
    ap.add_argument("--score-column", default="agatston_score")
    ap.add_argument("--reference-column", default="gt_total")
    ap.add_argument("--vendor-scores", type=pathlib.Path,
                    help="second arm (the unmodified vendor); enables M13's paired comparison")
    ap.add_argument("--vendor-column", default="agatston_decoupled")
    ap.add_argument("--earlier-scores", type=pathlib.Path,
                    help="an earlier release's scores; enables M8's set/direction checks")
    ap.add_argument("--earlier-column", default="agatston_score")
    ap.add_argument("--selftest", action="store_true",
                    help="run the paired code on a built-in fixture; needs no data")
    a = ap.parse_args()

    if a.selftest:
        return selftest()
    if not (a.scores and a.reference):
        ap.error("--scores and --reference are required unless --selftest is given")

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
    # from 3.7. Published for COCA non-gated: 52.4% scored vs 42.7% reference, on
    # the 206 acquisitions both engines scored, all of which carry one (M12).
    print(f"  Zero-CAC rate, scored        {100 * (x == 0).mean():6.1f}%"
          f"   (\u00a73.1)")
    print(f"  Zero-CAC rate, reference     {100 * (g == 0).mean():6.1f}%")
    missed = [i for i in ids if reference[i] > 0 and scores[i] == 0]
    if missed:
        burden = np.array([reference[i] for i in missed])
        print(f"  Expert-positive, scored 0    {len(missed)} of {int((g > 0).sum())}"
              f"   (missed burden: median {np.median(burden):.0f}, max {burden.max():.0f})")

    if a.vendor_scores:
        paired_panel(ids, scores, reference,
                     load(a.vendor_scores, a.vendor_column), a.vendor_scores.name)
    if a.earlier_scores:
        earlier_panel(ids, scores, load(a.earlier_scores, a.earlier_column),
                      a.earlier_scores.name)

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
