# Evaluation artifacts

Only privacy-safe routing evidence is bundled. `routing-2026-07-13-v3/`
contains an intentional fixture, pseudonymous case IDs, judgments, bounded
scores, and the public description variants needed to reproduce those scores.
Its result applies only to that fixture.

This repository does not publish raw run IDs, judge IDs, provider/session/agent
IDs, transcripts, personal logs, machine paths, or private skill snapshots.
The bundled fixture does not constitute Production run-compare evidence for
YW SkillFoundry 2.0.0.

Contributors may generate richer evidence locally, outside the repository or
inside an ignored workspace. Before publishing a minimal fixture:

1. replace external identifiers with release-local labels such as `run-a1`,
2. remove transcripts, logs, machine paths, and private snapshots,
3. retain only intentionally public inputs and bounded result summaries,
4. run `python3 scripts/privacy_lint.py --working-tree-only`,
5. never commit private identifiers and rely on later deletion to hide them.

See `PRIVACY.md` for the complete publication policy.
