"""Reproduce the COCA non-gated vs expert-reference correlation (manuscript §3.1).

Expected: n = 206, Pearson r ~ 0.957, zero-CAC 52.4% (AI) vs 42.7% (reference).

Why this script ships no COCA data
----------------------------------
The Stanford University School of Medicine COCA Research Use Agreement grants
"personal, non-commercial research" use only and states:

    YOU MAY NOT DISTRIBUTE, PUBLISH, OR REPRODUCE A COPY of any portion or all of
    the COCA- Coronary Calcium and chest CT's Dataset to others without specific
    prior written permission from the School of Medicine.

There is no research or reproducibility exception, and the dataset page describes
the non-gated release as "chest CT DICOM images *with coronary artery calcium
scores*" -- so the expert scores are part of the Dataset rather than a derivative
of it. Case identifiers and per-case header values are arguably "a portion" as
well. This repository therefore publishes nothing COCA-derived: no case list, no
reference values, no scores of ours.

Reproducing §3.1 end to end costs nothing extra, because this repository ships the
scoring engine itself:

    1. Register for COCA and download the non-gated release from Stanford AIMI.
    2. Score it with the CAC Plus engine (v2.5.2, the version pinned in the
       manuscript) to obtain one Agatston score per case.
    3. Build the expert reference from the annotations in your own download: one
       row per case, `gt_total` = the sum of the per-vessel expert scores.
    4. Run this script over your two files.

Usage
-----
    python analysis/coca_vs_reference.py \\
        --scores    /path/to/your_cac_plus_scores.csv \\
        --reference /path/to/your_coca_reference.csv

Both CSVs need a `patient_id` column holding the COCA case id ("1A", "100A", ...).
`--scores` needs `agatston_score`; `--reference` needs `gt_total`.
"""
from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

import numpy as np

EXPECTED_N = 206
EXPECTED_R = 0.957
EXPECTED_ZERO_AI = 52.4
EXPECTED_ZERO_REF = 42.7


def load(path: Path, value_col: str) -> dict[str, float]:
    if not path.exists():
        sys.exit(f"FAIL: file not found: {path}")
    out: dict[str, float] = {}
    with path.open(newline="", encoding="utf-8-sig") as fh:
        reader = csv.DictReader(fh)
        for col in ("patient_id", value_col):
            if col not in (reader.fieldnames or []):
                sys.exit(f"FAIL: {path.name} has no {col!r} column (found: {reader.fieldnames})")
        for row in reader:
            try:
                out[row["patient_id"].strip()] = float(row[value_col])
            except (TypeError, ValueError):
                continue
    if not out:
        sys.exit(f"FAIL: {path.name} yielded no usable rows")
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--scores", required=True, type=Path,
                    help="your CAC Plus scores: patient_id + agatston_score")
    ap.add_argument("--reference", required=True, type=Path,
                    help="your COCA expert reference: patient_id + gt_total")
    a = ap.parse_args()

    scores = load(a.scores, "agatston_score")
    reference = load(a.reference, "gt_total")
    shared = sorted(set(scores) & set(reference))
    if not shared:
        sys.exit("FAIL: no overlapping patient_id between the two files. COCA case ids "
                 "look like '1A', '100A' -- check the id column format.")

    ai = np.array([scores[p] for p in shared])
    gt = np.array([reference[p] for p in shared])
    r = float(np.corrcoef(ai, gt)[0, 1])
    zero_ai = 100 * float((ai == 0).mean())
    zero_gt = 100 * float((gt == 0).mean())

    print(f"n matched                 : {len(shared):>6}      (manuscript: {EXPECTED_N})")
    print(f"Pearson r (AI vs expert)  : {r:>6.3f}      (manuscript: {EXPECTED_R})")
    print(f"zero-CAC by AI            : {zero_ai:>5.1f}%      (manuscript: {EXPECTED_ZERO_AI}%)")
    print(f"zero-CAC by reference     : {zero_gt:>5.1f}%      (manuscript: {EXPECTED_ZERO_REF}%)")
    if len(shared) != EXPECTED_N:
        print(f"\nNote: matched {len(shared)} of {EXPECTED_N} cases; the figures above are over "
              f"the matched subset only.")


if __name__ == "__main__":
    main()
