# Worked Example — building a skill from scratch, fully self-contained

This file exists to solve a specific problem: a skill's body should never lean on private
skills a reader cannot open and verify. This example
depends on **nothing external**. The domain is deliberately tiny and universal —
*writing a git commit message* — so you can reproduce every step yourself and judge whether
the craft principles actually do what YW SkillFoundry claims.

Read it as a transcript of the Write-mode workflow, with the reasoning shown inline.

---

## Step 1 — Discover (name the default failure)

**What does AI do by default?** Run the task with no skill: "write a commit message for
this diff." Baseline output, observed repeatedly:

```
Update files

- Made some changes to the auth module
- Fixed a few things
- Updated tests
```

The default failures, named precisely:
1. Subject is generic ("Update files") — no type, no scope, no real summary.
2. Body narrates *what* ("made some changes") instead of *why*.
3. No structure a tool or reviewer can parse (no Conventional Commits type).

**The replacement (ZZ):** a typed, imperative subject ≤ 50 chars + a body that states the
*reason for the change*, following Conventional Commits.

This is the whole justification for the skill. If you cannot write this paragraph, stop —
you do not have a problem worth a skill (Hard Rule: skills need a named default failure).

## Step 1.4 — Draft the eval before the body

Trigger cases (these become `evals/trigger_cases.jsonl`):

```jsonl
{"prompt": "写个 commit message", "expect": "trigger", "kind": "exact-zh"}
{"prompt": "help me write a commit message for this diff", "expect": "trigger", "kind": "exact-en"}
{"prompt": "这个提交信息怎么写", "expect": "trigger", "kind": "fuzzy-zh", "holdout": true}
{"prompt": "帮我写一篇博客", "expect": "no", "kind": "near_neighbor"}
{"prompt": "git 怎么撤销 commit", "expect": "no", "kind": "keyword_overlap", "holdout": true}
{"prompt": "今天几号", "expect": "no", "kind": "unrelated"}
```

An output case (what a *good* result looks like — the Content-layer oracle):

```
fix(auth): reject expired refresh tokens before DB lookup

Expired tokens were hitting the user table on every request, adding ~40ms
of latency and a needless query. Validate expiry first and short-circuit.
```

## Step 2 — Name It (description), then lint

```yaml
description: "Use when the user asks to write or improve a git commit message, 写 commit / 提交信息 / commit message, or wants Conventional Commits formatting. Not for explaining git commands or undoing commits (that is plain git help)."
```

Why this passes the routing rules:
- starts with "Use when" → trigger condition, not a capability summary;
- bilingual keywords (写 commit / 提交信息 / commit message);
- has a `Not for…` exclusion → blocks the near-neighbor "git 怎么撤销 commit";
- no workflow language → the agent must read the body to learn *how*.

Run `python3 scripts/trigger_eval.py lint --skill .` → expect 0 FAIL. Then generate
separate train and holdout worksheets, collect fresh-context judgments, and run
`score`. The target is 6/6, including both holdouts; record the actual result rather
than assuming it. The `Not for` clause is intended to make "git 怎么撤销 commit" score
as a correct **no** instead of an over-trigger.

## Step 4 — The crafted SKILL.md (the "after")

```markdown
---
name: commit-message
description: "Use when the user asks to write or improve a git commit message, 写 commit / 提交信息 / commit message, or wants Conventional Commits formatting. Not for explaining git commands or undoing commits."
---

# Commit Message

A commit message is read far more often than it is written. Optimize for the reviewer six
months from now who is asking "why did this change?" — not for describing what the diff did.

## Outcome Contract
- **Outcome**: a Conventional-Commits message: a typed imperative subject + a why-focused body.
- **Done when**: subject ≤ 50 chars, typed, imperative; body explains the reason, wraps at 72.
- **Output**: the message in a fenced block, ready to paste.

## Workflow
1. Read the diff. State in one sentence the *reason* the change exists.
2. Pick the type: feat / fix / refactor / docs / test / chore / perf.
3. Write the subject: `type(scope): imperative summary` — no trailing period, ≤ 50 chars.
4. Write the body: 1-3 sentences on *why*, not *what*. The diff already shows the what.

## Hard Rules
- Subject MUST be imperative mood ("add", not "added"/"adds"). No exceptions.
- Body MUST state a reason. NEVER restate the diff line-by-line.
- NEVER invent a motivation the diff does not support. If the why is unknown, ask.

## Gotchas
| What happened | Rule |
|---|---|
| Subject was "fix: fixed the bug". | "fixed" is past tense and "the bug" is contentless. Imperative + name the bug: "fix(auth): reject expired refresh tokens". |
| Body re-listed every changed file. | The diff already shows files. The body's only job is the why. |
```

Notice what this 30-line skill does **not** have: no references, no scripts, no governance.
That is correct — Scaffold-tier work. Adding a `references/` folder here would be the
over-engineering the official spec warns against. Rigor must track risk, not habit.

## What principles this example demonstrates (verifiable here, not by citation)

| Principle (from a YW SkillFoundry reference) | Where you can see it above |
|---|---|
| Named default failure before writing | Step 1's three numbered failures |
| Eval before body | Step 1.4 fixture + output case |
| Description = trigger, with `Not for` exclusion | Step 2 description + lint reasoning |
| Opening Statement sets a point of view | "read far more often than written…" |
| `What` vs `why` decoupling (Calibration: Meaning > Polish) | Hard Rules + Gotchas |
| Gotcha as a concrete story | the "fixed the bug" row |
| Match rigor to risk (Operating-mode discipline) | the "no references/scripts" note |

You did not need to trust a screenshot of someone's private skill to check any of these.
That is the standard every example in this repo should meet — see *Citation Discipline* in
`references/quality-assurance.md`.
