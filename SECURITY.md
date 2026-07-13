# Security Policy

## Supported versions

Security fixes are applied to the latest released version of YW SkillFoundry.

## Report a vulnerability

Do not open a public issue for an undisclosed vulnerability. Use GitHub's
private vulnerability reporting feature for this repository. If it is
unavailable, contact the repository owner privately through the contact method
listed on their GitHub profile.

Include:

- the affected file and version,
- a minimal reproduction,
- the security impact,
- any known mitigations.

You should receive an acknowledgement within 7 days. Please allow time for a
fix and coordinated disclosure.

## Scope

Useful reports include path traversal, symlink attacks, unsafe overwrites,
evidence-verification bypasses, command injection, secret disclosure, and CI or
release-archive integrity failures.

Generated skill quality, model behavior, rubric disagreement, and provider
availability are generally correctness or support issues unless they produce a
concrete security impact.

## Safe use

YW SkillFoundry does not sandbox agents or generated scripts. Review instructions
and executable files before use, run with least privilege, and do not place
secrets in skill bodies or evidence artifacts.
