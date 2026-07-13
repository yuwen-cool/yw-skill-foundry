#!/usr/bin/env python3
"""citation_lint.py — keep the skill body free of names a reader cannot open.

Citation Discipline (references/quality-assurance.md): the loaded body (SKILL.md +
references/ + templates/ + examples/) must not cite private/internal skills. A name a
reader cannot open carries no verifiable evidence and no recognized authority — it just
costs context and reads like an ad. Keep the *technique* and the *inlined evidence*; drop
the name. Public, checkable sources (Anthropic spec, agentskills.io, Meincke et al. PNAS
2026, Lost in the Middle) are fine and are NOT flagged.

This makes that rule runnable instead of self-policed, so the names cannot creep back in.

Usage:
  python3 scripts/citation_lint.py --skill .
  python3 scripts/citation_lint.py --skill . --blocklist policy/private-names.txt

Scans SKILL.md, references/*.md, templates/*.md, examples/*.md. It deliberately
does not scan CHANGELOG.md or historical evidence under evals/.

Exit code 0 = clean, 1 = at least one private name found.

No names are built in. Public distributions must not encode one author's private
library as universal policy. Supply a project-owned blocklist when needed.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

SCAN_GLOBS = ["SKILL.md", "references/*.md", "templates/*.md", "examples/*.md"]


def iter_target_files(skill_dir: Path):
    seen: set[Path] = set()
    for pattern in SCAN_GLOBS:
        for path in sorted(skill_dir.glob(pattern)):
            if path.is_file() and path not in seen:
                seen.add(path)
                yield path


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="citation_lint.py", description=__doc__)
    p.add_argument("--skill", default=".", help="skill directory (contains SKILL.md)")
    p.add_argument(
        "--blocklist",
        default=None,
        help="optional UTF-8 file with names to block, one per line",
    )
    args = p.parse_args(argv)

    blocklist: list[str] = []
    if args.blocklist:
        extra_path = Path(args.blocklist)
        if not extra_path.is_file():
            print(f"error: blocklist file not found at {extra_path}", file=sys.stderr)
            return 2
        for line in extra_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#"):
                blocklist.append(line.lower())

    skill_dir = Path(args.skill).resolve()
    if not (skill_dir / "SKILL.md").is_file():
        print(f"error: SKILL.md not found at {skill_dir}", file=sys.stderr)
        return 2

    # Word-boundary matching keeps a blocked latin name from firing inside a
    # longer word. Names ending in "-" are
    # prefix patterns (e.g. "yuwen-" catches every yuwen-* variant). CJK names
    # match as substrings (CJK has no word boundaries).
    def compile_name(name: str) -> re.Pattern:
        if any("\u4e00" <= ch <= "\u9fff" for ch in name):
            return re.compile(re.escape(name), re.IGNORECASE)
        body = re.escape(name)
        tail = r"" if name.endswith("-") else r"(?![a-z0-9])"
        return re.compile(rf"(?<![a-z0-9]){body}{tail}", re.IGNORECASE)

    patterns = [(name, compile_name(name)) for name in blocklist]

    hits: list[tuple[Path, int, str, str]] = []
    scanned = 0
    for path in iter_target_files(skill_dir):
        scanned += 1
        for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            for name, rx in patterns:
                if rx.search(line):
                    hits.append((path.relative_to(skill_dir), lineno, name, line.strip()))

    print(f"== citation lint: scanned {scanned} body file(s) ==")

    if hits:
        print(f"FOUND {len(hits)} private name reference(s) — strip the name, keep the technique/evidence:\n")
        for rel, lineno, name, line in hits:
            snippet = line if len(line) <= 100 else line[:97] + "..."
            print(f"  {rel}:{lineno}  [{name}]  {snippet}")
        print("\nAction: a reader cannot open these. Remove the name; keep the technique and any "
              "inlined evidence. Public provenance belongs in CHANGELOG.md or an evidence note.")
        return 1

    if blocklist:
        print(f"clean: no names from the {len(blocklist)}-entry external blocklist.")
    else:
        print("clean: no external blocklist supplied; scanned files are readable.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
