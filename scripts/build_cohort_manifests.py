#!/usr/bin/env python3
"""Build the per-acquisition cohort manifests shipped in results_expected/.

Requires the private source tables in `ai-cac-research`, so this is a maintainer
script and CI cannot run it. What CI runs instead is
`scripts/verify_cohort_manifest.py`, which checks the shipped artefact using
nothing but this repository.

Why a manifest at all
---------------------
A results table keyed by NLST `patient_id` says what we scored, not which
acquisition we scored. That is enough within this cohort (2,231 thin scans map
1:1 onto 2,231 distinct SeriesInstanceUIDs), but NLST is a three-round annual
screening trial, so a reader holding only a participant ID cannot tell which
screening round or which reconstruction produced our numbers.
The manifest adds `selected_series_uid` and the acquisition parameters, which is
what makes the subset re-downloadable from TCIA / NCI Imaging Data Commons.

What is deliberately NOT published
----------------------------------
* `data_source_path` / `inference_path` -- local filesystem paths.
* `patient_age` / `patient_sex` -- empty for NLST (TCIA strips them) and not
  needed to reproduce anything.
* Anything COCA-derived at all. The Stanford University School of Medicine COCA
  Research Use Agreement grants only "personal, non-commercial research" use and
  states: "YOU MAY NOT DISTRIBUTE, PUBLISH, OR REPRODUCE A COPY of any portion or
  all of the ... Dataset to others without specific prior written permission from
  the School of Medicine." It carries no research or reproducibility exception,
  and the dataset page describes the non-gated release as "chest CT DICOM images
  *with coronary artery calcium scores*" -- so the expert scores are the Dataset,
  not a derivative of it. Case identifiers and per-case DICOM header values are
  arguably "a portion" too. COCA therefore contributes nothing to this repository;
  see data/README.md for how §3.1 is reproduced instead.

This script runs against the private source tree (`ai-cac-research`); the CSVs it
writes are the checked-in artefacts. Counts are asserted against the manuscript,
so a source-data change that would silently alter a published denominator fails
the build instead.
"""
from __future__ import annotations

import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from risk_categories import RISK_ORDER, classify_cac_risk  # noqa: E402

REPO = Path(__file__).resolve().parents[1]
OUT = REPO / "results_expected"
SRC = Path.home() / "projects" / "ai-cac-research" / "results"

NLST_SOURCES = [
    ("thin", SRC / "v252_nlst_full_20260621" / "NLST_thin_results.csv"),
    ("thin", SRC / "v252_nlst_full_20260621" / "NLST_batch3_thin_results.csv"),
    # The thick-slice sources are deliberately not read: see RECONSTRUCTIONS below.
]
# The v2.5.2 external re-baseline is the run the manuscript reports (§3.1);
# it carries the acquisition metadata the GT-joined table dropped.
# (No COCA source: nothing COCA-derived is published here -- see the module
    #  docstring and data/README.md.)

FIELDS = [
    "patient_id", "cohort", "reconstruction", "selected_series_uid", "study_date",
    "manufacturer", "convolution_kernel", "nominal_thickness_mm", "actual_spacing_mm",
    "num_slices", "agatston_score", "risk_category",
    "algorithm_version", "model_weights_md5",
]

# Manuscript denominators (Table 1 / §2.3 / §3.1). A mismatch means the source
# data moved under us -- fail rather than publish a manifest that disagrees with
# the paper.
# The CMPB manuscript's cohort is 2,231 NLST thin-slice acquisitions plus 206
# COCA (Table 1); the paired thick-slice arm belonged to the former §3.6, which
# the CMPB restructure removed. Emitting it here would ship a manifest broader
# than the paper it accompanies -- the same drift that left Figures 4-5 in the
# package after the section they illustrated was cut.
RECONSTRUCTIONS = ("thin",)
EXPECTED = {"nlst_thin": 2231}


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
                # Derived here, not copied. The upstream scoring CSV carries a
                # FIVE-category label (None / Minimal <=10 / Mild <=100 / Moderate
                # <=400 / Severe) from the production batch driver, which is a
                # different scheme from the four categories the manuscript reports
                # and uses different boundaries. Copying it verbatim, as this line
                # did until 2026-09-05, published a column that no analysis in this
                # package produces and that the paper never defines. Deriving it
                # from the same function the analysis and figure scripts use means
                # the manifest cannot disagree with them.
                "risk_category": (
                    classify_cac_risk(float(r["agatston_score"]))
                    if r.get("agatston_score", "").strip() not in ("", "None")
                    else ""
                ),
                "algorithm_version": r.get("algorithm_version", ""),
                "model_weights_md5": r.get("model_weights_md5", ""),
            }
    rows = sorted(by_uid.values(), key=lambda d: (d["reconstruction"], int(d["patient_id"])))
    for role in RECONSTRUCTIONS:
        n = sum(1 for d in rows if d["reconstruction"] == role)
        if n != EXPECTED[f"nlst_{role}"]:
            fail(f"NLST {role}: manifest has {n} acquisitions, "
                 f"manuscript reports {EXPECTED[f'nlst_{role}']}")
    stray = {d["reconstruction"] for d in rows} - set(RECONSTRUCTIONS)
    if stray:
        fail(f"manifest carries reconstructions the manuscript does not describe: {sorted(stray)}")
    # The published manifest may carry only the categories the manuscript defines.
    # Until 2026-09-05 it carried a fifth, `Minimal`, inherited from the upstream
    # scoring CSV -- a label the paper never mentions, on boundaries it does not use.
    emitted = {d["risk_category"] for d in rows if d["risk_category"]}
    if not emitted <= set(RISK_ORDER):
        fail(f"manifest carries risk categories the manuscript does not define: "
             f"{sorted(emitted - set(RISK_ORDER))}. The published categories are "
             f"{RISK_ORDER}; a fifth label means the column was copied from an upstream "
             f"file instead of derived with classify_cac_risk().")
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
    sys.stdout.flush()


def main() -> None:
    # Build first, announce afterwards. This printed "OK - wrote:" before doing
    # any work, so a run that failed on a missing source table still had "OK" in
    # its output -- and in CI, where stdout is block-buffered and the exit
    # message goes to stderr, the OK appeared *after* the FAIL.
    write(OUT / "nlst_cohort_manifest.csv", build_nlst())
    print("OK - manifest written and verified against the manuscript.")


if __name__ == "__main__":
    main()
