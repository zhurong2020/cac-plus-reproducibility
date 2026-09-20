#!/usr/bin/env python3
"""A shared fixture for injection-testing the checks in `analysis/`.

**Why this exists.** Every check in this repository asserts that the published numbers are what
the shipped tables say. Nothing asserted that the checks *notice when the tables are wrong*. In
September 2026 an external reviewer perturbed `identity_nlst_full_n2231.csv` four ways and the
checker returned exit 0 on three of them: it recomputed one predicate from the numeric columns
and then trusted a recorded flag for the other, never asserted zero failed rows, and asserted
only the minimum of a distribution, which the mutation preserved. Those four perturbations are
now regression tests in `test_analysis_mutations.py`.

**Why it is a fixture and not four hand-written tests.** The first attempt at reproducing that
report was written by hand and got the wrong answer: the harness wrote a mutated CSV and never
closed the file, so the subprocess read a truncated table and failed on the row count instead of
on the thing under test. All four mutations looked caught. Three were not. A test that reports a
pass for the wrong reason is worse than no test, so the handling of the file is in one place
here, and two rules are enforced rather than remembered:

1. **The unmutated control must pass first.** If the baseline fails, every "mutation caught"
   below it is uninformative -- that is precisely how the truncated file hid three defects.
2. **A mutation must change the bytes**, and the written file is closed, flushed and re-read
   before the check sees it. A mutation that silently matched nothing would otherwise count as
   a caught defect forever.

Adding an injection test to a new check should cost three lines; that is the point. See the
bottom of this file for the shape.
"""
from __future__ import annotations

import csv
import hashlib
import io
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile
from typing import Callable, Iterable, NamedTuple

REPO = pathlib.Path(__file__).resolve().parents[1]

Rows = list[dict]


class Mutation(NamedTuple):
    """One perturbation of one shipped table, and what the check is expected to do about it."""

    name: str
    table: str                      # file name under results_expected/
    apply: Callable[[Rows], Rows]   # pure; returns the mutated rows
    why: str                        # what a reader should learn from this one failing


def _write_csv(path: pathlib.Path, rows: Rows, fieldnames: list[str]) -> int:
    """Write and return the byte length. Closed via context manager, then verified on disk.

    The explicit re-stat is not defensive decoration: the bug this fixture was built after was an
    unclosed handle, and the symptom was a plausible-looking failure for the wrong reason.
    """
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=fieldnames)
    w.writeheader()
    w.writerows(rows)
    payload = buf.getvalue().encode("utf-8")
    with open(path, "wb") as fh:
        fh.write(payload)
        fh.flush()
        os.fsync(fh.fileno())
    on_disk = path.stat().st_size
    if on_disk != len(payload):
        raise AssertionError(f"{path.name}: wrote {len(payload)} bytes, {on_disk} on disk")
    return on_disk


def _sandbox(script: pathlib.Path, tables: Iterable[str], tmp: pathlib.Path) -> pathlib.Path:
    """A throwaway tree the check can run in without touching the working copy.

    The checks resolve their data as `Path(__file__).resolve().parents[1] / "results_expected"`,
    and `resolve()` follows symlinks -- so the script and the tables it reads are real copies,
    while everything else is linked. That keeps the sandbox cheap and keeps a mutated table from
    ever being written inside the repository.
    """
    (tmp / "analysis").mkdir(parents=True, exist_ok=True)
    (tmp / "results_expected").mkdir(parents=True, exist_ok=True)
    shutil.copy2(script, tmp / "analysis" / script.name)
    for t in tables:
        shutil.copy2(REPO / "results_expected" / t, tmp / "results_expected" / t)
    for entry in REPO.iterdir():
        if entry.name in {"analysis", "results_expected", ".git"}:
            continue
        link = tmp / entry.name
        if not link.exists():
            link.symlink_to(entry)
    return tmp / "analysis" / script.name


def _run(script: pathlib.Path) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(script)], capture_output=True, text=True,
                          cwd=script.parents[1], timeout=300)


def check_mutations(script_name: str, mutations: list[Mutation]) -> int:
    """Run one check unmutated, then once per mutation. Returns a process exit code.

    The control is not optional and not a formality: it is the assertion that a failure below it
    means what it appears to mean.
    """
    script = REPO / "analysis" / script_name
    tables = sorted({m.table for m in mutations})
    print(f"== {script_name}: control + {len(mutations)} mutation(s) ==")

    with tempfile.TemporaryDirectory(prefix="mutate-control-") as d:
        control = _run(_sandbox(script, tables, pathlib.Path(d)))
    if control.returncode != 0:
        print(f"  CONTROL FAILED (exit {control.returncode}) -- every result below is "
              f"uninformative until this passes.\n{control.stdout[-1500:]}{control.stderr[-800:]}")
        return 1
    print("  control (unmutated): PASS, so a failure below is attributable to the mutation")

    failures = []
    for m in mutations:
        with tempfile.TemporaryDirectory(prefix="mutate-") as d:
            tmp = pathlib.Path(d)
            sandboxed = _sandbox(script, tables, tmp)
            target = tmp / "results_expected" / m.table
            before = target.read_bytes()
            with open(target, newline="", encoding="utf-8") as fh:
                reader = csv.DictReader(fh)
                rows, fieldnames = list(reader), list(reader.fieldnames or [])
            mutated = m.apply([dict(r) for r in rows])
            _write_csv(target, mutated, fieldnames)
            if target.read_bytes() == before:
                failures.append(f"{m.name}: mutation changed nothing -- the test is vacuous")
                print(f"  [X] {m.name}: VACUOUS (bytes unchanged)")
                continue
            got = _run(sandboxed)
        if got.returncode == 0:
            failures.append(f"{m.name}: check returned 0; {m.why}")
            print(f"  [X] {m.name}: NOT CAUGHT (exit 0) -- {m.why}")
        else:
            first = next((ln for ln in got.stdout.splitlines() if ln.strip().startswith("-")), "")
            print(f"  [OK] {m.name}: caught (exit {got.returncode}){(' ' + first.strip()) if first else ''}")

    if failures:
        print(f"\nFAIL: {len(failures)} of {len(mutations)} mutation(s) not caught:")
        for f in failures:
            print(f"  - {f}")
        return 1
    print(f"PASS: all {len(mutations)} mutations caught, control clean.")
    return 0


# --- The shape of a new injection test, for whoever adds the next check -------------------
#
#     from mutate import Mutation, check_mutations
#
#     def _break_a_total(rows):
#         rows[0]["published_score"] = "999999"
#         return rows
#
#     MUTATIONS = [Mutation("published score altered", "my_table.csv", _break_a_total,
#                           "the check trusts a recorded flag instead of the numeric column")]
#     raise SystemExit(check_mutations("my_check.py", MUTATIONS))
#
# Ask of each candidate mutation: if this table were wrong in this way in a real run, would
# anything downstream notice? If the answer is no, the mutation belongs here.
