# Security policy

## Scope

This repository is a **reproducibility package**: an Agatston scoring implementation and the
scripts that validate it against a published manuscript. It is not clinical software, it
processes no live patient data, and it exposes no network service. The threat model is
correspondingly narrow.

What is in scope:

- a defect that makes a reported number wrong (a correctness bug in the Agatston
  implementations, the risk-strata definition, or an assertion that passes when it should
  fail);
- an inadvertent disclosure in a committed file — a patient identifier, a data-use-agreement
  violation, a credential;
- a dependency advisory affecting `requirements.txt`.

Out of scope: the wider CAC Plus deployment toolkit, which is not distributed here, and the
wrapped VA AI-CAC algorithm, which belongs to its own upstream project
(`Raffi-Hagopian/AI-CAC`).

## Reporting

Open a GitHub issue for anything in scope. For a disclosure concern — a patient identifier
or a licence-term problem in a committed file — e-mail the corresponding author
(`zhurong0525@gmail.com`) rather than filing a public issue, so it can be removed before it
is amplified.

There is no service level attached to a research package. Expect an acknowledgement rather
than a patch schedule.

## What this repository does about disclosure itself

A pre-commit hook blocks the patterns that have actually appeared here or in sibling
repositories: internal hospital case identifiers, Chinese national-ID shapes, credential
shapes, home-directory paths, patient-name column headers, and the COCA expert-score column
names that the Stanford Research Use Agreement forbids redistributing. It is per-clone, so
it has to be enabled after cloning:

```bash
git config core.hooksPath .githooks
```

It was installed on 2026-09-18, after an audit found 100 rows of internal case identifiers
in a shipped result table. The hook is the reason that class of defect should not recur; it
is not a reason to skip reading a diff.
