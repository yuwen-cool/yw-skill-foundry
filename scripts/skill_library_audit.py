#!/usr/bin/env python3
"""skill_library_audit.py — find collisions across a *set* of skills, not within one.

Every other checker here grades ONE skill in isolation. A common routing failure
appears only at the *library* level: hosts expose multiple skill descriptions to a
model or router, and overlapping trigger vocabulary can make selection ambiguous.
An isolated test cannot reveal that competition, so this tool audits the loaded set.

This script is the DETERMINISTIC first pass: it surfaces the facts an agent would
otherwise have to eyeball across dozens of files —
  1. Description budget   — total metadata vs a configurable ceiling (--budget).
                            The real ceiling and truncation behavior are HOST-SPECIFIC;
                            the default is a review heuristic, not a platform constant.
  2. Per-skill length     — empty/missing (can't route at all) and >1024 (over limit).
  3. Duplicate names      — two SKILL.md resolving to the same name shadow each other.
  4. Trigger overlap      — skill pairs whose descriptions share enough vocabulary to
                            compete for the same prompt (overlap coefficient + Jaccard).

Discovery is RECURSIVE (depth 6 by default, hidden dirs included, node_modules/.git
skipped), never follows directory symlinks, and accepts multiple --root flags —
one-level scanning misses nested/system/plugin skills and produces a false "clean".

It deliberately does NOT render a final verdict on a collision: judging whether two
overlapping skills *actually* fight needs an agent reading the set in context. The
script's job is to hand that agent a ranked, evidence-backed shortlist instead of 40
files. (Same discipline as citation_lint: deterministic surface + explicit handoff.)

Usage:
  python3 scripts/skill_library_audit.py                 # audit this standalone repo
  python3 scripts/skill_library_audit.py --root DIR      # audit a specific library
  python3 scripts/skill_library_audit.py --overlap 0.5   # stricter overlap threshold

Exit 0 = no hard defect (overlaps are reported as REVIEW, not failure).
Exit 1 = a hard defect: missing/empty description, over-1024 description, or total
         budget over the truncation ceiling.
"""

from __future__ import annotations

import argparse
import re
import sys
from itertools import combinations
from pathlib import Path

sys.dont_write_bytecode = True

from frontmatter import FrontmatterError, parse_frontmatter_file

# Default heuristic budget for the metadata block that holds all skill descriptions.
# The real budget and truncation behavior are HOST-SPECIFIC. This default is only a
# review heuristic; pass --budget when the target host publishes or exposes a limit.
BUDGET_CEILING = 15000
DESC_LIMIT = 1024  # per-skill hard limit
MAX_DEPTH = 6      # deep enough for plugin caches (<provider>/<publisher>/<plugin>/<hash>/skills/<name>)
SKIP_DIRS = {"node_modules", ".git", "__pycache__", ".venv", "venv", "dist", "build"}

# Stopwords that carry no trigger signal — every skill description has these.
STOP = {
    "use", "when", "the", "for", "and", "or", "to", "a", "an", "of", "in", "on",
    "with", "this", "that", "is", "are", "be", "it", "as", "by", "from", "skill",
    "skills", "user", "users", "asks", "ask", "want", "wants", "need", "needs",
    "not", "you", "your", "if", "into", "via", "any", "etc", "using", "used",
    "其", "的", "了", "和", "或", "把", "在", "做", "用", "时", "这", "那", "等",
    "一个", "一下", "帮我", "如果", "以及", "进行", "或者",
}

CJK = r"\u4e00-\u9fff\u3040-\u30ff\uac00-\ud7af"


def tokenize(text: str) -> set[str]:
    """Trigger vocabulary = ascii word tokens (len>=3) + CJK character bigrams."""
    text = text.lower()
    tokens: set[str] = set()
    for w in re.findall(r"[a-z][a-z0-9_-]{2,}", text):
        if w not in STOP:
            tokens.add(w)
    for run in re.findall(f"[{CJK}]+", text):
        if len(run) == 1:
            if run not in STOP:
                tokens.add(run)
        else:
            for i in range(len(run) - 1):
                bg = run[i : i + 2]
                if bg not in STOP:
                    tokens.add(bg)
    return tokens


