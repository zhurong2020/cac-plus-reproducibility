#!/usr/bin/env python3
"""Injection tests: perturb a shipped table, require the check to fail.

The first four are the perturbations an external reviewer applied to
`identity_nlst_full_n2231.csv` in round six of AIC-01's review. **Three of them returned exit 0.**
They are kept here verbatim, not paraphrased, because a regression test's job is to fail the way
the original defect failed. The remaining mutations extend the same discipline to the other three
checks, which had never been injection-tested at all.

A mutation is chosen by asking: *if a real run produced a table wrong in this way, would anything
notice?* Where the answer was no, the check was hardened -- see `analysis/full_cohort_identity.py`
for what the first four cost.

Run: python3 tests/test_analysis_mutations.py [check_name ...]
"""
from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from mutate import Mutation, check_mutations  # noqa: E402

IDENTITY = "identity_nlst_full_n2231.csv"
SENS = "min_sensitivity_nlst_n100.csv"
SPEEDUP = "speedup_nlst_b3_50case.csv"
MANIFEST = "nlst_cohort_manifest.csv"


# --- round six, reproduced verbatim ------------------------------------------------------

def _published_score_altered(rows):
    """Reviewer's mutation 1. Passed: the check trusted `reproduces_published` as a flag."""
    rows[0]["published_score"] = "999999"
    return rows


def _duplicate_row(rows):
    """Reviewer's mutation 2. Caught, but only by the row count -- so it would have been missed
    had it replaced a row instead of appending one. Both forms are now tested."""
    return rows + [dict(rows[0])]


def _error_row_appended(rows):
    """Reviewer's mutation 3. Passed: nothing asserted that every row succeeded."""
    bad = dict(rows[0])
    bad.update(patient_id="INJECTED", series_uid="1.2.injected", status="error",
               error="injected", score_vectorised="", score_vendor_naive="", identical="",
               published_score="", reproduces_published="", mask_ge130_pct="")
    return rows + [bad]


def _alignment_flattened(rows):
    """Reviewer's mutation 4. Passed: only the *minimum* of the distribution was asserted, and
    the mutation preserved it. A summary statistic is not the distribution."""
    for r in rows:
        if r.get("mask_ge130_pct", "").strip():
            r["mask_ge130_pct"] = "88.90"
    return rows


# --- the same questions, asked of the rest of the table ----------------------------------

def _duplicate_replaces_a_row(rows):
    """The row count survives; only an identifier-uniqueness assertion catches this."""
    rows[1] = dict(rows[0])
    return rows


def _one_score_disagrees(rows):
    """The headline claim itself: 2,231 of 2,231 exact agreement."""
    rows[5]["score_vendor_naive"] = str(float(rows[5]["score_vendor_naive"]) + 1.0)
    return rows


def _stratum_shifted(rows):
    """A case moved across a burden boundary; the strata are published counts."""
    rows[0]["score_vectorised"] = rows[0]["score_vendor_naive"] = rows[0]["published_score"] = "450.0"
    return rows


def _blank_identifier(rows):
    """A blank key is the failure mode that made 19 patients inherit a stranger's record here in
    2026-09. It does not raise; it makes missingness look better."""
    rows[3]["patient_id"] = "   "
    return rows


# --- the other three checks --------------------------------------------------------------

def _sens_recompute_flag_flipped(rows):
    """The sensitivity table carries its own agreement flag. Is it recomputed or believed?"""
    for r in rows[:4]:
        r["score_min1_vendor_batch"] = str(float(r["score_min1_vendor_batch"]) + 25.0)
    return rows


def _sens_row_dropped(rows):
    return rows[:-1]


def _speedup_ratio_inflated(rows):
    """The published speedup interval must come from the timings, not from a stored ratio."""
    for r in rows:
        r["speedup_ratio_min1"] = "99.0"
    return rows


def _speedup_timing_zeroed(rows):
    for r in rows[:5]:
        r["cac_plus_optimized_s"] = "0.0"
    return rows


