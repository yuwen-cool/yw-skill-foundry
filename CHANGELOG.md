# Changelog

All notable changes to YW SkillFoundry are documented in this file.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.1.0] - 2026-07-14

### Added

- `log.md.example` and `scripts/ensure-log.sh`: a personal iteration-log
  template that is created on first use and never overwritten once it exists,
  so pulling updates cannot clobber a user's own notes.

### Changed

- Rewrote README.md, SKILL.md's opening, SECURITY.md, CONTRIBUTING.md,
  SUPPORT.md, and the GitHub issue/PR templates to lead with Chinese,
  plain-language framing of what the skill does and why, instead of
  process-first technical language.
- Restructured README.md around concrete capability ("what you get") with a
  worked before/after description example, moving install and tooling detail
  below the fold.
- Documented the specific mechanisms behind routing precision and instruction
  constraints (holdout routing eval, tiered authority wording,
  anti-rationalization, executable contracts, tested checkers) instead of
  leaving the claim implicit.
- Documented that `log.md`, `HANDOFF.md`, `private/`, `notes/`, `memory/`,
  and `workspaces/` are pre-ignored, so end users (not just contributors) know
  they can keep local notes without them leaking into a fork.

## [2.0.0] - 2026-07-14

### Changed

- Renamed the public skill, repository, install directory, release archives,
  and emitted protocol namespace to `yw-skill-foundry`; the display brand is
  now YW SkillFoundry.
- Reset the intended public history and removed pre-public run-compare
  snapshots containing private provider/session metadata.
- Limited bundled evidence claims to the privacy-safe routing fixture included
  in this release; 2.0.0 does not claim Production run-compare evidence.
- Replaced tracked-file packaging with an explicit end-user release allowlist.
- Updated the pinned GitHub checkout action to the current Node.js 24 release.

### Security

- Added a no-telemetry publication policy and a dependency-free privacy lint
  for source, reachable Git history, and release archives.
- Added defensive ignores and release gates for private identifiers, personal
  paths and emails, credentials, logs, local databases, caches, and host state.

### Compatibility

- Newly created evidence uses `yw-skill-foundry.*` schema IDs.
- Verifiers continue accepting legacy `skill-foundry.*` and `skill-craft.*`
  v1/v2 artifacts.

## [1.0.1] - 2026-07-13

### Changed

- Upgraded pinned GitHub Actions to Node.js 24-based releases, removing the
  runner deprecation warning from CI and release workflows.

## [1.0.0] - 2026-07-13

### Added

- First public release of the `skill-foundry` Agent Skill.
- Scaffold and Production authoring tracks, references, templates, examples,
  routing fixtures, and auditable run-compare tooling.
- Standard-library Python and Bash validation, contract, evidence, citation,
  and library-audit commands.
- Public CI, deterministic release archives, security policy, and contributor
  documentation.

### Security

- Output targets reject existing and dangling symlinks and accidental
  overwrites.
- Evidence writes use validated parents and atomic replacement.
- Frontmatter parsing handles portable text encodings while rejecting duplicate
  routing keys.

### Compatibility

- Newly created evidence uses `skill-foundry.*` schema IDs.
- Verification remains compatible with persisted legacy `skill-craft.*` v1/v2
  evidence.
