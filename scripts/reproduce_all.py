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
import os
import pathlib
import subprocess
import sys

REPO = pathlib.Path(__file__).resolve().parents[1]


def _colour_supported() -> bool:
    """Whether writing ANSI colour to stdout will render rather than litter it.

    Windows PowerShell 5.1 -- still the default shell on a stock Windows install
    -- does not process VT sequences unless they are switched on, so an
    unconditional "\033[32m" prints as a literal `[32m` before every status. A
    reviewer opening this package on Windows saw exactly that on 2026-09-18.

    Order matters: honour NO_COLOR first (it is a user's explicit choice), then
    refuse colour when stdout is not a terminal (a redirected log should be
    plain text), then on Windows try to enable VT processing and fall back to no
    colour if the console will not take it.
    """
    if os.environ.get("NO_COLOR") is not None:
        return False
    if not sys.stdout.isatty():
        return False
    if sys.platform != "win32":
        return True
    try:                                      # pragma: no cover - Windows only
        import ctypes

        kernel32 = ctypes.windll.kernel32
        handle = kernel32.GetStdHandle(-11)   # STD_OUTPUT_HANDLE
        mode = ctypes.c_uint32()
        if not kernel32.GetConsoleMode(handle, ctypes.byref(mode)):
            return False
        ENABLE_VIRTUAL_TERMINAL_PROCESSING = 0x0004
        return bool(kernel32.SetConsoleMode(
            handle, mode.value | ENABLE_VIRTUAL_TERMINAL_PROCESSING))
    except Exception:
        return False


COLOUR = _colour_supported()
GREEN, RED, YELLOW, DIM, RESET = (
    ("\033[32m", "\033[31m", "\033[33m", "\033[2m", "\033[0m") if COLOUR
    else ("", "", "", "", ""))

# Without colour the status has to carry itself, so bracket it. This is also the
# workspace convention for anything that may be read on a Windows console.
MARK = {"PASS": "[PASS]", "FAIL": "[FAIL]", "SKIP": "[SKIP]"} if not COLOUR else \
       {"PASS": "PASS", "FAIL": "FAIL", "SKIP": "SKIP"}


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
        # Force UTF-8 on both sides. With text=True the parent decodes using its
        # locale and the child encodes using its own; on a GBK console -- the
        # default in a Chinese Windows install -- those disagree and this raised
        # UnicodeDecodeError before printing anything. A reviewer would have seen
        # a traceback instead of a result.
        env = dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONUTF8="1")
        proc = subprocess.run([sys.executable, *self.argv], cwd=REPO, env=env,
                              capture_output=True, encoding="utf-8",
                              errors="replace")
        out = proc.stdout + proc.stderr
        if proc.returncode != 0:
            first = next((l for l in out.splitlines() if l.strip()), "no output")
            return "FAIL", f"exit {proc.returncode}: {first[:70]}", out
        absent = [e for e in self.expect if e not in out]
        if absent:
            return "FAIL", f"published value(s) not in output: {', '.join(absent)}", out
        return "PASS", self.note, out


