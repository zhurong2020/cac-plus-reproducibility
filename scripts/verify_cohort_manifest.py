#!/usr/bin/env python3
"""Verify the shipped cohort manifest using nothing but this repository.

`build_cohort_manifests.py` needs the private source tables in `ai-cac-research`
and is a maintainer script; CI cannot run it, and on 2026-09-18 CI tried to and
failed, which is why this exists. A reader cloning this repository is in the same
position as CI: they can check the artefact, not rebuild it.

Checks, all against the manuscript or against this repository's own rules:
  * the published denominator (§2.3 / Table 1): 2,231 NLST thin-slice acquisitions;
  * one row per SeriesInstanceUID, which is what makes the subset re-downloadable;
  * no reconstruction the manuscript does not describe (the paired thick-slice arm
    belonged to the former §3.6 and was removed with it);
  * risk categories confined to the four strata §2.4 defines;
  * no local filesystem path, and no patient identifier beyond the NLST
    participant id that NLST's own terms permit publishing.
"""
from __future__ import annotations

import csv
import pathlib
import re
import sys

REPO = pathlib.Path(__file__).resolve().parents[1]
MANIFEST = REPO / "results_expected" / "nlst_cohort_manifest.csv"

EXPECTED_ROWS = 2231
ALLOWED_RECONSTRUCTIONS = {"thin"}
ALLOWED_RISK = {"None", "Mild", "Moderate", "Severe", ""}
LEAK_MARKERS = ("/mnt/", "/home/", "/Users/", "C:\\", "OneDrive")


def main() -> int:
    if not MANIFEST.exists():
        print(f"FAIL: {MANIFEST.relative_to(REPO)} is missing.", file=sys.stderr)
        return 1

    blob = MANIFEST.read_text(encoding="utf-8")
    rows = list(csv.DictReader(MANIFEST.open(encoding="utf-8")))
    problems: list[str] = []

    if len(rows) != EXPECTED_ROWS:
        problems.append(f"{len(rows)} rows, manuscript reports {EXPECTED_ROWS}")

    recons = {r["reconstruction"] for r in rows}
    if not recons <= ALLOWED_RECONSTRUCTIONS:
        problems.append(f"reconstructions the manuscript does not describe: "
                        f"{sorted(recons - ALLOWED_RECONSTRUCTIONS)}")

    uids = [r["selected_series_uid"] for r in rows]
    if "" in uids:
        problems.append(f"{uids.count('')} rows carry no SeriesInstanceUID")
    if len(set(uids)) != len(uids):
        problems.append(f"{len(uids) - len(set(uids))} duplicate SeriesInstanceUIDs")

    risks = {r["risk_category"] for r in rows}
    if not risks <= ALLOWED_RISK:
        problems.append(f"risk categories outside §2.4: {sorted(risks - ALLOWED_RISK)}")

    for marker in LEAK_MARKERS:
        if marker in blob:
            problems.append(f"leaks a local filesystem path ({marker!r})")

    if re.search(r"dicom_[0-9]{6,}", blob):
        problems.append("carries an internal hospital case identifier")

    if problems:
        print("FAIL:", file=sys.stderr)
        for p in problems:
            print(f"  {p}", file=sys.stderr)
        return 1

    print(f"OK - {len(rows)} NLST thin-slice acquisitions, "
          f"{len(set(uids))} distinct SeriesInstanceUIDs, "
          f"risk categories within §2.4, no path or identifier leak.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
