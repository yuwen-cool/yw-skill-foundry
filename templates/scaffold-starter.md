---
name: [skill-name]
description: "[Capability]. Use when [trigger 1], [trigger 2], or [trigger 3]. Not for [near-neighbor]."
---

# [Skill Name]

[AI defaults to X. This skill ensures Y instead.]

## Workflow

### 1. [Verb] — [observable intermediate result]

[Instruction. State what to produce, not merely what to think about.]

### 2. [Verb] — [observable intermediate result]

[Instruction.]

### 3. [Verify] — [pass/fail signal]

[Run a deterministic check when possible; otherwise name the rubric.]

## Hard Rules

- [True non-negotiable] **MUST** [observable behavior]. No exceptions.
- [Safety boundary] **NEVER** [banned behavior], because [brief reason].
- [Ordinary rule as imperative], because [brief reason].

## Output Format

```text
[minimal deliverable structure]
```

<!-- Ship this with evals/trigger_cases.jsonl:
     - at least 3 should-trigger cases
     - at least 3 should-not-trigger cases
     - one JSON object per line: {"prompt":"...","expect":"trigger|no","kind":"..."}
     - mark at least one positive and one negative case with "holdout": true
     Add Production modules only after real usage makes them load-bearing:
     Outcome Contract, Capability Circle, Mode Router, Anti-Rationalization,
     references, scripts, and Gotchas. -->