def parse_frontmatter(skill_md: Path) -> dict[str, str]:
    """Read metadata through the shared dependency-free parser."""
    try:
        return parse_frontmatter_file(skill_md)
    except (OSError, FrontmatterError):
        return {}


def find_skills(root: Path) -> list[tuple[str, Path]]:
    """Every SKILL.md under root, recursively up to MAX_DEPTH.

    One-level scanning misses real skills — hosts also load nested layouts
    (`.system/<name>/SKILL.md`, plugin caches, project `.cursor/skills/`).
    A "clean" verdict that never saw those skills is a false clean.
    Hidden directories are included; vendored/build dirs are skipped.
    """
    found: list[tuple[str, Path]] = []
    visited: set[tuple[int, int]] = set()

    def walk(d: Path, depth: int) -> None:
        if d.is_symlink():
            return
        try:
            stat = d.stat()
        except (OSError, PermissionError):
            return
        identity = (stat.st_dev, stat.st_ino)
        if identity in visited:
            return
        visited.add(identity)
        sm = d / "SKILL.md"
        if sm.is_file() and not sm.is_symlink():
            found.append((d.name if d != root else root.name, sm))
            return  # a SKILL.md nested under another skill (vendored copy) is not loaded
        if depth >= MAX_DEPTH:
            return
        try:
            children = sorted(
                p for p in d.iterdir() if not p.is_symlink() and p.is_dir()
            )
        except (OSError, PermissionError):
            return
        for child in children:
            if child.name in SKIP_DIRS:
                continue
            walk(child, depth + 1)

    walk(root, 0)
    return found


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="skill_library_audit.py", description=__doc__)
    default_root = Path(__file__).resolve().parent.parent
    p.add_argument("--root", action="append", default=None,
                   help="library dir to scan (repeatable — pass every root the host "
                        "actually loads: user skills, project skills, plugin caches); "
                        "default: standalone repository root")
    p.add_argument("--budget", type=int, default=BUDGET_CEILING,
                   help=f"metadata budget ceiling in chars (default {BUDGET_CEILING}; "
                        "heuristic — the real budget is host-specific and dynamic)")
    p.add_argument("--overlap", type=float, default=0.40,
                   help="overlap-coefficient threshold to flag a pair (default 0.40)")
    p.add_argument("--jaccard", type=float, default=0.25,
                   help="jaccard threshold to flag a pair (default 0.25)")
    p.add_argument("--top", type=int, default=20, help="max overlapping pairs to print")
    args = p.parse_args(argv)

    roots = [Path(r).resolve() for r in (args.root or [str(default_root)])]
    for r in roots:
        if not r.is_dir():
            print(f"error: root not found: {r}", file=sys.stderr)
            return 2

    skills: list[tuple[str, Path]] = []
    seen_paths: set[Path] = set()
    for r in roots:
        for name, sm in find_skills(r):
            if sm not in seen_paths:
                seen_paths.add(sm)
                skills.append((name, sm))
    if not skills:
        print(f"error: no SKILL.md found under {', '.join(map(str, roots))}", file=sys.stderr)
        return 2

    fail = 0
    review = 0
    print(f"== skill library audit: {len(skills)} skill(s) under "
          f"{', '.join(map(str, roots))} (recursive, depth {MAX_DEPTH}) ==\n")

    # --- 1 & 2: per-skill description facts ------------------------------------
    metas: list[tuple[str, str, set[str]]] = []  # (name, description, tokens)
    total_budget = 0
    missing: list[str] = []
    overlong: list[tuple[str, int]] = []
    heavy: list[tuple[str, int]] = []

    name_locations: dict[str, list[Path]] = {}
    for dirname, sm in skills:
        fm = parse_frontmatter(sm)
        name = fm.get("name", dirname) or dirname
        name_locations.setdefault(name, []).append(sm)
        desc = fm.get("description", "").strip()
        if not desc:
            missing.append(name)
            continue
        dl = len(desc)
        total_budget += len(name) + dl
        if dl > DESC_LIMIT:
            overlong.append((name, dl))
        elif dl > 500:
            heavy.append((name, dl))
        metas.append((name, desc, tokenize(desc)))

    budget = args.budget
    risk = int(budget * 0.8)
    print("-- description budget (heuristic — the real ceiling is host-specific & dynamic) --")
    flag = ""
    if total_budget > budget:
        flag = "  <- OVER CEILING: the host will drop/truncate some descriptions"
        fail += 1
    elif total_budget > risk:
        flag = "  <- risk zone (approaching the ceiling)"
        review += 1
    print(f"  total name+description chars: {total_budget} "
          f"(risk {risk} / ceiling {budget}; tune with --budget){flag}\n")

    dupes = {n: ps for n, ps in name_locations.items() if len(ps) > 1}
    if dupes:
        fail += 1
        print(f"-- FAIL: {len(dupes)} duplicate skill name(s) — the host resolves one, the rest are shadowed --")
        for n, ps in sorted(dupes.items()):
            print(f"  {n}:")
            for path in ps:
                print(f"    {path}")
        print()

    if missing:
        fail += 1
        print(f"-- FAIL: {len(missing)} skill(s) with no/empty description (cannot route) --")
        for n in missing:
            print(f"  {n}")
        print()
    if overlong:
        fail += 1
        print(f"-- FAIL: {len(overlong)} description(s) over the {DESC_LIMIT}-char limit --")
        for n, dl in overlong:
            print(f"  {n}: {dl} chars")
        print()
    if heavy:
        print(f"-- note: {len(heavy)} description(s) > 500 chars (trim toward 150-400) --")
        for n, dl in sorted(heavy, key=lambda x: -x[1]):
            print(f"  {n}: {dl} chars")
        print()

    # --- 3: pairwise trigger overlap ------------------------------------------
    pairs: list[tuple[float, float, str, str, list[str]]] = []
    for (na, _da, ta), (nb, _db, tb) in combinations(metas, 2):
        if not ta or not tb:
            continue
        inter = ta & tb
        if not inter:
            continue
        overlap = len(inter) / min(len(ta), len(tb))
        jacc = len(inter) / len(ta | tb)
        if overlap >= args.overlap or jacc >= args.jaccard:
            shared = sorted(inter, key=lambda w: (-len(w), w))[:8]
            pairs.append((overlap, jacc, na, nb, shared))

    pairs.sort(key=lambda x: (-x[0], -x[1]))
    print("-- trigger overlap (collision candidates — a property of the SET) --")
    if not pairs:
        print("  none above threshold — no obvious cross-skill trigger competition.\n")
    else:
        review += len(pairs)
        print(f"  {len(pairs)} candidate pair(s); review the top ones for real competition:\n")
        for overlap, jacc, na, nb, shared in pairs[: args.top]:
            print(f"  overlap {overlap:.2f} jaccard {jacc:.2f}  {na}  <>  {nb}")
            print(f"      shared triggers: {', '.join(shared)}")
        if len(pairs) > args.top:
            print(f"  ... and {len(pairs) - args.top} more (raise --overlap to narrow)")
        print()

    # --- verdict --------------------------------------------------------------
    print(f"Result: {fail} FAIL / {review} REVIEW / {len(skills)} skill(s)")
    if fail:
        print("Action: fix the FAIL items — they are deterministic routing breakers "
              "(no description = invisible; over budget = truncated; over 1024 = rejected).")
        return 1
    if review:
        print("Action: no hard breakers. REVIEW the overlapping pairs — collision is a "
              "property of the set, so confirm in context: do they actually compete on a "
              "real prompt? If so, add a 'Not for X (use Y)' exclusion to the broader one, "
              "or rename one so the trigger diverges. (Final judgment needs an agent, not this script.)")
        return 0
    print("Action: library is clean — budget under ceiling, all routable, no trigger overlap.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
