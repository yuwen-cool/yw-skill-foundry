# Privacy and Publication Policy

YW SkillFoundry does not collect telemetry. Its local scripts do not send
source, evidence, identifiers, or usage data to a service.

## Never publish

Do not commit, package, attach, or paste any of the following into public
project artifacts:

- personal email addresses or absolute home-directory paths,
- credentials, secrets, tokens, private keys, or `.env*` files,
- logs, `HANDOFF.md`, personal notes, memory directories, or local databases,
- chat, transcript, or conversation dumps,
- raw provider, session, run, judge, or agent identifiers,
- private skill snapshots or private workspaces,
- host-specific agent state, caches, or editor state.

Allowed platform metadata is not treated as personal contact data: GitHub
`noreply` / `support` addresses, id-prefixed `users.noreply.github.com`
addresses (including Dependabot), and the public Cursor agent co-author
address. Maintainer commits and annotated tags must use a GitHub noreply
identity rather than a personal mailbox.

Use `python3 scripts/privacy_lint.py` before publication. In a Git repository
the default scan includes current public files plus reachable commit and tag
metadata and blobs. `--working-tree-only` exists solely for a deliberate
history-cleanup migration; a release must pass the default history scan.

## Public evidence

Public evidence must be intentionally authored for publication. Use
pseudonymous, release-local labels such as `run-a1` and `judge-b1`, and use
synthetic fixtures that contain no real account or provider identifiers.
Describe models and hosts only at the level needed to bound a claim.

The repository may bundle sanitized routing fixtures and aggregate results.
Do not publish raw transcripts, personal logs, private snapshots, or exported
provider records to make an evidence claim look more complete.

## Contributor workflow

Generate experimental evidence outside the repository or in an ignored local
workspace. Before copying selected material into `evals/`:

1. replace external identifiers with release-local pseudonyms,
2. retain only the minimum task, fixture, result, and claim-boundary material,
3. confirm every included input was intentionally created for public use,
4. run `python3 scripts/privacy_lint.py --working-tree-only`,
5. before release, run the default history scan and scan the built archives.

If a finding appears in reachable history, removing the working-tree file is
not sufficient. Rewrite public history before publication, then rerun the
default scan.
