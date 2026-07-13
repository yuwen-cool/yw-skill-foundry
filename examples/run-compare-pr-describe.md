# Run-Compare — `pr-describe` (2026-06-20)

A historical method reconstruction illustrating this comparison sequence:
**Qualify → Write → lint → P5 candidate selection → run-compare with P1 (variance) + P2 (blind judge).**
The skill, fixture, task, and summarized results are fixed below. Honest limitation: the raw
outputs (two baseline runs, the with-skill run, the verbatim judge prompt) were **not** persisted,
so the verdict here is method-demonstration, not independently re-scorable evidence. The current
protocol requires saving those artifacts into `evals/run-compare-<date>/`
(see `references/quality-assurance.md` § Run-Compare).

## The skill under test

`pr-describe` — given a diff/commits, produce a reviewer-actionable PR description with a fixed
5-section contract (Title / Summary / Changes / Test plan / Risk & rollback). Qualified as a real
skill: reused on every PR, has a reusable output contract, and sits next to easy-to-mis-route
near-neighbors (code review, single commit message, changelog/release notes).

## P5 — description chosen by holdout, not by feel

Two candidate descriptions were scored on the same routing fixture (7 train + 2 holdout, 9 families):

| Candidate | Difference | overall | holdout | result |
|---|---|---|---|---|
| **A** (shipped) | includes `Not for reviewing code / commit message / changelog` exclusions | 9/9 | **2/2** | PASSED |
| B | broad, no exclusions ("working with a PR/diff and wants help") | 6/9 | **1/2** | FAILED |

The per-family breakdown (P4) pinpointed exactly where B leaked: `commit_message 0/1`, `changelog 0/1`,
`code_review_pr 0/1` — all OVER-TRIGGER. **The exclusion clause is what earns the routing**, and the
holdout gate (not the train score) is what made that visible. Candidate A shipped.

## The task (identical for all runs)

> Write a PR description for: refresh-token rotation on every use; reuse/replay detection via a
> token-family id; replayed revoked tokens rejected with HTTP 401 + security event logged; new DB
> migration adds table `refresh_token_family`; tests added. **No linked issue. No benchmark numbers.**

This task has built-in discriminators a strong baseline often misses: a conventional title, *why* per
bullet, a reviewer-actionable test plan, an explicit migration+security risk flag, and the temptation
to invent an issue number that does not exist.

## P1 — variance / noise floor (two baseline runs)

Baseline was run **twice** (no skill) to separate signal from noise. What was **stable across both**
baseline runs (i.e. the real, non-noise gap the skill must close):

| Criterion | baseline-1 | baseline-2 | stable? |
|---|---|---|---|
| Flags DB migration | yes | yes | stable — baseline already does this |
| Flags security nature | yes | yes | stable — baseline already does this |
| Flags breaking client impact | yes | yes | stable — baseline already does this |
| Conventional title (`type(scope):`, ≤70) | no (prose H1) | no (prose H1) | **stable gap** |
| Reviewer-actionable test plan | no (`[x]` self-checklist) | no (describes tests) | **stable gap** |
| Marks missing issue as `TODO` | no (omitted) | no (omitted) | **stable gap** |
| Concise / scannable | no (~52 lines, 7 sections) | no (sprawling) | **stable gap** |

Reading: a strong-model baseline is **already good on substance** (it does flag the migration and the
security risk). The skill's value is **not** "catches the risk" — that would have been noise to claim,
since baseline catches it too. The value is the *form* a reviewer needs: conventional title, why-inline,
runnable test plan, honest `TODO`, brevity — and those gaps are **stable across both baseline runs**, so
they are real, not a single unlucky draw.

## P2 — blind judge (independent, provenance hidden)

The skill output and the **stronger** baseline (baseline-2) were relabeled A/B and given to an
independent agent with only the rubric — it was never told a skill was involved. Verdict:

> **Winner: B (the with-skill output) on all 7 criteria.** "It pairs each change with its rationale,
> gives a runnable reviewer test plan, and explicitly flags the migration + security risk (and the
> missing ticket link) in a compact form, whereas A is accurate but bloated and has a non-conventional
> title with a non-actionable test section."

The retained notes say the blinded judge selected the with-skill output. Because the raw
outputs and verbatim judge prompt are missing, this cannot be audited as clean evidence.
Blinding can reduce authorship bias; it does not prove that all bias was removed.

## Honest verdict

- The retained summary reports a moderate, repeated delta in reviewability rather
  than risky-substance correctness.
- Repeated baselines are a better variance check than one run, but the missing raw
  artifacts prevent independent confirmation that the delta exceeded noise.
- The reusable lesson is to combine holdouts, repeated runs, blinding, and complete
  artifact retention; none of those controls alone proves an unbiased verdict.
