#!/usr/bin/env python3
"""Dependency-free parser for Agent Skills YAML frontmatter.

This intentionally supports the portable metadata surface used by YW SkillFoundry:
top-level scalar values plus literal/folded block scalars. It is not a general
YAML parser; nested provider extensions remain opaque.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


class FrontmatterError(ValueError):
    """Raised when a SKILL.md has no valid frontmatter envelope."""


BLOCK_SCALARS = {"|", ">", "|-", ">-", "|+", ">+"}


def parse_frontmatter_text(text: str) -> dict[str, str]:
    text = text.removeprefix("\ufeff").replace("\r\n", "\n").replace("\r", "\n")
    match = re.match(r"^---[ \t]*\n(.*?)\n---[ \t]*(?:\n|$)", text, re.DOTALL)
    if not match:
        raise FrontmatterError("no YAML frontmatter (--- ... ---) found")

    lines = match.group(1).splitlines()
    out: dict[str, str] = {}
    i = 0
    while i < len(lines):
        key_match = re.match(r"^([A-Za-z_][\w-]*):[ \t]*(.*)$", lines[i])
        if not key_match:
            i += 1
            continue
        key, value = key_match.group(1), key_match.group(2).strip()
        if key in {"name", "description"} and key in out:
            raise FrontmatterError(f"duplicate frontmatter key: {key}")
        if value in BLOCK_SCALARS:
            style = value[0]
            gathered: list[str] = []
            i += 1
            while i < len(lines) and (
                lines[i].strip() == "" or lines[i][:1] in (" ", "\t")
            ):
                gathered.append(lines[i].strip())
                i += 1
            if style == ">":
                folded: list[str] = []
                previous_was_text = False
                blank_count = 0
                for part in gathered:
                    if part:
                        if blank_count:
                            folded.append("\n" * blank_count)
                        elif previous_was_text:
                            folded.append(" ")
                        folded.append(part)
                        previous_was_text = True
                        blank_count = 0
                    else:
                        blank_count += 1
                        previous_was_text = False
                value = "".join(folded)
            else:
                value = "\n".join(gathered).strip()
        else:
            if (
                len(value) >= 2
                and value[0] == value[-1]
                and value[0] in {'"', "'"}
            ):
                value = value[1:-1]
            i += 1
        out[key] = value.strip()
    return out


def parse_frontmatter_file(path: Path) -> dict[str, str]:
    return parse_frontmatter_text(path.read_text(encoding="utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("file", type=Path, help="SKILL.md to parse")
    args = parser.parse_args()
    try:
        data = parse_frontmatter_file(args.file)
    except (OSError, FrontmatterError) as exc:
        parser.error(str(exc))
    print(json.dumps(data, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
