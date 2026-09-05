"""Reproduce the C5 paired thin-vs-thick results (manuscript §3.6, Figures 4 & 5).

Reads results_expected/nlst_v252_paired.csv (checked-in, patient-level, de-identified)
and reproduces:
  - n paired patients
  - Pearson r (thin vs thick Agatston)
  - aggregate thick-to-thin ratio  Sum(thick)/Sum(thin)
  - Bland-Altman mean difference (thin - thick) and 95% limits of agreement
  - risk-category agreement + Cohen kappa (thin_risk vs thick_risk)
  - RESCUE count and rate (thick CAC = 0 with non-zero thin CAC)

Every quantity printed below is asserted against the value the manuscript prints,
so this script fails rather than reporting a number that disagrees with the paper.
An expected value written only in a docstring is not a check: this one said
`ratio=0.934` while the manuscript said 0.929, and nothing noticed.
"""
from __future__ import annotations

import csv
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from risk_categories import classify_cac_risk, RISK_ORDER  # noqa: E402

CSV = ROOT / "results_expected" / "nlst_v252_paired.csv"


def cohen_kappa(a, b, labels):
    idx = {l: i for i, l in enumerate(labels)}
    k = len(labels)
    m = np.zeros((k, k))
    for x, y in zip(a, b):
        m[idx[x], idx[y]] += 1
    n = m.sum()
    po = np.trace(m) / n
    pe = (m.sum(0) * m.sum(1)).sum() / (n * n)
    return (po - pe) / (1 - pe), po


def main():
    thin, thick, thin_r, thick_r, rescue = [], [], [], [], []
    for r in csv.DictReader(open(CSV)):
        try:
            a = float(r["thin_agatston"]); b = float(r["thick_agatston"])
        except (ValueError, KeyError):
            continue
        thin.append(a); thick.append(b)
        # 4-category risk derived from the Agatston score (None/Mild/Moderate/Severe)
        thin_r.append(classify_cac_risk(a)); thick_r.append(classify_cac_risk(b))
        rescue.append(r["rescue_phenomenon"].strip().lower() == "yes")
    thin, thick = np.array(thin), np.array(thick)

    r = float(np.corrcoef(thin, thick)[0, 1])
    # Aggregate thick-to-thin ratio over ALL paired patients, which is what the
    # manuscript reports: "aggregate Sum(thick)/Sum(thin) over all 2,224 paired
    # patients" (§3.6, Figure 4a annotation).
    #
    # 2026-09-05: this restricted the sum to patients non-zero on BOTH
    # reconstructions and therefore printed 0.934 -- the value an upstream audit
    # identified as an inadvertent denominator switch and retired on 2026-07-12,
    # after pinning the method by reproducing the original 0.927 on the original
    # v2.3.x data as an all-pairs figure. Anyone running this package got 0.934
    # against a paper that prints 0.929. Excluding the zero-score patients is
    # also the wrong estimator here: thick-slice zeros with non-zero thin scores
    # are the RESCUE phenomenon the paper is about, so dropping them removes
    # exactly the cases that make the ratio informative.
    ratio = float(thick.sum() / thin.sum())
    diff = thin - thick
    md, sd = float(diff.mean()), float(diff.std(ddof=1))
    kappa, agree = cohen_kappa(thick_r, thin_r, RISK_ORDER)
    n_rescue = int(sum(rescue))

    print(f"n paired patients        : {len(thin)}")
    print(f"Pearson r                : {r:.3f}")
    print(f"aggregate thick/thin     : {ratio:.3f}")
    print(f"Bland-Altman mean diff   : {md:.1f}  (95% LoA {md-1.96*sd:.1f} .. {md+1.96*sd:.1f})")
    print(f"risk-category agreement  : {100*agree:.1f}%")
    print(f"Cohen kappa              : {kappa:.3f}")
    print(f"RESCUE (thick=0, thin>0) : {n_rescue}/{len(thin)} = {100*n_rescue/len(thin):.2f}%")

    # --- The paper's printed values. Reproducing them is the point of this file.
    # Manuscript sources: §3.6 (all of these), Table 1 (n), Figure 4a annotation
    # (r, ratio), Figure 4b (Bland-Altman), Figure 5 / Supplementary Table 7
    # (agreement, kappa, RESCUE).
    expected = [
        ("n paired patients", len(thin), 2224, 0),
        ("Pearson r", r, 0.974, 5e-4),
        ("aggregate thick/thin", ratio, 0.929, 5e-4),
        ("Bland-Altman mean difference", md, 22.8, 0.05),
        ("Bland-Altman lower LoA", md - 1.96 * sd, -212.9, 0.05),
        ("Bland-Altman upper LoA", md + 1.96 * sd, 258.6, 0.05),
        ("risk-category agreement (%)", 100 * agree, 72.8, 0.05),
        ("Cohen kappa", kappa, 0.639, 5e-4),
        ("RESCUE count", n_rescue, 327, 0),
    ]
    bad = [(name, got, want) for name, got, want, tol in expected if abs(got - want) > tol]
    # The reclassification matrix, cell by cell, is what makes the risk-category
    # boundary checkable rather than merely stated (manuscript Supplementary
    # Table 7 / Figure 5a; rows = thick, columns = thin, both in RISK_ORDER).
    idx = {c: i for i, c in enumerate(RISK_ORDER)}
    matrix = [[0] * 4 for _ in range(4)]
    for tk, tn in zip(thick_r, thin_r):
        matrix[idx[tk]][idx[tn]] += 1
    matrix_expected = [[320, 323, 4, 0], [11, 426, 148, 3], [0, 20, 380, 83], [0, 0, 12, 494]]
    if matrix != matrix_expected:
        bad.append(("reclassification matrix", matrix, matrix_expected))
    if bad:
        print("\nFAILED — these do not match the published manuscript:")
        for name, got, want in bad:
            print(f"  {name}: got {got}, manuscript reports {want}")
        raise SystemExit(1)
    print("\nAll values match the published manuscript.")


if __name__ == "__main__":
    main()
