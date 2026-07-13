# YW SkillFoundry

Design, evaluate, and improve production-grade Agent Skills with a reusable
method, runnable checks, and auditable comparison evidence.

YW SkillFoundry is itself an Agent Skill. It helps authors decide whether a skill
is the right vehicle, write precise routing metadata and instructions, choose
between a lightweight Scaffold and a Production track, and verify claims
without treating self-attestation as evidence.

## Evidence scope

This repository bundles one privacy-safe routing evidence set:

- `evals/routing-2026-07-13-v3/` records a 14-case routing optimization.

This fixture-specific evidence supports only the recorded routing cases. It
does not prove universal effectiveness, provide Production run-compare
evidence for 2.0.0, or validate every third-party skill produced with this
project. Raw run IDs, judge IDs, transcripts, personal logs, machine
paths, and private snapshots are not published. See `evals/README.md` and
`PRIVACY.md`.

## Requirements and hosts

- Python 3.10 or later, standard library only
- Bash 3.2 or later
- macOS or Linux
- Codex, Cursor, Claude Code, or another host implementing the Agent Skills
  `SKILL.md` convention

WSL is expected to work but is not currently covered by CI. Native Windows
PowerShell and `cmd.exe` are not supported by the Bash tooling.

## Install

Clone or copy this repository directly into a host's skills directory so the
repository root remains the skill root:

```bash
# Codex
git clone https://github.com/yuwen-cool/yw-skill-foundry.git ~/.codex/skills/yw-skill-foundry

# Cursor
git clone https://github.com/yuwen-cool/yw-skill-foundry.git ~/.cursor/skills/yw-skill-foundry

# Claude Code (project-local)
git clone https://github.com/yuwen-cool/yw-skill-foundry.git .claude/skills/yw-skill-foundry

# Generic Agent Skills host
git clone https://github.com/yuwen-cool/yw-skill-foundry.git <skills-root>/yw-skill-foundry
```

If you already cloned it elsewhere, copy or symlink the complete repository
directory into the host's skills root. Confirm that `SKILL.md` is at
`yw-skill-foundry/SKILL.md`. The directory name is part of the portable skill
identity and validators intentionally reject another parent-directory name.

## Quickstart

Ask your agent for a reusable instruction artifact, for example:

> Create an Agent Skill that reviews database migrations before deployment.

Then validate the result:

```bash
python3 scripts/trigger_eval.py lint --skill path/to/new-skill
bash scripts/validate-skill.sh path/to/new-skill
python3 scripts/citation_lint.py --skill path/to/new-skill
```

Draft routing cases before tuning the body. Start from
`evals/trigger_cases.example.jsonl`, generate an unlabeled worksheet in a fresh
context, and score the returned judgments with `trigger_eval.py`.

## Scaffold vs Production

**Scaffold** is the default first usable version: focused frontmatter, an
opening statement, workflow, hard rules, output format, and a 3-positive /
3-negative routing fixture with holdouts. It must be labeled unproven trial use.

**Production** adds only evidence-backed controls: output contracts, persisted
comparative content evidence, repeated matched runs, blind position-swapped
judging, and regression gates. A structural score is not effectiveness proof.

## Tooling

| Tool | Purpose |
|---|---|
| `scripts/validate-skill.sh` | Structural, metadata, reference, secret, and risky-command checks |
| `scripts/trigger_eval.py` | Routing lint, blinded worksheets, scoring, and bound reports |
| `scripts/contract_eval.py` | Deterministic and explicitly graded output-contract checks |
| `scripts/evidence.py` | Create and verify immutable run-compare manifests |
| `scripts/skill_library_audit.py` | Recursive set-level routing and collision audit |
| `scripts/citation_lint.py` | Scan public body files with an optional external blocklist |
| `scripts/privacy_lint.py` | Reject private paths, emails, raw IDs, sensitive files, and secrets in source/history/archives |
| `scripts/self-check.sh` | Positive and bite tests for the checker suite |
| `scripts/regress.sh` | Full local regression surface |
| `scripts/package-release.py` | Build deterministic versioned tar.gz and zip archives |

New protocol artifacts use `yw-skill-foundry.*` schema IDs. Verification
remains backward-compatible with legacy `skill-foundry.*` and `skill-craft.*`
artifacts; see `references/evidence-schema.md`.

## Release archives

`package-release.py` builds `yw-skill-foundry-<version>.tar.gz` and `.zip`
from an explicit end-user allowlist. Archives include the skill, license,
README, version, dependency declaration, references, scripts, templates,
examples, selected public docs, and sanitized routing fixtures. They exclude
`.github`, Git/editor configuration, unknown tracked paths, caches, and private
artifacts. Every candidate under an allowed release directory is privacy
checked even when it is not allowlisted, and CI scans the completed archives.

## Repository structure

```text
SKILL.md              Active public skill
references/           Conditional methodology and protocol references
scripts/              Dependency-free validation and evidence tools
templates/            Scaffold and Production starters
examples/             Worked examples
evals/                Privacy-safe routing fixtures and evidence
.github/               CI, release automation, and community templates
```

## Verify this release

```bash
bash scripts/regress.sh
python3 scripts/privacy_lint.py
git diff --check
git ls-files -z | python3 -c 'import os,sys; bad=[p for p in sys.stdin.buffer.read().split(b"\0") if p.endswith((b".pyc",b".DS_Store")) or b"__pycache__" in p]; raise SystemExit(bool(bad))'
```

## Standards and research boundaries

- [Agent Skills specification](https://agentskills.io/specification.md) defines
  the portable `SKILL.md` format and progressive-disclosure model.
- [Anthropic's Agent Skills engineering
  overview](https://www.anthropic.com/engineering/equipping-agents-for-the-real-world-with-agent-skills)
  explains metadata discovery and conditional resource loading.
- [Liu et al., *Lost in the Middle* (TACL
  2024)](https://aclanthology.org/2024.tacl-1.9/) shows position-dependent
  degradation in controlled long-context tasks. It does not establish a
  universal token threshold or fixed accuracy loss.
- [Meincke et al., *Persuading large language models to comply with
  objectionable requests* (PNAS
  2026)](https://doi.org/10.1073/pnas.2535868123) measures persuasion effects
  in a safety-compliance setting. YW SkillFoundry treats it only as indirect
  evidence that framing can affect model behavior, never as a measured Skill
  compliance gain.

## Security and limitations

The tools reject output symlinks, accidental overwrites, path escapes in
evidence, malformed metadata, and common secret patterns. They do not sandbox
an agent, authenticate provider run IDs, establish rubric validity, or prove
that an instruction is safe for every environment. Review generated skills and
scripts before execution. See `SECURITY.md` for vulnerability reporting and
`PRIVACY.md` for the publication policy.

## Contributing

Read `CONTRIBUTING.md`, `PRIVACY.md`, and `CODE_OF_CONDUCT.md`. Changes to
routing or behavior should include the smallest privacy-safe fixture or bite
test. Do not publish raw provider/session identifiers or private snapshots.

## License

MIT © 2026 yuwen-cool. See `LICENSE`.
