"""Regenerate the data figures from the checked-in paired NLST table.

Reproduces Figure 4 (thin-vs-thick scatter + Bland-Altman) and Figure 5 (RESCUE
risk-reclassification heatmap + per-stratum RESCUE-rate bars) of the manuscript from
results_expected/nlst_v252_paired.csv. Output PNGs are written next to this script.
"""
from __future__ import annotations

import csv
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from risk_categories import classify_cac_risk, RISK_ORDER  # noqa: E402

CSV = ROOT / "results_expected" / "nlst_v252_paired.csv"
OUT = Path(__file__).resolve().parent


def load():
    thin, thick = [], []
    for r in csv.DictReader(open(CSV)):
        try:
            thin.append(float(r["thin_agatston"])); thick.append(float(r["thick_agatston"]))
        except (ValueError, KeyError):
            continue
    return np.array(thin), np.array(thick)


def figure_4(thin, thick):
    r = np.corrcoef(thin, thick)[0, 1]
    fig, ax = plt.subplots(1, 2, figsize=(13, 5.2))
    lim = max(thin.max(), thick.max())
    ax[0].scatter(thin, thick, s=14, alpha=0.4, edgecolors="none", color="#4a7fb5")
    ax[0].plot([0, lim], [0, lim], "k--", lw=0.8, label="Line of identity")
    b, a = np.polyfit(thin, thick, 1)
    ax[0].plot([0, lim], [a, a + b * lim], "r-", lw=1.2, label=f"Best fit: y={b:.3f}x{a:+.1f}")
    ax[0].set_xlabel("Thin-slice Agatston (~2 mm)"); ax[0].set_ylabel("Thick-slice Agatston (~5 mm)")
    ax[0].set_title("(a)", loc="left", fontweight="bold"); ax[0].legend(loc="upper left", fontsize=8)
    both = (thin > 0) & (thick > 0)
    ax[0].text(0.97, 0.05, f"Pearson r = {r:.3f}\nAggregate thick/thin = {thick[both].sum()/thin[both].sum():.3f}",
               transform=ax[0].transAxes, ha="right",
               bbox=dict(boxstyle="round,pad=0.3", facecolor="white", edgecolor="gray"), fontsize=9)

    mean = (thin + thick) / 2; diff = thin - thick
    md, sd = diff.mean(), diff.std(ddof=1)
    ax[1].scatter(mean, diff, s=14, alpha=0.4, edgecolors="none", color="#4a7fb5")
    ax[1].axhline(md, color="red", lw=1.2, label=f"Mean diff: {md:.1f}")
    ax[1].axhline(md + 1.96 * sd, color="red", ls="--", lw=1.0, label=f"+1.96 SD: {md+1.96*sd:.1f}")
    ax[1].axhline(md - 1.96 * sd, color="red", ls="--", lw=1.0, label=f"-1.96 SD: {md-1.96*sd:.1f}")
    ax[1].set_xlabel("Mean of thin and thick Agatston"); ax[1].set_ylabel("Thin - Thick Agatston")
    ax[1].set_title("(b)", loc="left", fontweight="bold"); ax[1].legend(loc="upper right", fontsize=8)
    fig.tight_layout(); fig.savefig(OUT / "figure_4_c5_thin_vs_thick.png", dpi=200); plt.close(fig)
    print("  saved figure_4_c5_thin_vs_thick.png")


def figure_5(thin, thick):
    tr = [classify_cac_risk(v) for v in thin]; kr = [classify_cac_risk(v) for v in thick]
    idx = {l: i for i, l in enumerate(RISK_ORDER)}
    mat = np.zeros((4, 4), int)
    for a, b in zip(kr, tr):  # rows = thick, cols = thin
        mat[idx[a], idx[b]] += 1
    fig, ax = plt.subplots(1, 2, figsize=(13, 5.2))
    im = ax[0].imshow(mat, cmap="Blues")
    for i in range(4):
        for j in range(4):
            ax[0].text(j, i, str(mat[i, j]), ha="center", va="center",
                       fontweight="bold" if i == j else "normal",
                       color="white" if mat[i, j] > mat.max() * 0.5 else "black")
    ax[0].set_xticks(range(4)); ax[0].set_xticklabels(RISK_ORDER)
    ax[0].set_yticks(range(4)); ax[0].set_yticklabels(RISK_ORDER)
    ax[0].set_xlabel("Thin-slice (~2 mm) risk category"); ax[0].set_ylabel("Thick-slice (~5 mm) risk category")
    ax[0].set_title("(a)", loc="left", fontweight="bold"); fig.colorbar(im, ax=ax[0], shrink=0.8)

    rates, labels = [], []
    for cat in RISK_ORDER:
        den = sum(1 for v in thin if classify_cac_risk(v) == cat)
        num = sum(1 for t, k in zip(thin, thick) if classify_cac_risk(t) == cat and t > 0 and k == 0)
        rates.append(100 * num / den if den else 0); labels.append(f"{num}/{den}")
    bars = ax[1].bar(RISK_ORDER, rates, color=["#bbbbbb", "#ff8c1a", "#ff8c1a", "#ff8c1a"])
    for bar, lab in zip(bars, labels):
        ax[1].text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.5, lab, ha="center", fontsize=9)
    ax[1].set_ylabel("RESCUE rate (%)"); ax[1].set_xlabel("Thin-slice (~2 mm) risk category")
    ax[1].set_title("(b)", loc="left", fontweight="bold")
    fig.tight_layout(); fig.savefig(OUT / "figure_5_rescue_phenomenon.png", dpi=200); plt.close(fig)
    print("  saved figure_5_rescue_phenomenon.png")


if __name__ == "__main__":
    thin, thick = load()
    figure_4(thin, thick)
    figure_5(thin, thick)
