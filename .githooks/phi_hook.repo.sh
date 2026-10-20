# .githooks/phi_hook.repo.sh — per-repo extension for the cardiac PHI hook.
# Sourced by .githooks/pre-commit (the canonical core from
# cardiac-shared/tools/phi_hook/pre-commit). Edit this file, not the core.
# Seed: cardiac-shared/tools/phi_hook/repos/cac-plus-reproducibility.sh — after
# rollout the copy in the repo is authoritative; the seed is only used when the
# repo has none.
#
# This repository is PUBLIC. Group 3 (real names) is deliberately absent: a
# tracked file naming people publishes them. Names live in the gitignored
# .githooks/phi_patterns.local (group 8).
#
# Before CS-069 this repo's hook set PROJECT_PATTERN='gt_total|gt_LCA|...' but
# never OR-ed it into PATTERN, so it blocked nothing. The COCA protection that
# actually ran is the data-file check below; it is reproduced unchanged.
REPO_PATTERN=''
REPO_ALLOWLIST_RE=''

# COCA expert-score columns — DATA FILES ONLY.
#
# Stanford's Research Use Agreement for the AIMI datasets forbids publishing
# "any portion" of the Dataset, and Stanford describes the expert calcium scores
# as part of the Dataset rather than a derivative of it. A committed CSV carrying
# gt_total (or the per-vessel gt_* columns) would therefore be a redistribution.
#
# Scoped to data extensions on purpose. These names appear legitimately in source
# and prose -- analysis/agreement_panel.py takes `--reference-column gt_total`
# precisely because the user supplies that file from their own download, and this
# hook's first version blocked its own documentation. A pattern that fires on the
# control describing it teaches people to bypass the hook.
repo_extra_checks() {
    local staged_data coca_hits
    mapfile -t staged_data < <(printf '%s\n' "$@" | grep -iE '\.(csv|tsv|json|xlsx|parquet)$' || true)
    if (( ${#staged_data[@]} > 0 )); then
        coca_hits=$(git grep --cached -nE '\bgt_(total|LCA|LAD|LCX|RCA)\b' -- "${staged_data[@]}" 2>/dev/null || true)
        if [[ -n "$coca_hits" ]]; then
            echo "============================================================" >&2
            echo "ERROR: pre-commit blocked — COCA expert scores in a data file" >&2
            echo "============================================================" >&2
            echo "$coca_hits" >&2
            echo >&2
            echo "Stanford's Research Use Agreement forbids publishing any portion of" >&2
            echo "the Dataset, and the expert scores are part of it. Nothing" >&2
            echo "COCA-derived belongs in this repository; analysis scripts take the" >&2
            echo "reference file as an argument from the reader's own download." >&2
            return 1
        fi
    fi
    return 0
}
