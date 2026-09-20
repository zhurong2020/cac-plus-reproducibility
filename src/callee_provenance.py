#!/usr/bin/env python3
"""Identify the function a run actually called, not the script that called it.

**Why.** Round six of AIC-01's review found that the two arms of one comparison had used two
different comparators. The 100-case synthetic arm ran against the vendor's own published code;
the 2,231-case arm ran against `src/agatston_vendor_ref.py`, whose docstring says plainly that it
is *our transcription of the vendor's logic, not the vendor's code*. Both runs recorded a
`script_version` column, both said `v1.0`, and both were telling the truth: the driver was the
same. The comparator was not, and no column in either table said which one it was.

A script version identifies the caller. What a result depends on is the **callee**: which module,
which bytes of source, and -- when it came from somewhere else -- which upstream commit. That is
three cheap facts and they belong in the output table, recorded at the time of the run. Recording
them afterwards is not the same thing, and the paper now says so in M3a for a related reason: a
reproduced summary statistic is many-to-one and cannot recover the inputs after the fact.

Usage, three lines in a driver:

    from callee_provenance import callee_record
    PROV = callee_record(agatston_naive)          # once, at import
    row.update(PROV)                              # per row, or once in a sidecar

`callee_record` never raises. A provenance column that crashes a 9-hour batch is worse than one
that says `unavailable`, so every field degrades to a string and the reason is recorded in
`callee_note`.
"""
from __future__ import annotations

import hashlib
import inspect
import pathlib
import subprocess
from typing import Any, Callable

FIELDS = ["callee_qualname", "callee_module_path", "callee_source_sha256",
          "callee_file_sha256", "callee_repo_commit", "callee_repo_dirty",
          "callee_distribution", "callee_note"]


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _git(repo: pathlib.Path, *args: str) -> str:
    out = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True,
                         timeout=15)
    return out.stdout.strip() if out.returncode == 0 else ""


def _repo_state(path: pathlib.Path) -> tuple[str, str, str]:
    """Commit and worktree cleanliness of whatever repository holds this file.

    A commit alone is a half-truth if the tree is dirty -- the file on disk then matches no
    commit at all. The dirty flag is scoped to the file, not the repository: an unrelated edit
    elsewhere says nothing about the function that ran.
    """
    top = _git(path.parent, "rev-parse", "--show-toplevel")
    if not top:
        return "", "", "not under git"
    repo = pathlib.Path(top)
    commit = _git(repo, "rev-parse", "HEAD")
    try:
        rel = path.resolve().relative_to(repo.resolve()).as_posix()
    except ValueError:
        return commit, "unknown", "file outside its own repository root"
    dirty = "yes" if _git(repo, "status", "--porcelain", "--", rel) else "no"
    return commit, dirty, ""


def callee_record(fn: Callable[..., Any]) -> dict[str, str]:
    """Everything needed to say which implementation produced a row. Never raises."""
    rec = dict.fromkeys(FIELDS, "")
    notes: list[str] = []
    try:
        rec["callee_qualname"] = f"{getattr(fn, '__module__', '?')}.{getattr(fn, '__qualname__', repr(fn))}"
    except Exception:
        rec["callee_qualname"] = repr(fn)

    try:
        src = inspect.getsource(fn).encode("utf-8")
        rec["callee_source_sha256"] = _sha256(src)
    except (OSError, TypeError) as exc:
        notes.append(f"source unavailable ({type(exc).__name__})")

    try:
        path = pathlib.Path(inspect.getfile(fn)).resolve()
        rec["callee_module_path"] = str(path)
        rec["callee_file_sha256"] = _sha256(path.read_bytes())
        commit, dirty, why = _repo_state(path)
        rec["callee_repo_commit"], rec["callee_repo_dirty"] = commit, dirty
        if why:
            notes.append(why)
    except Exception as exc:
        notes.append(f"file unavailable ({type(exc).__name__})")

    mod = getattr(fn, "__module__", "") or ""
    try:
        from importlib import metadata
        top = mod.split(".")[0]
        for dist in metadata.distributions():
            if top in (metadata.packages_distributions().get(top) or []) or dist.name == top:
                rec["callee_distribution"] = f"{dist.name} {dist.version}"
                break
    except Exception:
        pass

    rec["callee_note"] = "; ".join(notes)
    return rec


def describe(fn: Callable[..., Any]) -> str:
    """One human-readable line, for a log header or a runbook transcript."""
    r = callee_record(fn)
    where = r["callee_module_path"] or "unknown path"
    commit = (r["callee_repo_commit"] or "no commit")[:12]
    dirty = " (worktree dirty)" if r["callee_repo_dirty"] == "yes" else ""
    return (f"{r['callee_qualname']} <- {where} @ {commit}{dirty} "
            f"source sha256 {r['callee_source_sha256'][:16] or 'n/a'}"
            + (f" [{r['callee_note']}]" if r["callee_note"] else ""))


if __name__ == "__main__":
    import sys
    sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
    from agatston_vectorised import agatston_vectorised
    from agatston_vendor_ref import agatston_naive
    for f in (agatston_vectorised, agatston_naive):
        print(describe(f))
