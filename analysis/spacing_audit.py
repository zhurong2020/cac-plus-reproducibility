#!/usr/bin/env python3
"""C5: the ImagePositionPatient axial-spacing audit (manuscript §3.6).

Recomputes, from the shipped NLST manifest, the count of overlap-reconstruction
acquisitions whose DICOM `SliceThickness` tag disagrees with the spacing actually
measured from `ImagePositionPatient[2]` differences. Applying the vendor formula
to these inflates the Agatston multiplier in proportion to the ratio, because the
Agatston score scales linearly with axial voxel volume.

Why the manuscript says "exactly 2.0"
-------------------------------------
This script is what found the one inaccuracy the published text had. The paper's
274 is the count at ratio *exactly* 2.0. Allow a tolerance and it becomes 280:
six further Siemens acquisitions measure 0.9967-1.0031 mm instead of 1.0, so
their ratio is 1.994-2.007 -- the same 50%-overlap protocol with sub-millimetre
jitter in the reported slice positions. The paper's count was right; the sentence
that followed it ("the remaining acquisitions have ratio approximately 1.0 and
the fix is a no-op") was not, and was corrected on 2026-09-18.

The fix itself never depended on the bucket: it uses each acquisition's measured
spacing. Only the description did.

Asserts both counts, so this script fails rather than reporting a number that
disagrees with the paper.
"""
from __future__ import annotations

import collections
import csv
import pathlib
import sys

MANIFEST = pathlib.Path(__file__).resolve().parents[1] / "results_expected" / "nlst_cohort_manifest.csv"

EXPECT_EXACT = 274          # §3.6: 266 Siemens + 8 GE Medical Systems
EXPECT_EXACT_BY_VENDOR = {"SIEMENS": 266, "GE MEDICAL SYSTEMS": 8}
EXPECT_NEAR = 280           # within 0.4% of 2.0
TOLERANCE = 0.004


def main() -> int:
    rows = [r for r in csv.DictReader(MANIFEST.open()) if r["reconstruction"] == "thin"]
    print(f"NLST thin-slice acquisitions in the manifest: {len(rows)}")

    exact, near = [], []
    for r in rows:
        try:
            ratio = float(r["nominal_thickness_mm"]) / float(r["actual_spacing_mm"])
        except (ValueError, ZeroDivisionError, KeyError):
            continue
        if ratio == 2.0:
            exact.append(r)
        if abs(ratio - 2.0) <= 2.0 * TOLERANCE:
            near.append(r)

    by_vendor = collections.Counter(r["manufacturer"] for r in exact)
    print(f"\nratio exactly 2.0 : {len(exact)}")
    for vendor, n in sorted(by_vendor.items()):
        print(f"    {vendor}: {n}")
    print(f"ratio within {100 * TOLERANCE:.1f}% of 2.0 : {len(near)}"
          f"   (+{len(near) - len(exact)} with sub-millimetre position jitter)")
    print(f"no-op (ratio ~ 1.0) : {len(rows) - len(near)}")

    fails = []
    if len(exact) != EXPECT_EXACT:
        fails.append(f"exact-2.0 count {len(exact)} != published {EXPECT_EXACT}")
    if dict(by_vendor) != EXPECT_EXACT_BY_VENDOR:
        fails.append(f"vendor split {dict(by_vendor)} != published {EXPECT_EXACT_BY_VENDOR}")
    if len(near) != EXPECT_NEAR:
        fails.append(f"near-2.0 count {len(near)} != {EXPECT_NEAR}")
    if fails:
        print("\nFAIL:")
        for f in fails:
            print(f"  {f}")
        return 1

    print("\nPASS: every count matches the published values.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
