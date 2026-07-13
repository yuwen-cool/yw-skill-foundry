# Routing Evidence — v3 Optimization

## Protocol

- Fixture: `fixture.jsonl` (14 cases; 11 train, 3 holdout).
- Judges saw only the skill name, one description candidate, and unlabeled prompts.
- Before judge: fresh isolated judging session (session identifier removed for publication).
- After judge: fresh isolated judging session (session identifier removed for publication).
- Threshold: 100% for every judged phase.

## Before

- Overall: 13/14 (93%)
- Train: 10/11 (91%) — **FAIL**
- Holdout: 3/3 (100%)
- Miss: id 10, `explain_only`, over-triggered.

The old description included broad “asking about prompt engineering and
instruction design” language without excluding explanation-only requests.
The combined gate correctly failed even though holdout passed.

## After

- Overall: 14/14 (100%)
- Train: 11/11 (100%)
- Holdout: 3/3 (100%)
- Result: **PASS**

The replacement description excludes explanation, summary, and translation
requests that do not create or change an instruction artifact.

## Reproduce

```bash
python3 scripts/trigger_eval.py score \
  --fixture evals/routing-2026-07-13-v3/fixture.jsonl \
  --judgments evals/routing-2026-07-13-v3/judgments-before.jsonl

python3 scripts/trigger_eval.py score \
  --fixture evals/routing-2026-07-13-v3/fixture.jsonl \
  --judgments evals/routing-2026-07-13-v3/judgments-after.jsonl
```
