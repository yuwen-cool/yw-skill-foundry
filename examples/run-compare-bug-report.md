# Historical Run-Compare Reconstruction — bug report

This reconstructs an early run-compare method demonstration from its task, skill contract,
and criterion-level notes. The two raw outputs were **not** persisted, so the comparison
cannot be independently re-scored and must not support an effectiveness claim. Use it only
to understand the workflow and reproduce a complete run on another skill. The current protocol
closes that gap — save `task.md`, `baseline.md`, `with_skill.md`, the judge prompt, and the
verdict into `evals/run-compare-<date>/` (see `references/quality-assurance.md` § Run-Compare).

## The skill under test

A small `bug-report` skill authored in Write mode. Its Outcome Contract requires six things:
(1) a one-line title naming symptom + trigger condition, (2) numbered repro steps from a known
state, (3) Expected and Actual as two separate lines, (4) environment/build, (5) a Scope line
stating what does NOT trigger the bug, (6) no guess stated as fact. `trigger_eval.py lint`
passed (description 228 chars, 0 FAIL) and `citation_lint.py` was clean.

## The task (given identically to both subagents)

> Write a bug report: uploading a profile photo larger than ~5 MB makes the spinner run
> forever and the photo never appears; smaller photos upload fine; iOS app v4.1.2, iPhone,
> WiFi; the web uploader accepts the same large file without issue.

A deliberately *different* scenario than the skill's own NO/OK example, so the with-skill
agent must apply the structure, not copy it.

## The diff (against the skill's Outcome Contract)

| Outcome Contract criterion | baseline (no skill) | with-skill | delta |
|---|---|---|---|
| 1. Title names symptom + trigger | met | met | even |
| 2. Numbered repro from known state | met | met | even |
| 3. Expected / Actual on separate lines | met (as sections) | met (strict two lines) | even |
| 4. Environment / build | met | met | even |
| 5. **Scope line (what does NOT trigger it)** | present but buried in "Additional Notes," mixed with speculation | **dedicated `Scope:` line** | **improved** |
| 6. **No guess stated as fact** | "indicating the issue is specific to the iOS client" — stated fairly assertively | guess explicitly tagged "(stated as a guess, not confirmed)" | **improved** |
| (bonus) structural restraint | added unrequested Severity / Additional Notes sections | strictly in contract order, no sprawl | improved |

## Verdict (honest)

The retained notes reported a moderate delta concentrated in the `Scope:` slot and explicit
speculation labeling. Because the source outputs are missing, treat that as an unverified
historical observation, not a measured result. The useful lesson is procedural: persist raw
artifacts first, then grade every criterion so an all-even result can remain a valid outcome.

## How to reproduce

1. Author the skill; run `trigger_eval.py lint` and `citation_lint.py`.
2. Pick one hard, real task — NOT the skill's own example.
3. Spawn two subagents on that task: one given the SKILL.md to follow, one with no skill.
4. Persist the raw artifacts first — `task.md`, `baseline.md`, `with_skill.md` in
   `evals/run-compare-<date>/` — so the comparison stays re-scorable.
5. Diff both outputs against the skill's Outcome Contract, row by row. The delta is the evidence.
