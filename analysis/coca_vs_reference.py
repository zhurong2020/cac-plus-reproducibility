"""Reproduce the COCA non-gated vs expert-reference correlation (manuscript §3.1).

Expected: n = 206, Pearson r ~ 0.957, zero-CAC 52.4% (AI) vs 42.7% (reference).

Why this script needs a file from you
------------------------------------
The COCA expert reference (per-vessel and total Agatston from Stanford's manual
calcium annotations) is **part of the Stanford AIMI release, not our output**, so
it is not redistributed here -- see `data/README.md`. Our own scores ship in
`results_expected/coca_cohort_manifest.csv`; you supply the reference from your
own COCA download and this script joins the two.

Usage
-----
    python analysis/coca_vs_reference.py --reference /path/to/coca_reference.csv

`--reference` must be a CSV with at least these two columns:

    patient_id   COCA case id as distributed by AIMI, e.g. "1A", "100A"
    gt_total     total Agatston from the case's expert annotation

Build it from the annotation files in your COCA download; summing the per-vessel
expert scores (LCA/LAD/LCX/RCA) per case reproduces `gt_total`.
"""
from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

import numpy as np

SCORES = Path(__file__).resolve().parents[1] / "results_expected" / "coca_cohort_manifest.csv"


def load_scores() -> dict[str, float]:
    if not SCORES.exists():
        sys.exit(f"FAIL: {SCORES.name} not found; run scripts/build_cohort_manifests.py")
    out = {}
    with SCORES.open(newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            try:
                out[row["patient_id"].strip()] = float(row["agatston_score"])
            except (ValueError, KeyError):
                continue
    return out


def load_reference(path: Path) -> dict[str, float]:
    if not path.exists():
        sys.exit(f"FAIL: reference file not found: {path}")
    out = {}
    with path.open(newline="", encoding="utf-8-sig") as fh:
        reader = csv.DictReader(fh)
        for col in ("patient_id", "gt_total"):
            if col not in (reader.fieldnames or []):
                sys.exit(f"FAIL: reference file has no {col!r} column "
                         f"(found: {reader.fieldnames})")
        for row in reader:
            try:
                out[row["patient_id"].strip()] = float(row["gt_total"])
            except (TypeError, ValueError):
                continue
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--reference", required=True, type=Path,
                    help="CSV with patient_id + gt_total, built from your own COCA download")
    a = ap.parse_args()

    scores, reference = load_scores(), load_reference(a.reference)
    shared = sorted(set(scores) & set(reference))
    if not shared:
        sys.exit("FAIL: no overlapping patient_id between our scores and your reference file. "
                 "COCA case ids look like '1A', '100A' -- check the id column format.")

    ai = np.array([scores[p] for p in shared])
    gt = np.array([reference[p] for p in shared])
    r = float(np.corrcoef(ai, gt)[0, 1])

    print(f"n matched (AI + reference): {len(shared)}   (manuscript reports 206)")
    print(f"Pearson r (AI vs expert)  : {r:.3f}   (manuscript reports 0.957)")
    print(f"zero-CAC by AI            : {int((ai == 0).sum())}/{len(ai)} = {100*(ai==0).mean():.1f}%")
    print(f"zero-CAC by reference     : {int((gt == 0).sum())}/{len(gt)} = {100*(gt==0).mean():.1f}%")
    if len(shared) != 206:
        print(f"\nNote: matched {len(shared)} of the 206 cases the manuscript reports; "
              f"the printed r is over the matched subset only.")


if __name__ == "__main__":
    main()
