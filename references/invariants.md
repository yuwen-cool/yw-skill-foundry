# YW SkillFoundry Invariants

## Contents

- [1. Metadata](#1-metadata)
- [2. Size and Disclosure](#2-size-and-disclosure)
- [3. Module Tracks](#3-module-tracks)
- [4. Evaluation Gates](#4-evaluation-gates)
- [5. Evidence Integrity](#5-evidence-integrity)
- [6. Rule Authority](#6-rule-authority)

This file is the single source of truth for rules repeated across `SKILL.md`,
templates, references, and scripts. Other files may explain these rules, but
must not redefine their thresholds.

## 1. Metadata

- Frontmatter requires only `name` and `description` for portability.
- `name`: 1–64 characters; lowercase ASCII letters, digits, and single hyphens;
  no leading, trailing, or consecutive hyphens; it matches the skill directory
  name.
- `description`: 1–1024 Unicode characters. It states capability + trigger
  conditions, never workflow steps.
- Language coverage follows observed user requests. Bilingual descriptions are
  optional unless the target population actually uses both languages.
- Provider-specific fields are extensions. Add them only when the target host
  is known and document that dependency.

## 2. Size and Disclosure

- `SKILL.md` should stay at or below 500 lines.
- 501–700 lines requires an explicit reason or a split into conditional
  references.
- More than 700 lines fails the default validator.
- References live one directory depth from `SKILL.md`.
- A reference must be usable without loading another reference. Optional peer
  links are allowed; required nested loads are not.
- Reference files over 100 lines need a table of contents.

## 3. Module Tracks

Scaffold is the default for a first usable version:

1. frontmatter,
2. opening statement,
3. workflow,
4. hard rules,
5. output format,
6. routing fixture with at least 3 positive and 3 negative cases, including
   one positive and one negative holdout.

Production adds modules only when evidence makes them load-bearing:

- Outcome Contract for externally checked deliverables,
- Capability Circle for real scope or refusal boundaries,
- Mode Router for two or more distinct execution paths,
- Anti-Rationalization after an observed shortcut,
- Gotchas after real failures,
- references when conditional knowledge would otherwise bloat the body,
- scripts when a deterministic check or repeated operation exists.

Empty modules are defects, not signs of completeness.

## 4. Evaluation Gates

- Routing fixtures require complete judgments for every phase that is scored.
- Train-only runs gate train; holdout-only runs gate holdout.
- Combined runs require both train and holdout to meet the threshold.
- Every scored Scaffold or Production routing fixture has at least one positive
  and one negative holdout case.
- Content claims require persisted comparative evidence: a controlled business
  metric when available, otherwise a run-compare. Scaffold trial use may defer
  this layer only when it is labeled unproven.
- Deterministic Output Contract requirements run through `contract_eval.py`.
  Subjective contract checks require explicit pass/fail evidence; ungraded
  manual checks are incomplete, never a pass.
- Regression means re-running the affected routing and content paths after a
  meaningful change.

## 5. Evidence Integrity

A run-compare directory contains:

- `manifest.json`,
- the exact task,
- the exact `SKILL.md` snapshot used by the with-skill run,
- full baseline output,
- full with-skill output,
- the exact blinded Candidate A / Candidate B views sent to judges,
- judge prompt or rubric,
- blind-label mapping,
- `runs.json` with configuration, run number, model identity, output file, and
  either recorded metrics or an explicit reason metrics were unavailable,
- `judges.json` with exact candidate/prompt/evidence files and verdicts,
- verdict with criterion-level reasoning.

The manifest records schema version, skill identity, creation time, file paths,
SHA-256 hashes, and run metadata. Generated evidence is immutable; create a new
directory for a rerun.

Exploratory evidence may use one run per configuration and one blind judge.
Production evidence requires at least two matched baseline/with-skill run
pairs. Every pair receives blind judgments in both A/B orders for each judge
model used. Run IDs, output files, contract reports, judge IDs, and judge
evidence files are unique. Optional field-level examples are available in
`evidence-schema.md`, which SKILL.md indexes directly.

Public evidence uses intentional fixtures and release-local pseudonymous run
and judge labels. Raw provider/session/agent identifiers, transcripts, personal
logs, machine paths, and private skill snapshots are never published.

## 6. Rule Authority

- `MUST` / `NEVER`: safety, irreversible actions, and true non-negotiables.
- Imperative + reason: ordinary operating rules.
- Do not use `consider`, `try to`, or `you might want to` for live requirements.

When files disagree, update them to match this file and add a regression check
when the disagreement is machine-detectable.
