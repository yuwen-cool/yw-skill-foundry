#!/usr/bin/env python3
"""trigger_eval.py — make YW SkillFoundry's trigger evaluation runnable.

YW SkillFoundry uses a 3-hit + 3-miss routing test (references/description-and-triggering.md)
and a 4-layer eval (references/quality-assurance.md). This turns the Routing layer from
prose into something you actually run, so it stops "just sitting there."

Subcommands
-----------
  lint       Deterministic checks on a skill's frontmatter `description` (the Layer-0
             routing surface). No model needed. Catches the real CSO defects.
  worksheet  Print the description + fixture prompts WITHOUT their labels, in shuffled
             order, for judging in a FRESH context. The model in the loop is the agent
             itself — which is exactly how routing happens in production.
  score      Compare the agent's judgments against fixture ground truth. Reports routing
             accuracy and maps every miss to a targeted fix.

No third-party dependencies (stdlib only). Requires Python 3.10+ on macOS or
Linux; WSL is expected to work but is not currently CI-verified.

Fixture format (JSONL, one case per line; `id` = line index, 0-based):
  {"prompt": "帮我写一个新的 skill", "expect": "trigger", "kind": "exact"}
  {"prompt": "帮我写一篇文章",        "expect": "no",      "kind": "near_neighbor", "holdout": true}

Optional `holdout` field (default false) prevents overfitting: tune the description
against the TRAIN cases only (`worksheet --phase train`), then validate on the
unseen HOLDOUT cases (`worksheet --phase holdout`). `score` reports train/holdout
accuracy separately. A single-phase run gates that phase; a combined run requires
both TRAIN and HOLDOUT to pass, so a perfect holdout cannot hide a broken training
set. `score` also enforces COMPLETENESS: judging only part of a phase is
rejected (exit 2), so a partial submission can never fake a pass; duplicate or
out-of-range ids are rejected the same way.

Judgments format (JSONL the agent writes after the worksheet):
  {"id": 0, "decision": "trigger"}
  {"id": 1, "decision": "no"}
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import random
import re
import sys
import tempfile
from pathlib import Path

sys.dont_write_bytecode = True

from frontmatter import FrontmatterError, parse_frontmatter_file

VALID_LABELS = {"trigger", "no"}
RESULT_SCHEMA = "yw-skill-foundry.routing-result/v1"


# --------------------------------------------------------------------------- #
# helpers
# --------------------------------------------------------------------------- #
def _eprint(*args: object) -> None:
    print(*args, file=sys.stderr)


def _digest(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def _prepare_new_output(path: Path, label: str) -> Path:
    if path.is_symlink():
        _eprint(f"error: {label} must not be a symlink: {path}")
        sys.exit(2)
    if path.exists():
        _eprint(f"error: {label} already exists; refusing to overwrite: {path}")
        sys.exit(2)
    try:
        parent = path.parent.resolve(strict=True)
    except OSError as exc:
        _eprint(f"error: cannot resolve {label} parent for {path}: {exc}")
        sys.exit(2)
    if not parent.is_dir():
        _eprint(f"error: {label} parent is not a directory: {parent}")
        sys.exit(2)
    return parent / path.name


def _atomic_write_text(path: Path, text: str) -> None:
    fd, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.link(temp_name, path)
    finally:
        if os.path.exists(temp_name):
            os.unlink(temp_name)


def _input_record(path: Path, report_path: Path) -> dict[str, str]:
    resolved = path.resolve()
    report_parent = report_path.parent.resolve()
    try:
        display = resolved.relative_to(report_parent).as_posix()
    except ValueError:
        _eprint(
            f"error: report input must stay under the report directory: {resolved}"
        )
        sys.exit(2)
    return {
        "path": display,
        "sha256": _digest(resolved),
    }


def _write_score_report(
    args: argparse.Namespace,
    passed: bool,
    metrics: dict[str, object],
) -> None:
    if not args.report:
        return
    report_path = _prepare_new_output(Path(args.report), "--report")
    fixture = Path(args.fixture)
    judgments = Path(args.judgments)
    worksheet = Path(args.worksheet)
    input_paths = (fixture, judgments, worksheet)
    if any(report_path.resolve() == path.resolve() for path in input_paths):
        _eprint("error: --report must not overwrite fixture, judgments, or worksheet")
        sys.exit(2)
    report = {
        "schema": RESULT_SCHEMA,
        "inputs": {
            "fixture": _input_record(fixture, report_path),
            "judgments": _input_record(judgments, report_path),
            "worksheet": _input_record(worksheet, report_path),
        },
        "min_accuracy": args.min_accuracy,
        "passed": passed,
        **metrics,
    }
    try:
        _atomic_write_text(
            report_path,
            json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        )
    except OSError as exc:
        _eprint(f"error: cannot create report at {report_path}: {exc}")
        sys.exit(2)


def read_frontmatter(skill_dir: Path) -> dict[str, str]:
    """Parse <skill_dir>/SKILL.md using the shared metadata parser."""
    skill_file = skill_dir / "SKILL.md"
    if not skill_file.is_file():
        _eprint(f"error: SKILL.md not found at {skill_file}")
        sys.exit(2)
    try:
        return parse_frontmatter_file(skill_file)
    except (OSError, FrontmatterError) as exc:
        _eprint(f"error: {exc}")
        sys.exit(2)


# Agent Skills spec: 1-64 chars, lowercase letters / digits / hyphens,
# no leading/trailing hyphen, no consecutive hyphens.
NAME_RX = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")


def load_fixture(path: Path) -> list[dict]:
    if not path.is_file():
        _eprint(f"error: fixture not found at {path}")
        sys.exit(2)
    cases: list[dict] = []
    for lineno, raw in enumerate(path.read_text(encoding="utf-8").splitlines()):
        raw = raw.strip()
        if not raw or raw.startswith("#"):
            continue
        try:
            obj = json.loads(raw)
        except json.JSONDecodeError as exc:
            _eprint(f"error: fixture line {lineno + 1} is not valid JSON: {exc}")
            sys.exit(2)
        if "prompt" not in obj or obj.get("expect") not in VALID_LABELS:
            _eprint(
                f"error: fixture line {lineno + 1} needs 'prompt' and "
                f"'expect' in {sorted(VALID_LABELS)}"
            )
            sys.exit(2)
        obj.setdefault("kind", "unspecified")
        obj["holdout"] = bool(obj.get("holdout", False))
        cases.append(obj)
    if not cases:
        _eprint("error: fixture has no usable cases")
        sys.exit(2)
    return cases


def has_cjk(s: str) -> bool:
    return any("\u4e00" <= ch <= "\u9fff" for ch in s)


def has_latin(s: str) -> bool:
    return any("a" <= ch.lower() <= "z" for ch in s)


# --------------------------------------------------------------------------- #
# lint
# --------------------------------------------------------------------------- #
# Hard leak: sequenced process language ("step 1", "first X then Y", ordered
# dispatch) — a description carrying the recipe makes the agent skip the body.
WORKFLOW_LEAK_HARD = re.compile(
    r"\bstep\s*\d|first\b.*\bthen\b|\bdispatch(es|ed)?\b.*\b(per|each)\b"
    r"|execute.*\border\b|步骤\s*\d|先.*然后",
    re.IGNORECASE | re.DOTALL,
)
# Soft leak: process nouns that are usually a leak but can be a legitimate
# domain keyword ("Use when auditing workflow design"). Human-review, not auto-fail.
WORKFLOW_LEAK_SOFT = re.compile(r"\bworkflow\b|\bpipeline\b", re.IGNORECASE)


def cmd_lint(args: argparse.Namespace) -> int:
    skill_dir = Path(args.skill).resolve()
    fm = read_frontmatter(skill_dir)
    desc = fm.get("description", "")
    name = fm.get("name", skill_dir.name)

    fails: list[str] = []
    warns: list[str] = []
    infos: list[str] = []

    if "name" not in fm:
        fails.append("no `name:` field in frontmatter (required by the Agent Skills spec)")
    elif not NAME_RX.match(name) or len(name) > 64:
        fails.append(
            f"name {name!r} violates the spec: 1-64 chars, lowercase letters/digits/hyphens, "
            "no leading/trailing/consecutive hyphens"
        )
    elif name != skill_dir.name:
        fails.append(
            f"name {name!r} must match its parent directory {skill_dir.name!r}"
        )

    if "description" not in fm:
        fails.append("no `description:` field in frontmatter")

    n = len(desc)
    if n == 0 and "description" in fm:
        fails.append("description is empty")
    elif n > 1024:
        fails.append(f"description is {n} chars (> 1024 hard limit; Layer-0 cost)")
    elif n > 500:
        warns.append(f"description is {n} chars (sweet spot 200-400; > 500 is heavy)")
    else:
        infos.append(f"description length {n} chars")

    low = desc.lower()
    if not (low.startswith("use when") or "use when" in low or "use for" in low):
        warns.append(
            'description does not contain "Use when ..." — '
            "state trigger conditions, not a capability summary (rule 1)"
        )

    if WORKFLOW_LEAK_HARD.search(desc):
        fails.append(
            "description contains sequenced workflow language — the agent may follow "
            "the summary and skip the body (rule 5)"
        )
    elif WORKFLOW_LEAK_SOFT.search(desc):
        warns.append(
            'description contains "workflow"/"pipeline" — fine if it is a domain keyword '
            '("Use when auditing workflow design"), a leak if it summarizes the process (rule 5)'
        )

    if not ("not for" in low or "不要" in desc or "不用于" in desc):
        infos.append(
            'no negative trigger ("Not for X") — add one if confusion with a '
            "neighbor skill is plausible (rule 6)"
        )

    if not (has_cjk(desc) and has_latin(desc)):
        message = (
            "description is not bilingual — add both Chinese and English only when "
            "the skill's real user population needs both"
        )
        if args.require_bilingual:
            fails.append(f"{message} (--require-bilingual enabled)")
        else:
            infos.append(message)

    print(f"== lint: {name} ==")
    print(f"description: {desc!r}\n")
    for f in fails:
        print(f"FAIL  {f}")
    for w in warns:
        print(f"WARN  {w}")
    for i in infos:
        print(f"INFO  {i}")
    print(f"\nResult: {len(fails)} FAIL / {len(warns)} WARN / {len(infos)} INFO")
    if fails:
        print("Action: fix all FAIL items — they block reliable routing.")
        return 1
    print("Action: review WARN/INFO; no blocking defects in the routing surface.")
    return 0


# --------------------------------------------------------------------------- #
# worksheet
# --------------------------------------------------------------------------- #
def cmd_worksheet(args: argparse.Namespace) -> int:
    skill_dir = Path(args.skill).resolve()
    fm = read_frontmatter(skill_dir)
    desc = fm.get("description", "")
    name = fm.get("name", skill_dir.name)
    if not desc:
        _eprint("error: description is empty — fix `lint` failures before judging")
        sys.exit(2)
    cases = load_fixture(Path(args.fixture))

    phase = args.phase

    def in_phase(case: dict) -> bool:
        if phase == "all":
            return True
        if phase == "holdout":
            return case["holdout"]
        return not case["holdout"]  # train

    # ids stay anchored to the full-fixture index so `score` lines up regardless of phase
    order = [i for i in range(len(cases)) if in_phase(cases[i])]
    if not order:
        _eprint(f"error: no cases in phase {phase!r} (mark some with \"holdout\": true)")
        sys.exit(2)
    rng = random.Random(args.seed)
    rng.shuffle(order)

    print("=" * 70)
    print(f"TRIGGER WORKSHEET [phase={phase}] — judge in a FRESH context (no body, no labels).")
    print("=" * 70)
    print(
        "\nDecide, for each prompt, whether the skill below SHOULD activate based\n"
        "ONLY on its description. Do not read the SKILL.md body. Then write a\n"
        "judgments file (JSONL), one line per prompt:\n"
        '  {"id": <N>, "decision": "trigger"|"no"}\n'
        f"and score it with:  python3 {Path(__file__).name} score "
        f"--fixture {args.fixture} --judgments <file>\n"
    )
    print(f"SKILL name: {name}")
    print(f"SKILL description:\n  {desc}\n")
    print("-" * 70)
    for display_pos, idx in enumerate(order, start=1):
        print(f"[id={idx}]  {cases[idx]['prompt']}")
    print("-" * 70)
    print(f"{len(order)} prompts (phase={phase}). Judge each, then run `score`.")
    return 0


# --------------------------------------------------------------------------- #
# score
# --------------------------------------------------------------------------- #
def cmd_score(args: argparse.Namespace) -> int:
    if args.report and not args.worksheet:
        _eprint("error: --report requires --worksheet so the exact judge input is bound")
        return 2
    cases = load_fixture(Path(args.fixture))
    jpath = Path(args.judgments)
    if not jpath.is_file():
        _eprint(f"error: judgments file not found at {jpath}")
        sys.exit(2)

    judgments: dict[int, str] = {}
    for lineno, raw in enumerate(jpath.read_text(encoding="utf-8").splitlines()):
        raw = raw.strip()
        if not raw or raw.startswith("#"):
            continue
        try:
            obj = json.loads(raw)
            jid = int(obj["id"])
            decision = obj["decision"]
        except (json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
            _eprint(f"error: judgments line {lineno + 1} is malformed "
                    f'(need {{"id": <int>, "decision": "trigger"|"no"}}): {exc}')
            sys.exit(2)
        if decision not in VALID_LABELS:
            _eprint(f"error: judgments line {lineno + 1}: bad decision {decision!r}")
            sys.exit(2)
        if jid < 0 or jid >= len(cases):
            _eprint(f"error: judgments line {lineno + 1}: id {jid} is out of range "
                    f"(fixture has ids 0..{len(cases) - 1})")
            sys.exit(2)
        if jid in judgments:
            _eprint(f"error: judgments line {lineno + 1}: duplicate id {jid} — "
                    "each case must be judged exactly once")
            sys.exit(2)
        judgments[jid] = decision

    # only score what was judged, so a single-phase worksheet (train OR holdout) can be scored
    judged_ids = [i for i in range(len(cases)) if i in judgments]
    if not judged_ids:
        _eprint("error: judgments cover none of the fixture's case ids")
        sys.exit(2)
    unjudged = [i for i in range(len(cases)) if i not in judgments]

    # completeness gate: judging SOME holdout cases must never count as passing the
    # holdout — a partial submission could otherwise fake a 100% holdout pass.
    all_holdout = [i for i in range(len(cases)) if cases[i]["holdout"]]
    judged_holdout = [i for i in all_holdout if i in judgments]
    if judged_holdout and len(judged_holdout) < len(all_holdout):
        missing = [i for i in all_holdout if i not in judgments]
        _eprint(f"error: partial holdout coverage — judged {len(judged_holdout)}/"
                f"{len(all_holdout)} holdout case(s); missing ids {missing}. "
                "Judge ALL holdout cases (worksheet --phase holdout) or none.")
        sys.exit(2)
    all_train = [i for i in range(len(cases)) if not cases[i]["holdout"]]
    judged_train = [i for i in all_train if i in judgments]
    if judged_train and len(judged_train) < len(all_train):
        missing = [i for i in all_train if i not in judgments]
        _eprint(f"error: partial train coverage — judged {len(judged_train)}/"
                f"{len(all_train)} train case(s); missing ids {missing}. "
                "Judge ALL train cases (worksheet --phase train) or none.")
        sys.exit(2)

    def tally(ids: list[int]) -> tuple[int, int, list[dict], list[dict]]:
        correct = 0
        under: list[dict] = []  # expected trigger, judged no
        over: list[dict] = []   # expected no, judged trigger
        for i in ids:
            expect = cases[i]["expect"]
            got = judgments[i]
            if got == expect:
                correct += 1
            elif expect == "trigger":
                under.append({**cases[i], "id": i})
            else:
                over.append({**cases[i], "id": i})
        return correct, len(ids), under, over

    train_ids = [i for i in judged_ids if not cases[i]["holdout"]]
    holdout_ids = [i for i in judged_ids if cases[i]["holdout"]]

    o_correct, o_total, under_trigger, over_trigger = tally(judged_ids)
    acc = o_correct / o_total * 100.0
    phase_metrics: dict[str, dict[str, int]] = {
        "overall": {"correct": o_correct, "total": o_total}
    }

    print("== routing score ==")
    print(f"overall : {o_correct}/{o_total} = {acc:.0f}%")
    train_acc = None
    if train_ids:
        tc, tt, _, _ = tally(train_ids)
        train_acc = tc / tt * 100.0
        phase_metrics["train"] = {"correct": tc, "total": tt}
        print(f"train   : {tc}/{tt} = {train_acc:.0f}%")
    holdout_acc = None
    if holdout_ids:
        hc, ht, _, _ = tally(holdout_ids)
        holdout_acc = hc / ht * 100.0
        phase_metrics["holdout"] = {"correct": hc, "total": ht}
        print(f"holdout : {hc}/{ht} = {holdout_acc:.0f}%   <- the honest test (unseen while tuning)")
    if unjudged:
        print(f"note    : {len(unjudged)} fixture case(s) not judged this run: {unjudged}")
    print()

    # per-family (kind) breakdown — a regression hiding in one near-miss family
    # (e.g. translate_only, explain_only) is invisible in the overall number alone.
    by_kind: dict[str, list[int]] = {}
    for i in judged_ids:
        by_kind.setdefault(cases[i].get("kind", "untagged"), []).append(i)
    if len(by_kind) > 1:
        print("by family (kind):")
        for kind in sorted(by_kind):
            kc, kt, _, _ = tally(by_kind[kind])
            flag = "" if kc == kt else "  <- MISS"
            print(f"  {kind:<22} {kc}/{kt} = {kc / kt * 100:.0f}%{flag}")
        print()
    kind_metrics = {
        kind: {
            "correct": tally(ids)[0],
            "total": tally(ids)[1],
        }
        for kind, ids in sorted(by_kind.items())
    }

    if under_trigger:
        print("UNDER-TRIGGER (should activate, judged no) — description too NARROW:")
        for c in under_trigger:
            print(f"  [id={c['id']}, {c['kind']}] {c['prompt']}")
        print("  fix: add the missing natural-language / synonym / error-string "
              "keywords for these phrasings (description-and-triggering.md §触发词设计)\n")

    if over_trigger:
        print("OVER-TRIGGER (should NOT activate, judged trigger) — description too BROAD:")
        for c in over_trigger:
            print(f"  [id={c['id']}, {c['kind']}] {c['prompt']}")
        print("  fix: tighten wording or add a `Not for X (use Y instead)` exclusion "
              "(description-and-triggering.md rule 6)\n")

    min_acc = args.min_accuracy
    if not 0.0 <= min_acc <= 100.0:
        _eprint(f"error: --min-accuracy must be within 0-100 (got {min_acc})")
        sys.exit(2)
    # A single-phase worksheet gates that phase. A combined worksheet must pass
    # BOTH phases: holdout is the honest generalization test, but it must not hide
    # a description that already fails known training cases.
    gates: list[tuple[str, float]] = []
    if train_acc is not None:
        gates.append(("train", train_acc))
    if holdout_acc is not None:
        gates.append(("holdout", holdout_acc))
    if not gates:
        gates.append(("overall", acc))

    failed_gates = [(name, value) for name, value in gates if value + 1e-9 < min_acc]
    report_metrics = {
        "phases": phase_metrics,
        "by_kind": kind_metrics,
        "under_trigger_ids": [item["id"] for item in under_trigger],
        "over_trigger_ids": [item["id"] for item in over_trigger],
    }
    if failed_gates:
        details = ", ".join(f"{name} {value:.0f}%" for name, value in failed_gates)
        extra = ""
        if gates == [("train", train_acc)]:
            extra = ' (tip: mark unseen cases "holdout": true and validate them separately)'
        print(f"Action: routing FAILED — {details} < {min_acc:.0f}%. Fix the "
              f"description, re-run the worksheet in a fresh context, and score again.{extra}")
        _write_score_report(args, False, report_metrics)
        return 1
    passed = ", ".join(f"{name} {value:.0f}%" for name, value in gates)
    print(f"Action: routing PASSED — {passed} >= {min_acc:.0f}%.")
    _write_score_report(args, True, report_metrics)
    return 0


# --------------------------------------------------------------------------- #
# main
# --------------------------------------------------------------------------- #
def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        prog="trigger_eval.py",
        description="Runnable trigger / routing evaluation for YW SkillFoundry.",
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    pl = sub.add_parser("lint", help="deterministic checks on the frontmatter description")
    pl.add_argument("--skill", default=".", help="skill directory (contains SKILL.md)")
    pl.add_argument(
        "--require-bilingual",
        action="store_true",
        help="fail unless description contains both CJK and Latin trigger text",
    )
    pl.set_defaults(func=cmd_lint)

    pw = sub.add_parser("worksheet", help="emit shuffled, unlabeled prompts for fresh-context judging")
    pw.add_argument("--skill", default=".", help="skill directory (contains SKILL.md)")
    pw.add_argument("--fixture", required=True, help="path to trigger_cases JSONL")
    pw.add_argument("--seed", type=int, default=None, help="shuffle seed (for reproducible order)")
    pw.add_argument("--phase", choices=("train", "holdout", "all"), default="all",
                    help="which cases to emit: train (tune on these), holdout (validate on these), or all")
    pw.set_defaults(func=cmd_worksheet)

    ps = sub.add_parser("score", help="score judgments against fixture ground truth")
    ps.add_argument("--fixture", required=True, help="path to trigger_cases JSONL")
    ps.add_argument("--judgments", required=True, help="path to judgments JSONL the agent wrote")
    ps.add_argument("--worksheet", help="exact unlabeled worksheet shown to the judge")
    ps.add_argument("--report", help="write a hash-bound routing result JSON")
    ps.add_argument("--min-accuracy", type=float, default=100.0, help="pass threshold (default 100)")
    ps.set_defaults(func=cmd_score)

    args = p.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
