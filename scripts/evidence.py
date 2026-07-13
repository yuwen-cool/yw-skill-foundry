#!/usr/bin/env python3
"""Create and verify auditable run-compare evidence manifests."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

sys.dont_write_bytecode = True

from contract_eval import ContractError, run_check, validate_contract
from frontmatter import FrontmatterError, parse_frontmatter_file


SCHEMA = "yw-skill-foundry.run-compare/v2"
V2_SCHEMAS = {
    SCHEMA,
    "skill-foundry.run-compare/v2",
    "skill-craft.run-compare/v2",
}
V1_SCHEMAS = {
    "yw-skill-foundry.run-compare/v1",
    "skill-foundry.run-compare/v1",
    "skill-craft.run-compare/v1",
}
CONTRACT_RESULT_SCHEMAS = {
    "yw-skill-foundry.contract-result/v2",
    "skill-foundry.contract-result/v2",
    "skill-craft.contract-result/v2",
}
ROUTING_RESULT_SCHEMAS = {
    "yw-skill-foundry.routing-result/v1",
    "skill-foundry.routing-result/v1",
    "skill-craft.routing-result/v1",
}
RUNS_SCHEMAS = {
    "yw-skill-foundry.runs/v1",
    "skill-foundry.runs/v1",
    "skill-craft.runs/v1",
}
JUDGES_SCHEMAS = {
    "yw-skill-foundry.judges/v1",
    "skill-foundry.judges/v1",
    "skill-craft.judges/v1",
}
LEGACY_REQUIRED = (
    "task.md",
    "skill-snapshot.md",
    "baseline.md",
    "with_skill.md",
    "candidate-a.md",
    "candidate-b.md",
    "judge-prompt.md",
    "mapping.json",
    "verdict.md",
)
REQUIRED = (
    "task.md",
    "skill-snapshot.md",
    "judge-prompt.md",
    "mapping.json",
    "verdict.md",
    "runs.json",
    "judges.json",
)
PLACEHOLDER_MODELS = {"", "unknown", "unspecified", "n/a"}


def fail(message: str) -> int:
    print(f"FAIL  {message}", file=sys.stderr)
    return 1


def digest(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def file_record(path: Path) -> dict[str, object]:
    return {"sha256": digest(path), "bytes": path.stat().st_size}


def output_target_error(path: Path, label: str) -> str | None:
    if path.is_symlink():
        return f"{label} must not be a symlink: {path}"
    if path.exists():
        return f"{label} already exists; evidence runs are immutable"
    try:
        parent = path.parent.resolve(strict=True)
    except OSError as exc:
        return f"cannot resolve {label} parent for {path}: {exc}"
    if not parent.is_dir():
        return f"{label} parent is not a directory: {parent}"
    return None


def atomic_copy(source: Path, destination: Path) -> None:
    fd, temp_name = tempfile.mkstemp(
        prefix=f".{destination.name}.", dir=destination.parent
    )
    try:
        with source.open("rb") as src, os.fdopen(fd, "wb") as dst:
            shutil.copyfileobj(src, dst)
            dst.flush()
            os.fsync(dst.fileno())
        os.link(temp_name, destination)
    finally:
        if os.path.exists(temp_name):
            os.unlink(temp_name)


def atomic_write_json(path: Path, value: object) -> None:
    fd, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            json.dump(value, handle, ensure_ascii=False, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.link(temp_name, path)
    finally:
        if os.path.exists(temp_name):
            os.unlink(temp_name)


def load_json_file(path: Path, label: str, errors: list[str]) -> object | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        errors.append(f"invalid {label}: {exc}")
        return None


def safe_artifact_name(value: object, label: str, errors: list[str]) -> str | None:
    if not isinstance(value, str) or not value:
        errors.append(f"{label} must be a non-empty relative file path")
        return None
    path = Path(value)
    if path.is_absolute() or ".." in path.parts:
        errors.append(f"{label} must stay inside the evidence directory: {value!r}")
        return None
    return value


def artifact_is_contained(run_dir: Path, path: Path) -> bool:
    try:
        path.resolve().relative_to(run_dir.resolve())
        return True
    except ValueError:
        return False


def validate_contract_report(
    run_dir: Path,
    report_name: str,
    input_names: dict[str, str],
    declared_passed: object,
    label: str,
    errors: list[str],
) -> None:
    report_path = run_dir / report_name
    if not report_path.is_file():
        return
    if not artifact_is_contained(run_dir, report_path):
        errors.append(f"{label} contract report escapes evidence directory")
        return
    report = load_json_file(report_path, f"{label} contract report", errors)
    if not isinstance(report, dict):
        return
    if report.get("schema") not in CONTRACT_RESULT_SCHEMAS:
        errors.append(f"{label} contract report has unsupported schema")

    inputs = report.get("inputs")
    if not isinstance(inputs, dict):
        errors.append(f"{label} contract report inputs must be an object")
        inputs = {}
    inputs_safe = True
    for input_label, artifact_name in input_names.items():
        record = inputs.get(input_label)
        artifact_path = run_dir / artifact_name
        if not isinstance(record, dict):
            errors.append(f"{label} contract report lacks {input_label} input")
            continue
        if not artifact_is_contained(run_dir, artifact_path):
            errors.append(
                f"{label} contract report {input_label} escapes evidence directory"
            )
            inputs_safe = False
            continue
        expected_path = os.path.relpath(
            artifact_path.resolve(), report_path.parent.resolve()
        )
        if record.get("path") != expected_path:
            errors.append(
                f"{label} contract report {input_label} path does not bind to the run"
            )
        if artifact_path.is_file() and record.get("sha256") != digest(artifact_path):
            errors.append(
                f"{label} contract report {input_label} hash does not bind to the run"
            )
    if not inputs_safe:
        return

    contract_path = run_dir / input_names["contract"]
    output_path = run_dir / input_names["output"]
    manual_path = run_dir / input_names["manual_results"]
    semantic_results: list[dict[str, object]] = []
    try:
        contract = json.loads(contract_path.read_text(encoding="utf-8"))
        checks, manual_checks = validate_contract(contract)
        output_text = output_path.read_text(encoding="utf-8")
        try:
            parsed_output = json.loads(output_text)
        except json.JSONDecodeError:
            parsed_output = None
        manual_results = json.loads(manual_path.read_text(encoding="utf-8"))
        if not isinstance(manual_results, dict):
            raise ContractError("manual results root must be an object")
        expected_manual_ids = {item["id"] for item in manual_checks}
        if set(manual_results) != expected_manual_ids:
            raise ContractError("manual results do not cover every manual check once")
        for check in checks:
            passed, evidence = run_check(check, output_text, parsed_output)
            semantic_results.append(
                {
                    "id": check["id"],
                    "kind": "deterministic",
                    "passed": passed,
                    "evidence": evidence,
                }
            )
        for check in manual_checks:
            result = manual_results[check["id"]]
            if (
                not isinstance(result, dict)
                or not isinstance(result.get("passed"), bool)
                or not isinstance(result.get("evidence"), str)
                or not result.get("evidence")
            ):
                raise ContractError(
                    f"manual result {check['id']!r} needs passed + evidence"
                )
            semantic_results.append(
                {
                    "id": check["id"],
                    "kind": "manual",
                    "passed": result["passed"],
                    "evidence": result["evidence"],
                }
            )
    except (OSError, UnicodeError, json.JSONDecodeError, ContractError) as exc:
        errors.append(f"{label} cannot re-evaluate contract report: {exc}")
        return

    if report.get("results") != semantic_results:
        errors.append(f"{label} contract report results do not match re-evaluation")
    failed = sum(int(not result["passed"]) for result in semantic_results)
    if report.get("failed") != failed:
        errors.append(f"{label} contract report failed count is inconsistent")
    if report.get("incomplete_manual") != []:
        errors.append(f"{label} contract report has incomplete manual checks")
    if not isinstance(declared_passed, bool):
        errors.append(f"{label} contract_passed must be boolean")
    elif report.get("passed") != declared_passed:
        errors.append(f"{label} contract_passed disagrees with report")
    if report.get("passed") != (failed == 0):
        errors.append(f"{label} contract report pass state is inconsistent")


def validate_routing_report(
    run_dir: Path,
    report_name: str,
    input_names: dict[str, str],
    declared_passed: object,
    label: str,
    errors: list[str],
) -> None:
    report_path = run_dir / report_name
    if not report_path.is_file() or not artifact_is_contained(run_dir, report_path):
        errors.append(f"{label} routing report is missing or escapes evidence directory")
        return
    report = load_json_file(report_path, f"{label} routing report", errors)
    if not isinstance(report, dict):
        return
    if report.get("schema") not in ROUTING_RESULT_SCHEMAS:
        errors.append(f"{label} routing report has unsupported schema")

    inputs = report.get("inputs")
    if not isinstance(inputs, dict):
        errors.append(f"{label} routing report inputs must be an object")
        inputs = {}
    inputs_safe = True
    for input_label, artifact_name in input_names.items():
        artifact_path = run_dir / artifact_name
        record = inputs.get(input_label)
        if not artifact_is_contained(run_dir, artifact_path):
            errors.append(f"{label} routing {input_label} escapes evidence directory")
            inputs_safe = False
            continue
        if not isinstance(record, dict):
            errors.append(f"{label} routing report lacks {input_label} input")
            continue
        expected_path = os.path.relpath(
            artifact_path.resolve(), report_path.parent.resolve()
        )
        if record.get("path") != expected_path:
            errors.append(f"{label} routing {input_label} path is not bound")
        if artifact_path.is_file() and record.get("sha256") != digest(artifact_path):
            errors.append(f"{label} routing {input_label} hash is not bound")
    if not inputs_safe:
        return

    try:
        cases: list[dict[str, object]] = []
        for raw in (run_dir / input_names["fixture"]).read_text(
            encoding="utf-8"
        ).splitlines():
            if not raw.strip() or raw.lstrip().startswith("#"):
                continue
            case = json.loads(raw)
            if (
                not isinstance(case, dict)
                or not isinstance(case.get("prompt"), str)
                or case.get("expect") not in {"trigger", "no"}
            ):
                raise ValueError("malformed fixture case")
            case.setdefault("kind", "unspecified")
            case["holdout"] = bool(case.get("holdout", False))
            cases.append(case)
        judgments: dict[int, str] = {}
        for raw in (run_dir / input_names["judgments"]).read_text(
            encoding="utf-8"
        ).splitlines():
            if not raw.strip() or raw.lstrip().startswith("#"):
                continue
            item = json.loads(raw)
            jid = int(item["id"])
            decision = item["decision"]
            if decision not in {"trigger", "no"} or jid in judgments:
                raise ValueError("malformed or duplicate judgment")
            judgments[jid] = decision
        if not cases or set(judgments) != set(range(len(cases))):
            raise ValueError("routing report must cover every fixture case")
    except (OSError, UnicodeError, json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
        errors.append(f"{label} cannot re-evaluate routing report: {exc}")
        return

    def metric(ids: list[int]) -> dict[str, int]:
        return {
            "correct": sum(judgments[i] == cases[i]["expect"] for i in ids),
            "total": len(ids),
        }

    all_ids = list(range(len(cases)))
    train_ids = [i for i in all_ids if not cases[i]["holdout"]]
    holdout_ids = [i for i in all_ids if cases[i]["holdout"]]
    phases = {"overall": metric(all_ids)}
    if train_ids:
        phases["train"] = metric(train_ids)
    if holdout_ids:
        phases["holdout"] = metric(holdout_ids)
    by_kind: dict[str, list[int]] = {}
    for i, case in enumerate(cases):
        by_kind.setdefault(str(case["kind"]), []).append(i)
    kinds = {kind: metric(ids) for kind, ids in sorted(by_kind.items())}
    under = [
        i
        for i, case in enumerate(cases)
        if case["expect"] == "trigger" and judgments[i] == "no"
    ]
    over = [
        i
        for i, case in enumerate(cases)
        if case["expect"] == "no" and judgments[i] == "trigger"
    ]
    threshold = report.get("min_accuracy")
    if (
        not isinstance(threshold, (int, float))
        or isinstance(threshold, bool)
        or not 0 <= threshold <= 100
    ):
        errors.append(f"{label} routing report has invalid min_accuracy")
        return
    gated = []
    if train_ids:
        gated.append(phases["train"])
    if holdout_ids:
        gated.append(phases["holdout"])
    if not gated:
        gated.append(phases["overall"])
    passed = all(
        item["correct"] / item["total"] * 100 + 1e-9 >= threshold
        for item in gated
    )
    expected = {
        "phases": phases,
        "by_kind": kinds,
        "under_trigger_ids": under,
        "over_trigger_ids": over,
    }
    for key, value in expected.items():
        if report.get(key) != value:
            errors.append(f"{label} routing report {key} does not match re-evaluation")
    if not isinstance(declared_passed, bool):
        errors.append(f"{label} routing_passed must be boolean")
    elif declared_passed != passed or report.get("passed") != passed:
        errors.append(f"{label} routing pass state is inconsistent")


def validate_legacy_files(run_dir: Path) -> list[str]:
    errors: list[str] = []
    for name in LEGACY_REQUIRED:
        path = run_dir / name
        if not path.is_file():
            errors.append(f"missing required artifact: {name}")
        elif path.stat().st_size == 0:
            errors.append(f"empty required artifact: {name}")
        elif not artifact_is_contained(run_dir, path):
            errors.append(f"required artifact escapes evidence directory: {name}")
    mapping_path = run_dir / "mapping.json"
    if mapping_path.is_file() and artifact_is_contained(run_dir, mapping_path):
        try:
            mapping = json.loads(mapping_path.read_text(encoding="utf-8"))
            if not isinstance(mapping, dict) or set(mapping.values()) != {
                "baseline",
                "with_skill",
            }:
                errors.append(
                    'mapping.json must map blinded labels to exactly "baseline" and "with_skill"'
                )
        except (OSError, json.JSONDecodeError) as exc:
            errors.append(f"invalid mapping.json: {exc}")
    return errors


def validate_v2_files(
    run_dir: Path,
) -> tuple[list[str], set[str], dict[str, object]]:
    errors: list[str] = []
    artifacts = set(REQUIRED)
    protocol: dict[str, object] = {}

    for name in REQUIRED:
        path = run_dir / name
        if not path.is_file():
            errors.append(f"missing required artifact: {name}")
        elif path.stat().st_size == 0:
            errors.append(f"empty required artifact: {name}")
        elif not artifact_is_contained(run_dir, path):
            errors.append(f"required artifact escapes evidence directory: {name}")

    mapping_path = run_dir / "mapping.json"
    if mapping_path.is_file() and artifact_is_contained(run_dir, mapping_path):
        mapping = load_json_file(mapping_path, "mapping.json", errors)
        if not isinstance(mapping, dict) or set(mapping.values()) != {
            "baseline",
            "with_skill",
        }:
            errors.append(
                'mapping.json must map blinded labels to exactly "baseline" and "with_skill"'
            )

    runs_path = run_dir / "runs.json"
    judges_path = run_dir / "judges.json"
    runs_doc = (
        load_json_file(runs_path, "runs.json", errors)
        if artifact_is_contained(run_dir, runs_path)
        else None
    )
    judges_doc = (
        load_json_file(judges_path, "judges.json", errors)
        if artifact_is_contained(run_dir, judges_path)
        else None
    )
    if not isinstance(runs_doc, dict) or not isinstance(judges_doc, dict):
        return errors, artifacts, protocol

    level = runs_doc.get("evaluation_level")
    if level not in {"exploratory", "production"}:
        errors.append("runs.json evaluation_level must be exploratory or production")
        level = "exploratory"
    if runs_doc.get("schema") not in RUNS_SCHEMAS:
        errors.append("runs.json has unsupported schema")
    runs = runs_doc.get("runs")
    if not isinstance(runs, list):
        errors.append("runs.json runs must be an array")
        runs = []

    metrics_status = runs_doc.get("metrics_status")
    if metrics_status not in {"recorded", "unavailable"}:
        errors.append("runs.json metrics_status must be recorded or unavailable")
    if metrics_status == "unavailable" and not runs_doc.get(
        "metrics_unavailable_reason"
    ):
        errors.append("unavailable metrics need metrics_unavailable_reason")

    counts = {"baseline": 0, "with_skill": 0}
    generator_models: dict[str, set[str]] = {
        "baseline": set(),
        "with_skill": set(),
    }
    seen_runs: set[tuple[str, int]] = set()
    run_ids: set[str] = set()
    output_files: set[str] = set()
    contract_reports: set[str] = set()
    run_outputs: dict[tuple[str, int], str] = {}
    run_models: dict[tuple[str, int], str] = {}
    for index, run in enumerate(runs):
        if not isinstance(run, dict):
            errors.append(f"runs[{index}] must be an object")
            continue
        config = run.get("configuration")
        number = run.get("run_number")
        model = run.get("model")
        run_id = run.get("id")
        if config not in counts:
            errors.append(f"runs[{index}] has bad configuration {config!r}")
            continue
        if not isinstance(number, int) or isinstance(number, bool) or number < 1:
            errors.append(f"runs[{index}] run_number must be a positive integer")
            continue
        key = (config, number)
        if key in seen_runs:
            errors.append(f"duplicate run {config} #{number}")
        seen_runs.add(key)
        counts[config] += 1
        if not isinstance(run_id, str) or not run_id:
            errors.append(f"runs[{index}] needs a non-empty id")
        elif run_id in run_ids:
            errors.append(f"duplicate run id {run_id!r}")
        else:
            run_ids.add(run_id)
        if not isinstance(model, str) or model.strip().lower() in PLACEHOLDER_MODELS:
            errors.append(f"runs[{index}] needs a real model identity")
        else:
            generator_models[config].add(model)
            run_models[(config, number)] = model
        output = safe_artifact_name(run.get("output"), f"runs[{index}].output", errors)
        if output:
            artifacts.add(output)
            if output in output_files:
                errors.append(f"runs[{index}] reuses output file {output!r}")
            output_files.add(output)
            run_outputs[(config, number)] = output
        contract_report = (
            safe_artifact_name(
                run.get("contract_report"),
                f"runs[{index}].contract_report",
                errors,
            )
            if run.get("contract_report") is not None
            else None
        )
        contract_inputs: dict[str, str] = {}
        for field, input_label in (
            ("contract_file", "contract"),
            ("manual_results_file", "manual_results"),
        ):
            value = run.get(field)
            artifact = (
                safe_artifact_name(value, f"runs[{index}].{field}", errors)
                if value is not None
                else None
            )
            if artifact:
                artifacts.add(artifact)
                contract_inputs[input_label] = artifact
            elif level == "production":
                errors.append(f"runs[{index}] production run needs {field}")
        routing_fields: dict[str, str] = {}
        for field, input_label in (
            ("routing_fixture", "fixture"),
            ("routing_judgments", "judgments"),
            ("routing_worksheet", "worksheet"),
            ("routing_report", "report"),
        ):
            value = run.get(field)
            if value is not None:
                artifact = safe_artifact_name(
                    value, f"runs[{index}].{field}", errors
                )
                if artifact:
                    artifacts.add(artifact)
                    routing_fields[input_label] = artifact
        if routing_fields:
            missing_routing = {
                "fixture",
                "judgments",
                "worksheet",
                "report",
            } - set(routing_fields)
            if missing_routing:
                errors.append(
                    f"runs[{index}] incomplete routing evidence: {', '.join(sorted(missing_routing))}"
                )
            else:
                report_name = routing_fields.pop("report")
                validate_routing_report(
                    run_dir,
                    report_name,
                    routing_fields,
                    run.get("routing_passed"),
                    f"runs[{index}]",
                    errors,
                )
        if contract_report:
            artifacts.add(contract_report)
            if contract_report in contract_reports:
                errors.append(
                    f"runs[{index}] reuses contract report {contract_report!r}"
                )
            contract_reports.add(contract_report)
            if output and set(contract_inputs) == {"contract", "manual_results"}:
                validate_contract_report(
                    run_dir,
                    contract_report,
                    {**contract_inputs, "output": output},
                    run.get("contract_passed"),
                    f"runs[{index}]",
                    errors,
                )
        elif level == "production":
            errors.append(f"runs[{index}] production run needs contract_report")
        if metrics_status == "recorded":
            tokens = run.get("tokens")
            duration = run.get("duration_seconds")
            if not isinstance(tokens, int) or isinstance(tokens, bool) or tokens < 0:
                errors.append(f"runs[{index}] tokens must be a non-negative integer")
            if (
                not isinstance(duration, (int, float))
                or isinstance(duration, bool)
                or duration < 0
            ):
                errors.append(
                    f"runs[{index}] duration_seconds must be a non-negative number"
                )

    if counts["baseline"] < 1 or counts["with_skill"] < 1:
        errors.append("runs.json needs at least one baseline and one with_skill run")
    if level == "production" and (
        counts["baseline"] < 2 or counts["with_skill"] < 2
    ):
        errors.append("production evidence needs at least two runs per configuration")
    if level == "production":
        baseline_numbers = {
            number for config, number in run_outputs if config == "baseline"
        }
        with_skill_numbers = {
            number for config, number in run_outputs if config == "with_skill"
        }
        if baseline_numbers != with_skill_numbers:
            errors.append(
                "production baseline and with_skill runs need matching run numbers"
            )
        for number in sorted(baseline_numbers & with_skill_numbers):
            if run_models.get(("baseline", number)) != run_models.get(
                ("with_skill", number)
            ):
                errors.append(
                    f"production run #{number} baseline/with_skill model mismatch"
                )
    if level == "production" and generator_models["baseline"] != generator_models[
        "with_skill"
    ]:
        errors.append(
            "production baseline and with_skill runs must use the same model identities"
        )

    if judges_doc.get("schema") not in JUDGES_SCHEMAS:
        errors.append("judges.json has unsupported schema")
    judges = judges_doc.get("judges")
    if not isinstance(judges, list):
        errors.append("judges.json judges must be an array")
        judges = []
    orders: set[tuple[str, str]] = set()
    orders_by_model_run: dict[tuple[str, int], set[tuple[str, str]]] = {}
    judge_ids: set[str] = set()
    judge_evidence_files: set[str] = set()
    for index, judge in enumerate(judges):
        if not isinstance(judge, dict):
            errors.append(f"judges[{index}] must be an object")
            continue
        judge_id = judge.get("id")
        model = judge.get("model")
        candidate_a = judge.get("candidate_a")
        candidate_b = judge.get("candidate_b")
        verdict = judge.get("verdict")
        run_number = judge.get("run_number")
        if not isinstance(judge_id, str) or not judge_id:
            errors.append(f"judges[{index}] needs a non-empty id")
        elif judge_id in judge_ids:
            errors.append(f"duplicate judge id {judge_id!r}")
        else:
            judge_ids.add(judge_id)
        if not isinstance(model, str) or model.strip().lower() in PLACEHOLDER_MODELS:
            errors.append(f"judges[{index}] needs a real model identity")
        if (
            not isinstance(run_number, int)
            or isinstance(run_number, bool)
            or run_number < 1
        ):
            errors.append(f"judges[{index}] run_number must be a positive integer")
            run_number = -1
        if {candidate_a, candidate_b} != {"baseline", "with_skill"}:
            errors.append(
                f"judges[{index}] candidate_a/candidate_b must be a blind permutation"
            )
        else:
            orders.add((candidate_a, candidate_b))
            if (
                isinstance(model, str)
                and model.strip().lower() not in PLACEHOLDER_MODELS
                and run_number > 0
            ):
                orders_by_model_run.setdefault((model, run_number), set()).add(
                    (candidate_a, candidate_b)
                )
        if verdict not in {"baseline", "with_skill", "tie"}:
            errors.append(f"judges[{index}] has invalid verdict {verdict!r}")
        referenced: dict[str, str | None] = {}
        for field in (
            "candidate_a_file",
            "candidate_b_file",
            "prompt_file",
            "evidence_file",
        ):
            referenced[field] = safe_artifact_name(
                judge.get(field), f"judges[{index}].{field}", errors
            )
            if referenced[field]:
                artifacts.add(referenced[field] or "")
        evidence_file = referenced["evidence_file"]
        if evidence_file:
            if evidence_file in judge_evidence_files:
                errors.append(
                    f"judges[{index}] reuses evidence file {evidence_file!r}"
                )
            judge_evidence_files.add(evidence_file)
        for label, logical, field in (
            ("A", candidate_a, "candidate_a_file"),
            ("B", candidate_b, "candidate_b_file"),
        ):
            candidate_file = referenced[field]
            expected_file = run_outputs.get((logical, run_number))
            if expected_file is None:
                errors.append(
                    f"judges[{index}] Candidate {label} references missing {logical} run #{run_number}"
                )
            elif candidate_file:
                candidate_path = run_dir / candidate_file
                expected_path = run_dir / expected_file
                if not artifact_is_contained(
                    run_dir, candidate_path
                ) or not artifact_is_contained(run_dir, expected_path):
                    errors.append(
                        f"judges[{index}] Candidate {label} escapes evidence directory"
                    )
                elif (
                    candidate_path.is_file()
                    and expected_path.is_file()
                    and digest(candidate_path) != digest(expected_path)
                ):
                    errors.append(
                        f"judges[{index}] Candidate {label} bytes do not match {logical}"
                    )

    if not judges:
        errors.append("judges.json needs at least one judge")
    if level == "production":
        if len(judges) < 2:
            errors.append("production evidence needs at least two judge runs")
        required_orders = {
            ("baseline", "with_skill"),
            ("with_skill", "baseline"),
        }
        if orders != required_orders:
            errors.append(
                "production evidence needs position-swapped blind judgments"
            )
        judge_models = {
            model for model, _ in orders_by_model_run
        }
        expected_numbers = {
            number for config, number in run_outputs if config == "baseline"
        }
        for model in sorted(judge_models):
            for number in sorted(expected_numbers):
                model_orders = orders_by_model_run.get((model, number), set())
                if model_orders != required_orders:
                    errors.append(
                        f"production judge model {model!r} run #{number} needs both candidate orders"
                    )

    for name in sorted(artifacts):
        path = run_dir / name
        if not path.is_file():
            errors.append(f"missing referenced artifact: {name}")
        elif path.stat().st_size == 0:
            errors.append(f"empty referenced artifact: {name}")
        else:
            try:
                path.resolve().relative_to(run_dir.resolve())
            except ValueError:
                errors.append(f"referenced artifact escapes evidence directory: {name}")

    protocol = {
        "evaluation_level": level,
        "runs": counts,
        "judges": len(judges),
        "position_swapped": len(orders) == 2,
        "metrics_status": metrics_status,
    }
    return errors, artifacts, protocol


def cmd_create(args: argparse.Namespace) -> int:
    run_dir = args.run_dir.resolve()
    skill_dir = args.skill.resolve()
    manifest_path = run_dir / "manifest.json"
    skill_file = skill_dir / "SKILL.md"

    if not run_dir.is_dir():
        return fail(f"run directory does not exist: {run_dir}")
    if not skill_file.is_file():
        return fail(f"skill snapshot source not found: {skill_file}")

    snapshot = run_dir / "skill-snapshot.md"
    for target, label in (
        (manifest_path, "manifest.json"),
        (snapshot, "skill-snapshot.md"),
    ):
        error = output_target_error(target, label)
        if error:
            return fail(error)
    try:
        atomic_copy(skill_file, snapshot)
    except OSError as exc:
        return fail(f"cannot create skill-snapshot.md: {exc}")

    errors, artifacts, protocol = validate_v2_files(run_dir)
    if errors:
        snapshot.unlink(missing_ok=True)
        for error in errors:
            print(f"FAIL  {error}", file=sys.stderr)
        return 1

    try:
        metadata = parse_frontmatter_file(skill_file)
    except (OSError, FrontmatterError) as exc:
        snapshot.unlink(missing_ok=True)
        return fail(f"cannot parse skill metadata: {exc}")

    if artifact_is_contained(run_dir, skill_file):
        artifacts.add(os.path.relpath(skill_file, run_dir))
    files = {name: file_record(run_dir / name) for name in sorted(artifacts)}
    manifest = {
        "schema": SCHEMA,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "skill": {
            "name": metadata.get("name", skill_dir.name),
            "snapshot": "skill-snapshot.md",
        },
        "protocol": protocol,
        "notes": args.notes,
        "files": files,
    }

    try:
        atomic_write_json(manifest_path, manifest)
    except OSError as exc:
        snapshot.unlink(missing_ok=True)
        return fail(f"cannot create manifest.json: {exc}")

    print(f"PASS  created {manifest_path}")
    print(f"      {len(files)} artifacts hashed with {SCHEMA}")
    return 0


def cmd_verify(args: argparse.Namespace) -> int:
    run_dir = args.run_dir.resolve()
    manifest_path = run_dir / "manifest.json"
    if not manifest_path.is_file():
        return fail(f"manifest.json not found in {run_dir}")

    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return fail(f"invalid manifest.json: {exc}")

    schema = manifest.get("schema")
    if schema in V1_SCHEMAS:
        errors = validate_legacy_files(run_dir)
        artifacts = set(LEGACY_REQUIRED)
    elif schema in V2_SCHEMAS:
        errors, artifacts, protocol = validate_v2_files(run_dir)
        if manifest.get("protocol") != protocol:
            errors.append("manifest protocol summary does not match runs/judges metadata")
        skill_record = manifest.get("skill")
        if isinstance(skill_record, dict) and isinstance(
            skill_record.get("source_path"), str
        ):
            source_file = run_dir / skill_record["source_path"] / "SKILL.md"
            if source_file.is_file() and artifact_is_contained(run_dir, source_file):
                artifacts.add(os.path.relpath(source_file, run_dir))
    else:
        errors = [f"unsupported schema: {schema!r}"]
        artifacts = set()
    records = manifest.get("files")
    if not isinstance(records, dict):
        errors.append("manifest files must be an object")
        records = {}

    for name in sorted(artifacts):
        path = run_dir / name
        record = records.get(name)
        if not isinstance(record, dict):
            errors.append(f"manifest has no record for {name}")
            continue
        if path.is_file():
            if not artifact_is_contained(run_dir, path):
                errors.append(f"manifest artifact escapes evidence directory: {name}")
                continue
            actual_hash = digest(path)
            actual_bytes = path.stat().st_size
            if record.get("sha256") != actual_hash:
                errors.append(f"hash mismatch: {name}")
            if record.get("bytes") != actual_bytes:
                errors.append(f"size mismatch: {name}")

    extra_records = sorted(set(records) - artifacts)
    if extra_records:
        errors.append(f"manifest records unexpected artifact(s): {', '.join(extra_records)}")

    if errors:
        for error in errors:
            print(f"FAIL  {error}", file=sys.stderr)
        return 1
    print(f"PASS  evidence verified: {run_dir}")
    print(f"      {len(artifacts)} artifacts match their SHA-256 records ({schema})")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    create = sub.add_parser("create", help="snapshot a skill and create manifest.json")
    create.add_argument("run_dir", type=Path)
    create.add_argument("--skill", type=Path, required=True)
    create.add_argument("--notes", default="")
    create.set_defaults(func=cmd_create)

    verify = sub.add_parser("verify", help="verify all artifact hashes and structure")
    verify.add_argument("run_dir", type=Path)
    verify.set_defaults(func=cmd_verify)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
