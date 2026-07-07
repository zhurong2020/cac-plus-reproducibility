"""Reproduce the C5 paired thin-vs-thick results (manuscript §3.6, Figures 4 & 5).

Reads results_expected/nlst_v252_paired.csv (checked-in, patient-level, de-identified)
and reproduces:
  - n paired patients
  - Pearson r (thin vs thick Agatston)
  - aggregate thick-to-thin ratio  Sum(thick)/Sum(thin)
  - Bland-Altman mean difference (thin - thick) and 95% limits of agreement
  - risk-category agreement + Cohen kappa (thin_risk vs thick_risk)
  - RESCUE count and rate (thick CAC = 0 with non-zero thin CAC)

Expected (v2.5.2): n=2224, r=0.974, ratio=0.934, kappa=0.639, RESCUE 327/2224 (14.70%).
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
    # aggregate thick-to-thin ratio over patients with non-zero scores on BOTH
    # reconstructions (manuscript §3.6 / Figure 4 convention)
    both = (thin > 0) & (thick > 0)
    ratio = float(thick[both].sum() / thin[both].sum())
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


if __name__ == "__main__":
    main()
