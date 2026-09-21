#!/usr/bin/env python3
"""RETIRED 2026-09-21 as a reconstruction; kept as a check that the table states its own callees.

`identity_nlst_full_n2231.csv` now carries `ours_callee_*` and `ref_callee_*` on **every row**,
written at run time by driver v2.0.0. There is nothing left to reconstruct, and this script no
longer writes a sidecar. What it still does is verify that those columns are present, single-valued
and name the pinned upstream function -- because a table that silently lost them would look exactly
like one that never needed them.

The original text follows, because the reasoning is worth keeping: the table used to be generated
before the driver recorded its callees, so the facts were reconstructed rather than captured. That
is a weaker claim and the sidecar said so in its own text. What makes
the reconstruction checkable rather than asserted is one temporal fact this script verifies every
time it runs: **the last commit touching either comparator predates the first row's timestamp**,
so the source in the tree is the source that ran. If someone edits a comparator, the argument
stops holding and this exits non-zero rather than quietly printing a stale digest.

It cannot close the gap entirely, and nothing run afterwards can -- that is the same limit M3a
states about reproducing a published score. Runs from version 1.1.0 of the driver carry the
`ours_callee_*` / `ref_callee_*` columns and need no reconstruction.

Run: python3 scripts/record_callee_provenance.py [--write]
"""
from __future__ import annotations

import csv
import hashlib
import datetime as dt
import pathlib
import subprocess
import sys

REPO = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))
from callee_provenance import callee_record  # noqa: E402
from agatston_vectorised import agatston_vectorised  # noqa: E402
from agatston_vendor_ref import agatston_naive  # noqa: E402

TABLE = REPO / "results_expected" / "identity_nlst_full_n2231.csv"
UPSTREAM_COMMIT = "6989588536d266b00c422ef98f2fcf809a6b895a"
ARMS = [("CAC Plus, vectorised", agatston_vectorised, "src/agatston_vectorised.py"),
        ("reference comparator", agatston_naive, "src/agatston_vendor_ref.py")]


def last_commit(rel: str) -> tuple[str, dt.datetime]:
    """The commit that last touched this file, not the repository HEAD.

    `callee_record` reports HEAD, which is the right thing for a run -- it pins the whole tree
    alongside the dirty flag. It is the wrong thing here: this sidecar is a statement about two
    files, and HEAD moves for reasons that have nothing to do with either of them.
    """
    out = subprocess.run(["git", "-C", str(REPO), "log", "-1", "--format=%H %cI", "--", rel],
                         capture_output=True, text=True, timeout=15)
    sha, iso = out.stdout.strip().split()
    return sha, dt.datetime.fromisoformat(iso).replace(tzinfo=None)


def main() -> int:
    """Assert that the shipped table names its own comparators. No reconstruction."""
    with TABLE.open(newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    need = ["ours_callee", "ours_callee_source_sha256", "ours_callee_repo_commit",
            "ref_callee", "ref_callee_source_sha256", "ref_callee_repo_commit"]
    missing = [c for c in need if c not in (rows[0] if rows else {})]
    if missing:
        print("FAIL: the table no longer records its callees: " + ", ".join(missing))
        return 1

    bad = []
    # What must be constant is the FUNCTION, i.e. its source digest -- not the repository HEAD.
    # A run that spans an unrelated commit records two HEADs and is perfectly sound: this table
    # does, because a CHANGELOG commit landed between the pilot's tenth case and its eleventh,
    # and the diff of the scored function across those two commits is empty. Asserting on HEAD
    # would fail a correct run; asserting on the digest catches the thing that would matter.
    for col in need:
        vals = {r[col].strip() for r in rows}
        if "" in vals:
            bad.append(f"{col} is blank on at least one row")
        if col.endswith("sha256") or col in ("ours_callee", "ref_callee"):
            if len(vals) != 1:
                bad.append(f"{col} changed mid-run: {len(vals)} distinct values across "
                           f"{len(rows)} rows -- the comparator was not one function")
    for col in ("ours_callee_repo_commit", "ref_callee_repo_commit"):
        n = len({r[col] for r in rows})
        if n > 1:
            print(f"  note: {col} spans {n} commits; the source digest is unchanged, so the "
                  f"function is the same and the repository simply moved")
    ref = rows[0]["ref_callee"]
    if "AI-CAC@v1.0.0" not in ref or "compute_agatston_for_vol" not in ref:
        bad.append(f"reference arm is {ref!r}; expected the pinned upstream function")

    # Round seven: a reviewer replaced every recorded upstream digest with 64 zeros and this
    # script still returned success. It was checking that the digest was *single-valued*, never
    # that it was *right* -- the exact defect the injection tests exist to catch, in the script
    # written to enforce provenance. A digest nothing is compared against is decoration.
    #
    # Recompute it from the pinned checkout when that checkout is present. When it is not, say
    # the digest is unauthenticated rather than pass quietly: a reader without the upstream
    # source cannot verify this row, and the output should tell them so.
    recorded = rows[0]["ref_callee_source_sha256"].strip()
    upstream = pathlib.Path.home() / "projects" / "_upstream" / "AI-CAC-v1.0.0" / "processing.py"
    if upstream.is_file():
        # Parse, do not import: upstream's module header pulls in torch, pandas and pydicom,
        # and none of them is needed to read one function's source text.
        import ast
        try:
            text = upstream.read_text(encoding="utf-8")
            node = next(n for n in ast.parse(text).body
                        if isinstance(n, ast.FunctionDef) and n.name == "compute_agatston_for_vol")
            src = ast.get_source_segment(text, node)
            actual = hashlib.sha256((src + "\n").encode("utf-8")).hexdigest()
        except Exception as exc:                       # noqa: BLE001 - reported, not raised
            bad.append(f"could not hash the pinned upstream function: {type(exc).__name__}")
        else:
            if actual != recorded:
                bad.append(f"recorded upstream digest {recorded[:16]}… does not match the pinned "
                           f"source, which hashes to {actual[:16]}…")
            else:
                print(f"  digest authenticated against {upstream}")
    else:
        print(f"  [!] {upstream} absent: the recorded upstream digest is NOT authenticated here. "
              f"Clone Raffi-Hagopian/AI-CAC at v1.0.0 to that path to check it.")
    if {r["ref_callee_repo_commit"] for r in rows} != {UPSTREAM_COMMIT}:
        bad.append(f"reference commit {rows[0]['ref_callee_repo_commit'][:12]}, "
                   f"expected {UPSTREAM_COMMIT[:12]}")

    print(f"rows {len(rows)}")
    print(f"  test arm      {rows[0]['ours_callee']}")
    print(f"                sha256 {rows[0]['ours_callee_source_sha256'][:16]} @ "
          f"{rows[0]['ours_callee_repo_commit'][:12]}")
    print(f"  reference arm {rows[0]['ref_callee']}")
    print(f"                sha256 {rows[0]['ref_callee_source_sha256'][:16]} @ "
          f"{rows[0]['ref_callee_repo_commit'][:12]}")
    if bad:
        print("\nFAIL:\n  " + "\n  ".join(bad))
        return 1
    print("\nPASS: every row names one comparator pair, and the reference arm is upstream v1.0.0.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
