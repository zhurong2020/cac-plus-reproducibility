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
the fix is a no-op") was not.

That sentence was corrected once, for those six, and the correction was
incomplete: 50 GE acquisitions sit at ratio 1.15-1.50 and five more are outliers
(three where the measured spacing exceeds the nominal thickness, one at 1.11, one
at 2.51), and five Siemens sit 0.6% off 1.0. On all 60 the fix changes the
multiplier, so calling them no-ops was wrong by 60 acquisitions, not six. This script printed the same wrong bucket --
"no-op (ratio ~ 1.0)" for everything outside the 2.0 band -- while its own
docstring claimed the correction had been made. Both were fixed 2026-09-18 and
the full decomposition is now asserted, so the two cannot drift apart again.

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
# The manuscript says the 274 are "all in NLST batch 3" and that the 50 at ratio
# 1.25 split 48 / 2. Neither was checkable from the shipped manifest until a
# reviewer pointed out it carried no batch column (2026-09-19). It does now, and
# these assert what the paper claims.
EXPECT_EXACT_BATCH = {"NLST_b3": 274}          # exactly 2.0: entirely batch 3
EXPECT_NEAR_BATCH = {"NLST_b3": 278, "NLST_b12": 2}  # within 0.4%: two jitter cases are not
EXPECT_MID_BATCH = {"NLST_b3": 48, "NLST_b12": 2}
EXPECT_NEAR = 280           # within 0.4% of 2.0
# The rest of the cohort, which the paper used to call a no-op wholesale.
EXPECT_MID = 50             # GE, ratio 1.15-1.50
EXPECT_NEAR_ONE = 5         # Siemens, ratio 1.0055-1.0064 (position jitter)
EXPECT_OUTLIER = 5          # 3 with spacing > nominal, 1 at 1.11, 1 at 2.51
EXPECT_NOOP = 1891          # ratio exactly 1.0 -- byte-identical to the vendor
TOLERANCE = 0.004


def main() -> int:
    rows = [r for r in csv.DictReader(MANIFEST.open()) if r["reconstruction"] == "thin"]
    print(f"NLST thin-slice acquisitions in the manifest: {len(rows)}")

    # `near` contains `exact`; the other four buckets are disjoint from it and
    # from each other, so the five partition the cohort and the sum is asserted.
    exact, near, mid, near_one, exact_one, outlier, unparsed = [], [], [], [], [], [], []
    for r in rows:
        try:
            ratio = float(r["nominal_thickness_mm"]) / float(r["actual_spacing_mm"])
        except (ValueError, ZeroDivisionError, KeyError):
            # Dropping these silently would let the partition check pass on a
            # smaller cohort than the one the paper reports.
            unparsed.append(r)
            continue
        if ratio == 2.0:
            exact.append(r)
        if abs(ratio - 2.0) <= 2.0 * TOLERANCE:
            near.append(r)
        elif 1.15 <= ratio <= 1.50:
            mid.append(r)
        elif ratio == 1.0:
            exact_one.append(r)
        elif abs(ratio - 1.0) <= 0.01:
            near_one.append(r)
        else:
            outlier.append(ratio)

    by_vendor = collections.Counter(r["manufacturer"] for r in exact)
    print(f"\nratio exactly 2.0 : {len(exact)}")
    for vendor, n in sorted(by_vendor.items()):
        print(f"    {vendor}: {n}")
    print(f"ratio within {100 * TOLERANCE:.1f}% of 2.0 : {len(near)}"
          f"   (+{len(near) - len(exact)} with sub-millimetre position jitter)")
    print(f"ratio 1.15-1.50 (GE) : {len(mid)}")
    print(f"within 1% of 1.0 (position jitter) : {len(near_one)}")
    print(f"outliers : {len(outlier)}   (ratios "
          + ", ".join(f"{x:.2f}" for x in sorted(outlier)) + ")")
    print(f"no-op (ratio exactly 1.0) : {len(exact_one)}")

    fails = []
    if len(exact) != EXPECT_EXACT:
        fails.append(f"exact-2.0 count {len(exact)} != published {EXPECT_EXACT}")
    if dict(by_vendor) != EXPECT_EXACT_BY_VENDOR:
        fails.append(f"vendor split {dict(by_vendor)} != published {EXPECT_EXACT_BY_VENDOR}")
    if len(near) != EXPECT_NEAR:
        fails.append(f"near-2.0 count {len(near)} != {EXPECT_NEAR}")
    for label, got, want in (("ratio 1.15-1.50", len(mid), EXPECT_MID),
                             ("minor offsets near 1.0", len(near_one), EXPECT_NEAR_ONE),
                             ("outliers", len(outlier), EXPECT_OUTLIER),
                             ("no-op at exactly 1.0", len(exact_one), EXPECT_NOOP)):
        if got != want:
            fails.append(f"{label} count {got} != published {want}")
    total = len(near) + len(mid) + len(near_one) + len(outlier) + len(exact_one)
    if total + len(unparsed) != len(rows):
        fails.append(f"buckets sum to {total} (+{len(unparsed)} unparsed) != {len(rows)}")
    if unparsed:
        fails.append(f"{len(unparsed)} rows have no usable spacing ratio")
    if fails:
        print("\nFAIL:")
        for f in fails:
            print(f"  {f}")
        return 1

    batch_exact = collections.Counter(r.get("nlst_batch", "?") for r in exact)
    batch_mid = collections.Counter(r.get("nlst_batch", "?") for r in mid)
    print(f"batch of the exact-2.0 cases : {dict(batch_exact)}")
    print(f"batch of the ratio-1.25 cases: {dict(batch_mid)}")
    batch_near = collections.Counter(r.get("nlst_batch", "?") for r in near)
    print(f"batch of the within-0.4% cases: {dict(batch_near)}")
    assert dict(batch_near) == EXPECT_NEAR_BATCH, (
        f"the manuscript says the 0.4% bucket splits {EXPECT_NEAR_BATCH}; got {dict(batch_near)}")
    assert dict(batch_exact) == EXPECT_EXACT_BATCH, (
        f"the manuscript says all {EXPECT_EXACT}.exact-2.0 cases are in batch 3; got {dict(batch_exact)}")
    assert dict(batch_mid) == EXPECT_MID_BATCH, (
        f"the manuscript says the ratio-1.25 cases split {EXPECT_MID_BATCH}; got {dict(batch_mid)}")

    print("\nPASS: every count matches the published values.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
