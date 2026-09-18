#!/usr/bin/env python3
"""Run every check this package can run, and say plainly whether each reproduces.

    python scripts/reproduce_all.py                      # everything that needs no data
    python scripts/reproduce_all.py --coca-scores S.csv --coca-reference R.csv

Four of the five checks need no data at all -- no images, no model weights, no
network. They run from the per-case result tables in results_expected/. Only the
COCA agreement panel needs files you supply, because nothing COCA-derived may be
redistributed (see README).

Why a runner rather than a list of commands: exit code zero is not the same as
reproducing a published number. A script that reads a table and prints a median
exits zero whether the median is 1.97 or 5.87. So each check here carries the
values the manuscript reports, and this runner fails if the output does not
contain them -- which is what "reproduces" has to mean.
"""
from __future__ import annotations

import argparse
import pathlib
import subprocess
import sys

REPO = pathlib.Path(__file__).resolve().parents[1]

GREEN, RED, YELLOW, DIM, RESET = "\033[32m", "\033[31m", "\033[33m", "\033[2m", "\033[0m"


class Check:
    def __init__(self, name, section, argv, expect, needs=(), note=""):
        self.name, self.section, self.argv = name, section, argv
        self.expect = expect          # substrings the output must contain
        self.needs = needs            # paths that must exist, else SKIP
        self.note = note

    def run(self):
        missing = [p for p in self.needs if not pathlib.Path(p).exists()]
        if missing:
            return "SKIP", f"needs {', '.join(str(m) for m in missing)}", ""
        proc = subprocess.run([sys.executable, *self.argv], cwd=REPO,
                              capture_output=True, text=True)
        out = proc.stdout + proc.stderr
        if proc.returncode != 0:
            first = next((l for l in out.splitlines() if l.strip()), "no output")
            return "FAIL", f"exit {proc.returncode}: {first[:70]}", out
        absent = [e for e in self.expect if e not in out]
        if absent:
            return "FAIL", f"published value(s) not in output: {', '.join(absent)}", out
        return "PASS", self.note, out


def build_checks(coca_scores, coca_reference):
    checks = [
        Check("byte-identical Agatston", "§3.2 (C1)",
              ["benchmarks/byte_identity_synthetic.py"],
              expect=["preserves the Agatston score exactly"],
              note="freshly generated volumes, no data needed"),
        Check("Agatston-step speedup", "§3.3 (C2)",
              ["benchmarks/speedup_realct.py"],
              expect=["50/50", "median 1.97x", "1.09x", "5.53x"],
              note="median 1.97x, 50/50 identical, per-stratum medians"),
        Check("axial-spacing audit", "§3.6 (C5)",
              ["analysis/spacing_audit.py"],
              expect=["ratio exactly 2.0 : 274", "SIEMENS: 266", "GE MEDICAL SYSTEMS: 8",
                      "within 0.4% of 2.0 : 280"],
              note="274 at exactly 2.0; 280 within 0.4%"),
        Check("cohort manifest", "§2.3 / Table 1",
              ["scripts/verify_cohort_manifest.py"],
              expect=["2231 NLST thin-slice acquisitions", "2231 distinct SeriesInstanceUIDs"],
              note="n = 2,231, one row per series UID, no leak"),
    ]
    if coca_scores and coca_reference:
        checks.append(Check(
            "COCA agreement panel", "§3.1 + §3.7",
            ["analysis/agreement_panel.py", "--scores", str(coca_scores),
             "--reference", str(coca_reference)],
            # Every published §3.1/§3.7 value for the CAC Plus arm. If the reader
            # supplies the vendor arm instead, CCC reads 0.857 and this check
            # reports the difference rather than silently passing.
            expect=["n = 206", "0.957", "0.754", "0.856", "0.857", "0.734",
                    "72.0%", "52.4%", "42.7%", "-106.1"],
            needs=(coca_scores, coca_reference),
            note="CCC 0.856, ICC 0.857, kappa 0.734, sens 72.0%, zero-CAC 52.4/42.7"))
    else:
        checks.append(Check(
            "COCA agreement panel", "§3.1 + §3.7",
            ["analysis/agreement_panel.py"],
            expect=[], needs=("--coca-scores and --coca-reference",),
            note=""))
    return checks


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--coca-scores", type=pathlib.Path,
                    help="your CAC Plus scores for COCA: patient_id + agatston_score")
    ap.add_argument("--coca-reference", type=pathlib.Path,
                    help="your COCA expert reference: patient_id + gt_total")
    ap.add_argument("-v", "--verbose", action="store_true",
                    help="print each check's full output")
    a = ap.parse_args()

    checks = build_checks(a.coca_scores, a.coca_reference)
    print(f"CAC Plus reproducibility package — {len(checks)} checks\n")

    results = []
    for c in checks:
        print(f"{DIM}running{RESET} {c.name} ...", end="\r", flush=True)
        status, detail, out = c.run()
        colour = {"PASS": GREEN, "FAIL": RED, "SKIP": YELLOW}[status]
        print(f"  {colour}{status:4}{RESET}  {c.section:<16} {c.name:<26} {DIM}{detail}{RESET}")
        if a.verbose or status == "FAIL":
            for line in out.splitlines():
                print(f"         {DIM}{line}{RESET}")
        results.append(status)

    n_pass, n_fail, n_skip = (results.count(s) for s in ("PASS", "FAIL", "SKIP"))
    print()
    if n_fail:
        print(f"{RED}FAILED{RESET} — {n_fail} check(s) did not reproduce a published value. "
              f"{n_pass} passed, {n_skip} skipped.")
        return 1
    if n_skip:
        print(f"{GREEN}{n_pass} of {n_pass} runnable checks reproduce the manuscript.{RESET}")
        print(f"{YELLOW}{n_skip} skipped{RESET} — pass --coca-scores and --coca-reference to "
              f"include the COCA panel (see README).")
        return 0
    print(f"{GREEN}All {n_pass} checks reproduce the manuscript.{RESET}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
