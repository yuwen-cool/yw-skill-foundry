# Contributing to YW SkillFoundry

Thank you for improving YW SkillFoundry.

## Before opening a change

1. Search existing issues and pull requests.
2. Keep the change focused and explain the user-visible reason.
3. Publish only privacy-safe fixtures. Never commit raw provider/session IDs,
   transcripts, personal logs, machine paths, or private snapshots.
4. Do not add third-party Python dependencies.

## Development requirements

- Python 3.10 or later
- Bash 3.2 or later
- macOS or Linux; WSL is expected to work but is not currently CI-verified

## Validation

Run:

```bash
bash scripts/regress.sh
python3 scripts/privacy_lint.py
git diff --check
```

Changes to parsers, output writers, path handling, or evidence verification
need focused positive and bite tests in `scripts/self-check.sh`. Changes to
routing metadata need train and holdout cases. Content-effect claims need new
privacy-safe comparative evidence. Evidence claims must remain bounded to the
published fixture.

## Pull requests

Describe:

- what changed and why,
- which risks were considered,
- exact verification commands and results,
- whether evidence scope or compatibility changed.

Use clear commit messages and keep generated caches, local credentials, and
editor or agent state out of the repository. Read and follow `PRIVACY.md`
before adding fixtures, examples, or release artifacts.

By participating, you agree to follow `CODE_OF_CONDUCT.md`.