def _manifest_spacing_retyped(rows):
    """The spacing partition is a published count; retyping thick as thin must move it."""
    for r in rows[:40]:
        r["actual_spacing_mm"] = "1.0"
    return rows


def _manifest_row_dropped(rows):
    return rows[:-3]


# --- round seven: the reviewer's attack on the provenance checker ------------------------

def _upstream_digest_zeroed(rows):
    """Round seven, verbatim. The checker asserted the digest was single-valued and never that
    it was *right*, so 64 zeros passed. A digest nothing is compared against is decoration."""
    for r in rows:
        r["ref_callee_source_sha256"] = "0" * 64
    return rows


def _upstream_commit_swapped(rows):
    for r in rows:
        r["ref_callee_repo_commit"] = "deadbeef" * 5
    return rows


def _callee_renamed(rows):
    """The table would then name a comparator that is not the pinned upstream function."""
    for r in rows:
        r["ref_callee"] = "cac-plus-reproducibility:src/agatston_vendor_ref.py::agatston_naive"
    return rows


SUITES = {
    "full_cohort_identity.py": [
        Mutation("published_score -> 999999", IDENTITY, _published_score_altered,
                 "reproduces_published is trusted as a flag instead of recomputed from the column"),
        Mutation("duplicate row appended", IDENTITY, _duplicate_row,
                 "only the row count would notice, and only because the count changed"),
        Mutation("status=error row appended", IDENTITY, _error_row_appended,
                 "nothing asserts that every row succeeded"),
        Mutation("every alignment value -> 88.90", IDENTITY, _alignment_flattened,
                 "only the minimum is asserted, and the mutation preserves it"),
        Mutation("duplicate replaces a row", IDENTITY, _duplicate_replaces_a_row,
                 "identifier uniqueness is unasserted and the row count is unchanged"),
        Mutation("one score disagrees", IDENTITY, _one_score_disagrees,
                 "the headline 2231/2231 agreement is not recomputed"),
        Mutation("a case crosses a burden boundary", IDENTITY, _stratum_shifted,
                 "the published strata are not recomputed from the scores"),
        Mutation("blank patient_id", IDENTITY, _blank_identifier,
                 "a blank key joins to everything and raises nothing"),
    ],
    "min_sensitivity.py": [
        Mutation("vendor scores shifted", SENS, _sens_recompute_flag_flipped,
                 "the recorded agreement flag is believed rather than recomputed"),
        Mutation("a row dropped", SENS, _sens_row_dropped,
                 "the denominator is not asserted"),
    ],
    "speedup_intervals.py": [
        Mutation("stored ratio inflated to 99x", SPEEDUP, _speedup_ratio_inflated,
                 "the interval is read from a stored ratio rather than recomputed from timings"),
        Mutation("optimised timings zeroed", SPEEDUP, _speedup_timing_zeroed,
                 "a zero or negative duration is not rejected"),
    ],
    "../scripts/record_callee_provenance.py": [
        Mutation("upstream digest -> 64 zeros", IDENTITY, _upstream_digest_zeroed,
                 "the digest is asserted single-valued but never compared to the pinned source"),
        Mutation("upstream commit swapped", IDENTITY, _upstream_commit_swapped,
                 "the recorded commit is not checked against the pinned release"),
        Mutation("reference arm renamed to the transcription", IDENTITY, _callee_renamed,
                 "the table could name our transcription and still pass"),
    ],
    "spacing_audit.py": [
        Mutation("40 acquisitions retyped as 1.0 mm", MANIFEST, _manifest_spacing_retyped,
                 "the published spacing partition is not recomputed from the column"),
        Mutation("3 rows dropped", MANIFEST, _manifest_row_dropped,
                 "the manifest denominator is not asserted"),
    ],
}


def main(argv: list[str]) -> int:
    wanted = argv[1:] or list(SUITES)
    rc = 0
    for name in wanted:
        if name not in SUITES:
            print(f"unknown check: {name}; known: {', '.join(SUITES)}")
            return 3
        rc |= check_mutations(name, SUITES[name])
        print()
    print("ALL SUITES PASS" if rc == 0 else "ONE OR MORE SUITES FAILED")
    return rc


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