def build_checks(coca_scores, coca_reference, coca_vendor=None):
    checks = [
        Check("exact Agatston agreement", "sec 3.2 (C1)",
              ["benchmarks/byte_identity_synthetic.py"],
              expect=["preserves the Agatston score exactly"],
              note="freshly generated volumes, no data needed"),
        Check("Agatston-step speedup", "sec 3.3 (C2)",
              ["benchmarks/speedup_realct.py"],
              expect=["50/50", "median 1.97x", "1.01x", "5.53x"],
              note="median 1.97x, 50/50 identical, per-stratum medians"),
        Check("axial-spacing audit", "sec 3.6 (C5)",
              ["analysis/spacing_audit.py"],
              expect=["ratio exactly 2.0 : 274", "SIEMENS: 266", "GE MEDICAL SYSTEMS: 8",
                      "within 0.4% of 2.0 : 280"],
              note="274 at exactly 2.0; 280 within 0.4%"),
        Check("min_calc_object_pixels", "Online R8",
              ["analysis/min_sensitivity.py"],
              expect=["58/100", "14/100", "11/100", "47.7-67.8"],
              note="58 differ, 14 reclassified, 11 cross zero; exact CIs"),
        Check("speedup intervals", "sec 3.3 (C2)",
              ["analysis/speedup_intervals.py"],
              expect=["median 1.97x  95% CI 1.25-3.01x",
                      "median 3.30x  95% CI 2.65-4.91x", "zero             21  median 1.01x"],
              note="bootstrap CIs of the median, 10,000 resamples, seed 42"),
        Check("paired-comparison selftest", "Online M13",
              ["analysis/agreement_panel.py", "--selftest"],
              expect=["identity holds", "55/206 = 0.2669903", "selftest PASS"],
              note="M13's paired code on a fixture; no data needed"),
        Check("cohort manifest", "sec 2.3 / Tab 1",
              ["scripts/verify_cohort_manifest.py"],
              expect=["2231 NLST thin-slice acquisitions", "2231 distinct SeriesInstanceUIDs"],
              note="n = 2,231, one row per series UID, no leak"),
    ]
    if coca_scores and coca_reference:
        checks.append(Check(
            "COCA agreement panel", "sec 3.1 + 3.7",
            ["analysis/agreement_panel.py", "--scores", str(coca_scores),
             "--reference", str(coca_reference)]
            + (["--vendor-scores", str(coca_vendor)] if coca_vendor else []),
            # Every published §3.1/§3.7 value for the CAC Plus arm, on the 206
            # acquisitions both engines scored -- all of which carry a COCA expert
            # reference (§M12). This block was briefly rewritten to a 205 denominator
            # on 2026-09-19 and is restored: the 205 came from a derived reference
            # file that is missing one row, read as an acquisition with no reference.
            # An acceptance criterion is as much a published claim as the prose is,
            # so it has to move when the claim does -- and it has to move back when
            # the claim does. Add --vendor-scores to run M13's paired comparison too.
            expect=["n = 206", "0.957", "0.754", "0.856", "0.734",
                    "72.0%", "52.4%", "42.7%", "-106.1"],
            needs=(coca_scores, coca_reference),
            note="CCC 0.856, kappa 0.734, sens 72.0%, zero-CAC 52.4/42.7, bias -106.1"
                 + (" + M13 paired" if coca_vendor else "")))
    else:
        checks.append(Check(
            "COCA agreement panel", "sec 3.1 + 3.7",
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
    ap.add_argument("--coca-vendor-scores", type=pathlib.Path,
                    help="your unmodified-vendor scores for COCA: patient_id + "
                         "agatston_decoupled. Adds M13's paired comparison, which is the "
                         "one the manuscript makes; without it the panel runs one arm only")
    ap.add_argument("-v", "--verbose", action="store_true",
                    help="print each check's full output")
    a = ap.parse_args()

    checks = build_checks(a.coca_scores, a.coca_reference, a.coca_vendor_scores)
    print(f"CAC Plus reproducibility package - {len(checks)} checks\n")

    results = []
    for c in checks:
        if COLOUR:
            print(f"{DIM}running{RESET} {c.name} ...", end="\r", flush=True)
        status, detail, out = c.run()
        colour = {"PASS": GREEN, "FAIL": RED, "SKIP": YELLOW}[status]
        print(f"  {colour}{MARK[status]:<6}{RESET} {c.section:<16} {c.name:<26} {DIM}{detail}{RESET}")
        if a.verbose or status == "FAIL":
            for line in out.splitlines():
                print(f"         {DIM}{line}{RESET}")
        results.append(status)

    n_pass, n_fail, n_skip = (results.count(s) for s in ("PASS", "FAIL", "SKIP"))
    print()
    if n_fail:
        print(f"{RED}FAILED{RESET} - {n_fail} check(s) did not reproduce a published value. "
              f"{n_pass} passed, {n_skip} skipped.")
        return 1
    if n_skip:
        print(f"{GREEN}{n_pass} of {n_pass} runnable checks reproduce the manuscript.{RESET}")
        print(f"{YELLOW}{n_skip} skipped{RESET} - pass --coca-scores and --coca-reference to "
              f"include the COCA panel (see README).")
        return 0
    print(f"{GREEN}All {n_pass} checks reproduce the manuscript.{RESET}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
