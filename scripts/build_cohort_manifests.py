#!/usr/bin/env python3
"""Build the per-acquisition cohort manifests shipped in results_expected/.

Why a manifest at all
---------------------
`nlst_v252_paired.csv` is a *results* table: it is keyed by NLST `patient_id` and
says what we scored, not which acquisition we scored. That is enough within this
cohort (2,231 thin scans map 1:1 onto 2,231 distinct SeriesInstanceUIDs), but NLST
is a three-round annual screening trial, so a reader holding only a participant ID
cannot tell which screening round or which reconstruction produced our numbers.
The manifest adds `selected_series_uid` and the acquisition parameters, which is
what makes the subset re-downloadable from TCIA / NCI Imaging Data Commons.

What is deliberately NOT published
----------------------------------
* `data_source_path` / `inference_path` -- local filesystem paths.
* `patient_age` / `patient_sex` -- empty for NLST (TCIA strips them) and not
  needed to reproduce anything.
* COCA's expert reference (`gt_total` and the per-vessel `gt_*` columns) -- that
  is Stanford's annotation data, not our derived output. See data/README.md.

This script runs against the private source tree (`ai-cac-research`); the CSVs it
writes are the checked-in artefacts. Counts are asserted against the manuscript,
so a source-data change that would silently alter a published denominator fails
the build instead.
"""
from __future__ import annotations

import csv
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
OUT = REPO / "results_expected"
SRC = Path.home() / "projects" / "ai-cac-research" / "results"

NLST_SOURCES = [
    ("thin", SRC / "v252_nlst_full_20260621" / "NLST_thin_results.csv"),
    ("thin", SRC / "v252_nlst_full_20260621" / "NLST_batch3_thin_results.csv"),
    ("thick", SRC / "v252_nlst_full_20260621" / "NLST_thick_results.csv"),
    ("thick", SRC / "v252_nlst_full_20260621" / "NLST_batch3_thick_results.csv"),
]
# The v2.5.2 external re-baseline is the run the manuscript reports (§3.1);
# it carries the acquisition metadata the GT-joined table dropped.
COCA_SOURCE = SRC / "v252_external_rebaseline_20260706" / "external_v252_results.csv"

FIELDS = [
    "patient_id", "cohort", "reconstruction", "selected_series_uid", "study_date",
    "manufacturer", "convolution_kernel", "nominal_thickness_mm", "actual_spacing_mm",
    "num_slices", "agatston_score", "risk_category",
    "algorithm_version", "model_weights_md5",
]

# Manuscript denominators (Table 1 / §2.3 / §3.1). A mismatch means the source
# data moved under us -- fail rather than publish a manifest that disagrees with
# the paper.
EXPECTED = {"nlst_thin": 2231, "nlst_thick": 2224, "coca": 206}


def fail(msg: str) -> None:
    sys.exit(f"FAIL: {msg}")


def read(path: Path) -> list[dict]:
    if not path.exists():
        fail(f"source table not found: {path}")
    with path.open(newline="", encoding="utf-8-sig") as fh:
        return list(csv.DictReader(fh))


def build_nlst() -> list[dict]:
    """One row per scored acquisition, deduplicated on SeriesInstanceUID.

    The two thin tables overlap by 34 rows (batch 1-2 and batch 3 runs both
    emitted some cases): 2,265 raw rows dedupe to 2,231. Deduplicating on
    row count rather than on `selected_series_uid` would publish 34 phantom
    acquisitions.
    """
    by_uid: dict[tuple[str, str], dict] = {}
    for role, path in NLST_SOURCES:
        for r in read(path):
            if r.get("status") != "success":
                continue
            uid = (r.get("selected_series_uid") or "").strip()
            if not uid:
                fail(f"{path.name}: successful row for patient {r.get('patient_id')} has no series UID")
            key = (role, uid)
            if key in by_uid:
                continue  # batch-overlap duplicate
            by_uid[key] = {
                "patient_id": r["patient_id"],
                "cohort": "NLST",
                "reconstruction": role,
                "selected_series_uid": uid,
                "study_date": r.get("study_date", ""),
                "manufacturer": r.get("manufacturer", ""),
                "convolution_kernel": r.get("convolution_kernel", ""),
                "nominal_thickness_mm": r.get("input_thickness_mm", ""),
                "actual_spacing_mm": r.get("actual_spacing_mm", ""),
                "num_slices": r.get("num_slices_reported", ""),
                "agatston_score": r.get("agatston_score", ""),
                "risk_category": r.get("risk_category", ""),
                "algorithm_version": r.get("algorithm_version", ""),
                "model_weights_md5": r.get("model_weights_md5", ""),
            }
    rows = sorted(by_uid.values(), key=lambda d: (d["reconstruction"], int(d["patient_id"])))
    for role, key in (("thin", "nlst_thin"), ("thick", "nlst_thick")):
        n = sum(1 for d in rows if d["reconstruction"] == role)
        if n != EXPECTED[key]:
            fail(f"NLST {role}: manifest has {n} acquisitions, manuscript reports {EXPECTED[key]}")
    return rows


def build_coca() -> list[dict]:
    rows = []
    for r in read(COCA_SOURCE):
        if (r.get("cohort") or "").strip().lower() not in ("coca", "coca_nongated", "coca-nongated"):
            continue
        if r.get("status") != "success":
            continue          # the single Z-coverage-guard skip of 207 attempted
        pid = (r.get("patient_id") or "").strip()
        rows.append({
            "patient_id": pid,
            "cohort": "COCA-nongated",
            "reconstruction": "single",
            # COCA ships one prepared volume per case, so the AIMI case id is
            # the acquisition key; there is no series UID to give.
            "selected_series_uid": "",
            "study_date": "",
            "manufacturer": r.get("manufacturer", ""),
            "convolution_kernel": "",
            "nominal_thickness_mm": r.get("nominal_thickness_mm", ""),
            "actual_spacing_mm": r.get("input_spacing_z_mm", ""),
            "num_slices": r.get("num_slices", ""),
            "agatston_score": r.get("agatston_score", ""),
            "risk_category": r.get("risk_category", ""),
            "algorithm_version": r.get("algorithm_version", "2.5.2"),
            "model_weights_md5": r.get("model_weights_md5", ""),
        })
    rows.sort(key=lambda d: d["patient_id"])
    if len(rows) != EXPECTED["coca"]:
        fail(f"COCA: manifest has {len(rows)} rows, manuscript reports {EXPECTED['coca']} scored")
    for d in rows:
        for banned in ("gt_total", "gt_LCA", "gt_LAD", "gt_LCX", "gt_RCA"):
            if banned in d:
                fail(f"COCA manifest must not carry Stanford's expert annotation column {banned!r}")
    return rows


def write(path: Path, rows: list[dict]) -> None:
    with path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=FIELDS, lineterminator="\n")
        w.writeheader()
        w.writerows(rows)
    blob = path.read_text(encoding="utf-8")
    for leak in ("/mnt/", "/home/", "C:\\", "OneDrive"):
        if leak in blob:
            fail(f"{path.name} leaks a local filesystem path ({leak!r})")
    print(f"  {path.name}: {len(rows)} rows")


def main() -> None:
    print("OK - wrote:")
    write(OUT / "nlst_cohort_manifest.csv", build_nlst())
    write(OUT / "coca_cohort_manifest.csv", build_coca())


if __name__ == "__main__":
    main()
