#!/usr/bin/env python3
"""Evaluate deterministic and explicitly graded output-contract checks.

Contract format:
{
  "schema": "yw-skill-foundry.contract/v1",
  "checks": [
    {"id": "header", "type": "contains", "value": "## Findings"},
    {"id": "citation", "type": "regex", "pattern": "[A-Za-z0-9_./-]+:\\d+"},
    {"id": "no-todo", "type": "not_regex", "pattern": "\\bTODO\\b"}
  ],
  "manual_checks": [
    {"id": "actionable", "description": "Every finding names a failure path."}
  ]
}

Manual result format:
{"actionable": {"passed": true, "evidence": "Finding 1 names input X."}}
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import tempfile
from pathlib import Path
from typing import Any


SCHEMA = "yw-skill-foundry.contract/v1"
LEGACY_SCHEMAS = {
    "skill-foundry.contract/v1",
    "skill-craft.contract/v1",
}
RESULT_SCHEMA = "yw-skill-foundry.contract-result/v2"
CHECK_TYPES = {"contains", "not_contains", "regex", "not_regex", "json_fields"}


class ContractError(ValueError):
    pass


def prepare_new_output(path: Path, label: str) -> Path:
    if path.is_symlink():
        raise ContractError(f"{label} must not be a symlink: {path}")
    if path.exists():
        raise ContractError(f"{label} already exists; refusing to overwrite: {path}")
    try:
        parent = path.parent.resolve(strict=True)
    except OSError as exc:
        raise ContractError(f"cannot resolve {label} parent for {path}: {exc}") from exc
    if not parent.is_dir():
        raise ContractError(f"{label} parent is not a directory: {parent}")
    return parent / path.name


def atomic_write_text(path: Path, text: str) -> None:
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


def load_json(path: Path, label: str) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise ContractError(f"cannot read {label} at {path}: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise ContractError(f"{label} is invalid JSON: {exc}") from exc


def require_string(obj: dict[str, Any], key: str, check_id: str) -> str:
    value = obj.get(key)
    if not isinstance(value, str) or not value:
        raise ContractError(f"check {check_id!r} needs non-empty string {key!r}")
    return value


def resolve_json_path(value: Any, path: str) -> tuple[bool, Any]:
    current = value
    for part in path.split("."):
        if isinstance(current, dict) and part in current:
            current = current[part]
        elif isinstance(current, list) and part.isdigit() and int(part) < len(current):
            current = current[int(part)]
        else:
            return False, None
    return True, current


def digest(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def input_record(path: Path, report_path: Path | None) -> dict[str, str]:
    resolved = path.resolve()
    if report_path is not None:
        report_parent = report_path.parent.resolve()
        try:
            display = resolved.relative_to(report_parent).as_posix()
        except ValueError as exc:
            raise ContractError(
                f"report input must stay under the report directory: {resolved}"
            ) from exc
    else:
        display = path.name
    return {"path": display, "sha256": digest(resolved)}


def validate_contract(contract: Any) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    if not isinstance(contract, dict):
        raise ContractError("contract root must be an object")
    if contract.get("schema") not in {SCHEMA, *LEGACY_SCHEMAS}:
        raise ContractError(
            f"contract schema must be {SCHEMA!r} "
            f"(legacy accepted: {', '.join(sorted(LEGACY_SCHEMAS))})"
        )

    checks = contract.get("checks", [])
    manual = contract.get("manual_checks", [])
    if not isinstance(checks, list) or not isinstance(manual, list):
        raise ContractError("checks and manual_checks must be arrays")
    if not checks and not manual:
        raise ContractError("contract needs at least one check")

    seen: set[str] = set()
    for collection, manual_mode in ((checks, False), (manual, True)):
        for item in collection:
            if not isinstance(item, dict):
                raise ContractError("every check must be an object")
            check_id = require_string(item, "id", "<unknown>")
            if check_id in seen:
                raise ContractError(f"duplicate check id {check_id!r}")
            seen.add(check_id)
            if manual_mode:
                require_string(item, "description", check_id)
                continue
            check_type = require_string(item, "type", check_id)
            if check_type not in CHECK_TYPES:
                raise ContractError(
                    f"check {check_id!r} has unsupported type {check_type!r}"
                )
            if check_type in {"contains", "not_contains"}:
                require_string(item, "value", check_id)
            elif check_type in {"regex", "not_regex"}:
                pattern = require_string(item, "pattern", check_id)
                try:
                    re.compile(pattern)
                except re.error as exc:
                    raise ContractError(f"check {check_id!r} has invalid regex: {exc}") from exc
            elif check_type == "json_fields":
                paths = item.get("paths")
                if not isinstance(paths, list) or not paths or not all(
                    isinstance(path, str) and path for path in paths
                ):
                    raise ContractError(
                        f"check {check_id!r} needs a non-empty string array 'paths'"
                    )
            if check_type in {"contains", "regex"}:
                minimum = item.get("min_matches", 1)
                maximum = item.get("max_matches")
                if not isinstance(minimum, int) or isinstance(minimum, bool) or minimum < 0:
                    raise ContractError(
                        f"check {check_id!r} min_matches must be a non-negative integer"
                    )
                if maximum is not None and (
                    not isinstance(maximum, int)
                    or isinstance(maximum, bool)
                    or maximum < minimum
                ):
                    raise ContractError(
                        f"check {check_id!r} max_matches must be an integer >= min_matches"
                    )
    return checks, manual


def run_check(
    check: dict[str, Any], text: str, parsed_json: Any | None
) -> tuple[bool, str]:
    check_type = check["type"]
    if check_type == "contains":
        count = text.count(check["value"])
        minimum = int(check.get("min_matches", 1))
        maximum = check.get("max_matches")
        passed = count >= minimum and (
            maximum is None or count <= int(maximum)
        )
        expected = f">= {minimum}" if maximum is None else f"{minimum}..{maximum}"
        return passed, f"found {count}, required {expected}"
    if check_type == "not_contains":
        count = text.count(check["value"])
        return count == 0, f"found {count}, required 0"
    if check_type in {"regex", "not_regex"}:
        count = len(re.findall(check["pattern"], text, flags=re.MULTILINE))
        if check_type == "not_regex":
            return count == 0, f"matched {count}, required 0"
        minimum = int(check.get("min_matches", 1))
        maximum = check.get("max_matches")
        passed = count >= minimum and (
            maximum is None or count <= int(maximum)
        )
        expected = f">= {minimum}" if maximum is None else f"{minimum}..{maximum}"
        return passed, f"matched {count}, required {expected}"
    if check_type == "json_fields":
        if parsed_json is None:
            return False, "output is not valid JSON"
        missing = [
            path for path in check["paths"] if not resolve_json_path(parsed_json, path)[0]
        ]
        return not missing, (
            "all paths present" if not missing else f"missing paths: {', '.join(missing)}"
        )
    raise AssertionError(f"unhandled check type {check_type}")


def evaluate(args: argparse.Namespace) -> int:
    report_path: Path | None = None
    if args.report:
        try:
            report_path = prepare_new_output(args.report, "--report")
        except ContractError as exc:
            print(f"ERROR  {exc}", file=sys.stderr)
            return 2
    if args.report and any(
        args.report.resolve() == path.resolve()
        for path in (args.contract, args.output, args.manual_results)
        if path is not None
    ):
        print(
            "ERROR  --report must not overwrite contract, output, or manual-results input",
            file=sys.stderr,
        )
        return 2
    try:
        contract = load_json(args.contract, "contract")
        checks, manual_checks = validate_contract(contract)
        text = args.output.read_text(encoding="utf-8")
    except (ContractError, OSError, UnicodeError) as exc:
        print(f"ERROR  {exc}", file=sys.stderr)
        return 2

    try:
        parsed_json = json.loads(text)
    except json.JSONDecodeError:
        parsed_json = None

    results: list[dict[str, Any]] = []
    failed = 0
    for check in checks:
        passed, evidence = run_check(check, text, parsed_json)
        failed += int(not passed)
        results.append(
            {
                "id": check["id"],
                "kind": "deterministic",
                "passed": passed,
                "evidence": evidence,
            }
        )

    manual_results: dict[str, Any] = {}
    if args.manual_results:
        try:
            loaded = load_json(args.manual_results, "manual results")
            if not isinstance(loaded, dict):
                raise ContractError("manual results root must be an object")
            manual_results = loaded
            expected_manual_ids = {item["id"] for item in manual_checks}
            unexpected = sorted(set(manual_results) - expected_manual_ids)
            if unexpected:
                raise ContractError(
                    f"manual results contain unknown check ids: {', '.join(unexpected)}"
                )
        except ContractError as exc:
            print(f"ERROR  {exc}", file=sys.stderr)
            return 2

    incomplete: list[str] = []
    for check in manual_checks:
        result = manual_results.get(check["id"])
        if not isinstance(result, dict):
            incomplete.append(check["id"])
            continue
        passed = result.get("passed")
        evidence = result.get("evidence")
        if not isinstance(passed, bool) or not isinstance(evidence, str) or not evidence:
            incomplete.append(check["id"])
            continue
        failed += int(not passed)
        results.append(
            {
                "id": check["id"],
                "kind": "manual",
                "passed": passed,
                "evidence": evidence,
            }
        )

    try:
        report = {
            "schema": RESULT_SCHEMA,
            "inputs": {
                "contract": input_record(args.contract, report_path),
                "output": input_record(args.output, report_path),
                **(
                    {
                        "manual_results": input_record(
                            args.manual_results, report_path
                        )
                    }
                    if args.manual_results
                    else {}
                ),
            },
            "passed": failed == 0 and not incomplete,
            "failed": failed,
            "incomplete_manual": incomplete,
            "results": results,
        }
    except ContractError as exc:
        print(f"ERROR  {exc}", file=sys.stderr)
        return 2
    if report_path:
        try:
            atomic_write_text(
                report_path,
                json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            )
        except OSError as exc:
            print(f"ERROR  cannot write report at {report_path}: {exc}", file=sys.stderr)
            return 2

    for result in results:
        state = "PASS" if result["passed"] else "FAIL"
        print(f"{state:<4}  {result['id']}: {result['evidence']}")
    if incomplete:
        print(
            f"ERROR  incomplete manual checks: {', '.join(incomplete)}",
            file=sys.stderr,
        )
        return 2
    print(f"Result: {failed} FAIL / {len(results) - failed} PASS")
    return 1 if failed else 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--contract", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--manual-results", type=Path)
    parser.add_argument("--report", type=Path)
    return evaluate(parser.parse_args())


if __name__ == "__main__":
    raise SystemExit(main())
