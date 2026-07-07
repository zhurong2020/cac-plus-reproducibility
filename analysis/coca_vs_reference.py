"""Reproduce the COCA non-gated vs expert-reference correlation (manuscript §3.1).

Reads results_expected/coca_nongated_vs_reference.csv and reproduces the Pearson
correlation between the CAC Plus AI Agatston score and the COCA expert reference
(gt_total), plus the zero-CAC rates. Expected: r ~ 0.957.
"""
from __future__ import annotations

import csv
from pathlib import Path

import numpy as np

CSV = Path(__file__).resolve().parents[1] / "results_expected" / "coca_nongated_vs_reference.csv"


def main():
    ai, gt = [], []
    for row in csv.DictReader(open(CSV)):
        try:
            a = float(row["ai_agatston_v252"]); g = float(row["gt_total"])
        except (ValueError, KeyError):
            continue
        ai.append(a); gt.append(g)
    ai, gt = np.array(ai), np.array(gt)

    r = float(np.corrcoef(ai, gt)[0, 1])
    print(f"n scored (AI + reference): {len(ai)}")
    print(f"Pearson r (AI vs expert) : {r:.3f}")
    print(f"zero-CAC by AI           : {int((ai == 0).sum())}/{len(ai)} = {100*(ai==0).mean():.1f}%")
    print(f"zero-CAC by reference    : {int((gt == 0).sum())}/{len(gt)} = {100*(gt==0).mean():.1f}%")


if __name__ == "__main__":
    main()
