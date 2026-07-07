"""CAC risk-category thresholds used throughout the CAC Plus paper.

Four-category scheme (per the 2024 SCCT consensus, as reported in the manuscript
figure legends and Results): None / Mild / Moderate / Severe.
"""
from __future__ import annotations


def classify_cac_risk(agatston: float) -> str:
    """Map an Agatston score to its risk category.

    None      : Agatston == 0
    Mild      : 1   - 99
    Moderate  : 100 - 399
    Severe    : >= 400
    """
    if agatston <= 0:
        return "None"
    if agatston < 100:
        return "Mild"
    if agatston < 400:
        return "Moderate"
    return "Severe"


RISK_ORDER = ["None", "Mild", "Moderate", "Severe"]
