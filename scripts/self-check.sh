#!/usr/bin/env bash
set -uo pipefail

# self-check.sh — one command that proves YW SkillFoundry's own harness works.
#
# It does two things the manual runs don't:
#   1. Positive path: run the checkers on YW SkillFoundry itself; each must pass.
#   2. Bite path: feed each checker a deliberately broken input; each MUST fail.
#      A checker that passes everything (including garbage) is silently broken —
#      this is exactly the "scripts untested" gap. Bite tests guard the guards.
#
# Usage: bash scripts/self-check.sh   (run from the skill root)
# Exit 0 = harness healthy, Exit 1 = a check or a bite test misbehaved.

export PYTHONDONTWRITEBYTECODE=1

cd "$(dirname "$0")/.." || exit 2
ROOT="$(pwd)"
RELEASE_VERSION="$(< "$ROOT/VERSION")"
PASS=0; FAIL=0
ok()   { printf "PASS  %s\n" "$*"; PASS=$((PASS + 1)); }
bad()  { printf "FAIL  %s\n" "$*"; FAIL=$((FAIL + 1)); }

expect_exit() { # <want> <label> -- <cmd...>
  local want=$1 label=$2; shift 3
  "$@" >/dev/null 2>&1; local got=$?
  if [[ "$got" -eq "$want" ]]; then ok "$label (exit $got)"; else bad "$label (got exit $got, want $want)"; fi
}

TMP="$(mktemp -d)" || { echo "ERROR  mktemp failed" >&2; exit 2; }
[[ -n "$TMP" && -d "$TMP" ]] || { echo "ERROR  invalid temp directory" >&2; exit 2; }
trap 'rm -rf "$TMP"' EXIT

echo "== positive path: checkers must accept YW SkillFoundry itself =="
IDENTITY_ROOT="$TMP/yw-skill-foundry"
mkdir -p "$IDENTITY_ROOT"
cp "$ROOT/SKILL.md" "$IDENTITY_ROOT/SKILL.md"
cp -R "$ROOT/references" "$IDENTITY_ROOT/references"
expect_exit 0 "validate-skill.sh identity fixture" -- bash "$ROOT/scripts/validate-skill.sh" "$IDENTITY_ROOT"
expect_exit 0 "trigger_eval lint identity fixture" -- python3 "$ROOT/scripts/trigger_eval.py" lint --skill "$IDENTITY_ROOT"
expect_exit 0 "citation_lint ."            -- python3 "$ROOT/scripts/citation_lint.py" --skill "$ROOT"
expect_exit 0 "skill_library_audit default root" -- python3 "$ROOT/scripts/skill_library_audit.py"
expect_exit 0 "privacy_lint self-test"      -- python3 "$ROOT/scripts/privacy_lint.py" --self-test
expect_exit 0 "privacy_lint working tree"   -- python3 "$ROOT/scripts/privacy_lint.py" --working-tree-only

echo
echo "== bite path: checkers must REJECT broken input (guard the guards) =="

# 1. validate-skill.sh must fail when SKILL.md is missing.
mkdir -p "$TMP/no-skill"
expect_exit 1 "validate-skill.sh rejects missing SKILL.md" -- bash "$ROOT/scripts/validate-skill.sh" "$TMP/no-skill"

# 2. trigger_eval lint must fail on an empty description.
mkdir -p "$TMP/bad-desc"
printf -- '---\nname: x\ndescription: ""\n---\n# x\n' > "$TMP/bad-desc/SKILL.md"
expect_exit 1 "trigger_eval lint rejects empty description" -- python3 "$ROOT/scripts/trigger_eval.py" lint --skill "$TMP/bad-desc"

# 3. trigger_eval score must fail when a judgment is wrong (scorer regression guard).
printf '%s\n' \
  '{"prompt": "a", "expect": "trigger", "kind": "x"}' \
  '{"prompt": "b", "expect": "no", "kind": "y"}' > "$TMP/fix.jsonl"
printf '%s\n' '{"id": 0, "decision": "no"}' '{"id": 1, "decision": "no"}' > "$TMP/judge.jsonl"
expect_exit 1 "trigger_eval score rejects a wrong judgment" -- python3 "$ROOT/scripts/trigger_eval.py" score --fixture "$TMP/fix.jsonl" --judgments "$TMP/judge.jsonl"

# 4. validate-skill.sh must FAIL on a planted secret (R10 security-scan guard).
mkdir -p "$TMP/secret"
secret_value="AK""IA""1234567890ABCDEF"
printf -- '---\nname: x\ndescription: "Valid description, long enough to route, used for the secret-scan bite test."\n---\n# x\n%s\n' "$secret_value" > "$TMP/secret/SKILL.md"
expect_exit 1 "validate-skill.sh rejects a planted secret" -- bash "$ROOT/scripts/validate-skill.sh" "$TMP/secret"

# 5. skill_library_audit.py: a clean 2-skill library passes; a missing-description one fails.
mkdir -p "$TMP/lib-ok/alpha" "$TMP/lib-ok/beta"
printf -- '---\nname: alpha\ndescription: "Use when converting markdown files into styled pdf documents."\n---\n# a\n' > "$TMP/lib-ok/alpha/SKILL.md"
printf -- '---\nname: beta\ndescription: "Use when scheduling recurring database backup jobs on a remote server."\n---\n# b\n' > "$TMP/lib-ok/beta/SKILL.md"
expect_exit 0 "skill_library_audit accepts a clean library" -- python3 "$ROOT/scripts/skill_library_audit.py" --root "$TMP/lib-ok"
mkdir -p "$TMP/lib-bad/gamma"
printf -- '---\nname: gamma\ndescription: ""\n---\n# g\n' > "$TMP/lib-bad/gamma/SKILL.md"
expect_exit 1 "skill_library_audit rejects a skill with no description" -- python3 "$ROOT/scripts/skill_library_audit.py" --root "$TMP/lib-bad"

# 6. skill_library_audit.py must find NESTED skills (one-level scanning was a false clean).
mkdir -p "$TMP/lib-nested/.system/hidden-skill"
printf -- '---\nname: hidden-skill\ndescription: ""\n---\n# h\n' > "$TMP/lib-nested/.system/hidden-skill/SKILL.md"
expect_exit 1 "skill_library_audit finds a broken skill nested 2 levels deep" -- python3 "$ROOT/scripts/skill_library_audit.py" --root "$TMP/lib-nested"
mkdir -p "$TMP/lib-symlink/real/broken" "$TMP/lib-loop/root"
printf -- '---\nname: symlink-hidden\ndescription: ""\n---\n# h\n' > "$TMP/lib-symlink/real/broken/SKILL.md"
ln -s "$TMP/lib-symlink/real" "$TMP/lib-loop/root/external"
ln -s "$TMP/lib-loop/root" "$TMP/lib-loop/root/loop"
expect_exit 2 "skill_library_audit does not traverse directory symlinks or loops" -- python3 "$ROOT/scripts/skill_library_audit.py" --root "$TMP/lib-loop/root"

# 7. skill_library_audit.py must FAIL on duplicate skill names (shadowing).
mkdir -p "$TMP/lib-dup/a/same" "$TMP/lib-dup/b/same"
printf -- '---\nname: same\ndescription: "Use when testing duplicate detection in library audits."\n---\n# s\n' > "$TMP/lib-dup/a/same/SKILL.md"
printf -- '---\nname: same\ndescription: "Use when verifying that shadowed skills are reported as failures."\n---\n# s\n' > "$TMP/lib-dup/b/same/SKILL.md"
expect_exit 1 "skill_library_audit rejects duplicate skill names" -- python3 "$ROOT/scripts/skill_library_audit.py" --root "$TMP/lib-dup"

# 8. block-scalar frontmatter must be PARSED, not read as a literal '>' —
#    proven by an over-1024 block-scalar description that lint must reject.
mkdir -p "$TMP/block-long"
{
  printf -- '---\nname: block-long\ndescription: >\n'
  for _ in $(seq 1 30); do printf '  Use when testing block scalar parsing with a very long folded description line.\n'; done
  printf -- '---\n# t\n'
} > "$TMP/block-long/SKILL.md"
expect_exit 1 "trigger_eval lint parses block scalars (rejects over-length folded description)" -- python3 "$ROOT/scripts/trigger_eval.py" lint --skill "$TMP/block-long"

# 9. Frontmatter accepts portable encodings, preserves folded paragraphs, and
# rejects duplicate routing keys.
mkdir -p "$TMP/frontmatter-bom" "$TMP/frontmatter-cr" "$TMP/frontmatter-fold" "$TMP/frontmatter-dup-name" "$TMP/frontmatter-dup-desc"
printf '\357\273\277---\r\nname: frontmatter-bom\r\ndescription: \"Use when testing BOM and CRLF input.\"\r\n---\r\n# ok\r\n' > "$TMP/frontmatter-bom/SKILL.md"
expect_exit 0 "frontmatter accepts UTF-8 BOM plus CRLF" -- python3 "$ROOT/scripts/trigger_eval.py" lint --skill "$TMP/frontmatter-bom"
printf -- '---\rname: frontmatter-cr\rdescription: "Use when testing classic CR input."\r---\r# ok\r' > "$TMP/frontmatter-cr/SKILL.md"
expect_exit 0 "frontmatter accepts CR line endings" -- python3 "$ROOT/scripts/trigger_eval.py" lint --skill "$TMP/frontmatter-cr"
printf '%s\n' '---' 'name: fold-ok' 'description: >' '  Use when alpha' '  beta.' '' '  Not for gamma.' '---' '# ok' > "$TMP/frontmatter-fold/SKILL.md"
expect_exit 0 "frontmatter preserves folded paragraph boundaries" -- python3 -c 'import sys; sys.path.insert(0, sys.argv[1]); from frontmatter import parse_frontmatter_file; from pathlib import Path; value=parse_frontmatter_file(Path(sys.argv[2]))["description"]; raise SystemExit(0 if value == "Use when alpha beta.\nNot for gamma." else 1)' "$ROOT/scripts" "$TMP/frontmatter-fold/SKILL.md"
printf '%s\n' '---' 'name: first' 'name: second' 'description: "Use when testing duplicates."' '---' > "$TMP/frontmatter-dup-name/SKILL.md"
expect_exit 2 "frontmatter rejects duplicate name keys" -- python3 "$ROOT/scripts/trigger_eval.py" lint --skill "$TMP/frontmatter-dup-name"
printf '%s\n' '---' 'name: duplicate-description' 'description: "Use when testing one."' 'description: "Use when testing two."' '---' > "$TMP/frontmatter-dup-desc/SKILL.md"
expect_exit 2 "frontmatter rejects duplicate description keys" -- python3 "$ROOT/scripts/trigger_eval.py" lint --skill "$TMP/frontmatter-dup-desc"

# 10. spec-invalid `name` must be rejected by both metadata checkers.
mkdir -p "$TMP/bad-name"
printf -- '---\nname: Bad Name!\ndescription: "Use when testing that invalid names are rejected, 测试非法名字."\n---\n# t\n' > "$TMP/bad-name/SKILL.md"
expect_exit 1 "trigger_eval lint rejects a spec-invalid name" -- python3 "$ROOT/scripts/trigger_eval.py" lint --skill "$TMP/bad-name"
expect_exit 1 "validate-skill.sh rejects a spec-invalid name" -- bash "$ROOT/scripts/validate-skill.sh" "$TMP/bad-name"
mkdir -p "$TMP/name-directory-mismatch"
printf -- '---\nname: different-name\ndescription: "Use when testing directory-name validation."\n---\n# t\n' > "$TMP/name-directory-mismatch/SKILL.md"
expect_exit 1 "trigger_eval lint rejects a name/directory mismatch" -- python3 "$ROOT/scripts/trigger_eval.py" lint --skill "$TMP/name-directory-mismatch"
expect_exit 1 "validate-skill.sh rejects a name/directory mismatch" -- bash "$ROOT/scripts/validate-skill.sh" "$TMP/name-directory-mismatch"
mkdir -p "$TMP/name-injection"
printf '%s\n' '---' 'name: |' '  safe' "  \$(touch \"$TMP/validator-owned\")" 'description: "Use when testing hostile metadata."' '---' '# bad' > "$TMP/name-injection/SKILL.md"
expect_exit 1 "validate-skill.sh rejects multiline hostile names" -- bash "$ROOT/scripts/validate-skill.sh" "$TMP/name-injection"
if [[ -e "$TMP/validator-owned" ]]; then
  echo "FAIL  validate-skill.sh executed hostile frontmatter"
  FAIL=$((FAIL + 1))
else
  echo "PASS  validate-skill.sh never executes frontmatter"
  PASS=$((PASS + 1))
fi
mkdir -p "$TMP/workflow-leak"
printf '%s\n' '---' 'name: workflow-leak' 'description: |' '  Use when reviewing changes. First inspect the diff,' '  then publish a report.' '---' '# bad' > "$TMP/workflow-leak/SKILL.md"
expect_exit 1 "trigger_eval lint rejects multiline workflow leaks" -- python3 "$ROOT/scripts/trigger_eval.py" lint --skill "$TMP/workflow-leak"
expect_exit 1 "validate-skill.sh rejects multiline workflow leaks" -- bash "$ROOT/scripts/validate-skill.sh" "$TMP/workflow-leak"

# 11. score must reject PARTIAL holdout coverage (a partial submission could fake a pass).
printf '%s\n' \
  '{"prompt": "a", "expect": "trigger", "kind": "x"}' \
  '{"prompt": "b", "expect": "no", "kind": "y"}' \
  '{"prompt": "c", "expect": "trigger", "kind": "x", "holdout": true}' \
  '{"prompt": "d", "expect": "no", "kind": "y", "holdout": true}' > "$TMP/fix-ho.jsonl"
printf '%s\n' '{"id": 2, "decision": "trigger"}' > "$TMP/judge-partial.jsonl"
expect_exit 2 "trigger_eval score rejects partial holdout coverage" -- python3 "$ROOT/scripts/trigger_eval.py" score --fixture "$TMP/fix-ho.jsonl" --judgments "$TMP/judge-partial.jsonl"

# 11. score must reject duplicate ids (later lines silently overwrote earlier ones).
printf '%s\n' '{"id": 2, "decision": "trigger"}' '{"id": 2, "decision": "no"}' '{"id": 3, "decision": "no"}' > "$TMP/judge-dup.jsonl"
expect_exit 2 "trigger_eval score rejects duplicate judgment ids" -- python3 "$ROOT/scripts/trigger_eval.py" score --fixture "$TMP/fix-ho.jsonl" --judgments "$TMP/judge-dup.jsonl"

# 12. score positive path: complete, correct holdout judgments must PASS.
printf '%s\n' '{"id": 2, "decision": "trigger"}' '{"id": 3, "decision": "no"}' > "$TMP/judge-ok.jsonl"
expect_exit 0 "trigger_eval score passes complete correct holdout judgments" -- python3 "$ROOT/scripts/trigger_eval.py" score --fixture "$TMP/fix-ho.jsonl" --judgments "$TMP/judge-ok.jsonl"
printf '%s\n' '# Worksheet' > "$TMP/worksheet.md"
printf '%s\n' 'existing report target' > "$TMP/trigger-existing-target"
ln -s "$TMP/trigger-existing-target" "$TMP/trigger-report-link.json"
expect_exit 2 "trigger_eval rejects an existing report symlink" -- python3 "$ROOT/scripts/trigger_eval.py" score --fixture "$TMP/fix-ho.jsonl" --judgments "$TMP/judge-ok.jsonl" --worksheet "$TMP/worksheet.md" --report "$TMP/trigger-report-link.json"
ln -s "$TMP/missing-trigger-target" "$TMP/trigger-report-dangling.json"
expect_exit 2 "trigger_eval rejects a dangling report symlink" -- python3 "$ROOT/scripts/trigger_eval.py" score --fixture "$TMP/fix-ho.jsonl" --judgments "$TMP/judge-ok.jsonl" --worksheet "$TMP/worksheet.md" --report "$TMP/trigger-report-dangling.json"

# 13. Combined scoring must not let perfect holdout results hide a train failure.
printf '%s\n' \
  '{"id": 0, "decision": "no"}' \
  '{"id": 1, "decision": "no"}' \
  '{"id": 2, "decision": "trigger"}' \
  '{"id": 3, "decision": "no"}' > "$TMP/judge-train-fail.jsonl"
expect_exit 1 "trigger_eval score rejects train failure even when holdout passes" -- python3 "$ROOT/scripts/trigger_eval.py" score --fixture "$TMP/fix-ho.jsonl" --judgments "$TMP/judge-train-fail.jsonl"

# 14. Partial train, out-of-range ids, malformed lines, and invalid thresholds are usage errors.
printf '%s\n' '{"id": 0, "decision": "trigger"}' > "$TMP/judge-train-partial.jsonl"
expect_exit 2 "trigger_eval score rejects partial train coverage" -- python3 "$ROOT/scripts/trigger_eval.py" score --fixture "$TMP/fix-ho.jsonl" --judgments "$TMP/judge-train-partial.jsonl"
printf '%s\n' '{"id": 99, "decision": "trigger"}' > "$TMP/judge-range.jsonl"
expect_exit 2 "trigger_eval score rejects out-of-range ids" -- python3 "$ROOT/scripts/trigger_eval.py" score --fixture "$TMP/fix-ho.jsonl" --judgments "$TMP/judge-range.jsonl"
printf '%s\n' '{"id": "broken"}' > "$TMP/judge-malformed.jsonl"
expect_exit 2 "trigger_eval score rejects malformed judgments" -- python3 "$ROOT/scripts/trigger_eval.py" score --fixture "$TMP/fix-ho.jsonl" --judgments "$TMP/judge-malformed.jsonl"
expect_exit 2 "trigger_eval score rejects invalid accuracy thresholds" -- python3 "$ROOT/scripts/trigger_eval.py" score --fixture "$TMP/fix-ho.jsonl" --judgments "$TMP/judge-ok.jsonl" --min-accuracy 101

# Citation policy comes from a generic external blocklist and must respect boundaries.
printf '%s\n' '# Project-private names' 'internal-review-pro' > "$TMP/citation-blocklist.txt"
mkdir -p "$TMP/cite-bad"
printf -- '---\nname: t\ndescription: "Use when testing."\n---\n# t\nAs the internal-review-pro skill shows, this works.\n' > "$TMP/cite-bad/SKILL.md"
expect_exit 1 "citation_lint applies an external blocklist" -- python3 "$ROOT/scripts/citation_lint.py" --skill "$TMP/cite-bad" --blocklist "$TMP/citation-blocklist.txt"
mkdir -p "$TMP/cite-ok"
printf -- '---\nname: t\ndescription: "Use when testing."\n---\n# t\nThe internal-review-prototype label is unrelated.\n' > "$TMP/cite-ok/SKILL.md"
expect_exit 0 "citation_lint ignores blocked names embedded in longer words" -- python3 "$ROOT/scripts/citation_lint.py" --skill "$TMP/cite-ok" --blocklist "$TMP/citation-blocklist.txt"

# 16. References may mention peers, but required peer loads must fail validation.
mkdir -p "$TMP/ref-dep/references"
printf -- '---\nname: ref-dep\ndescription: "Use when testing standalone reference validation."\n---\n# t\n## Outcome Contract\n## Hard Rules\n## Gotchas\n`references/a.md` `references/b.md`\n' > "$TMP/ref-dep/SKILL.md"
printf '%s\n' '# A' 'Read `b.md` before using this file.' > "$TMP/ref-dep/references/a.md"
printf '%s\n' '# B' 'Standalone facts.' > "$TMP/ref-dep/references/b.md"
expect_exit 1 "validate-skill.sh rejects a required reference peer load" -- bash "$ROOT/scripts/validate-skill.sh" "$TMP/ref-dep"
printf '%s\n' '# A' 'Optional further reading: [B](b.md).' > "$TMP/ref-dep/references/a.md"
expect_exit 0 "validate-skill.sh allows optional reference peer links" -- bash "$ROOT/scripts/validate-skill.sh" "$TMP/ref-dep"

# 17. Evidence manifests must verify, reject overwrite, and detect tampering.
mkdir -p "$TMP/evidence"
printf '%s\n' '# Task' 'Create a compact test artifact.' > "$TMP/evidence/task.md"
printf '%s\n' '# Baseline' 'Default output.' > "$TMP/evidence/baseline.md"
printf '%s\n' '# With skill' 'Constrained output.' > "$TMP/evidence/with_skill.md"
cp "$TMP/evidence/baseline.md" "$TMP/evidence/candidate-a.md"
cp "$TMP/evidence/with_skill.md" "$TMP/evidence/candidate-b.md"
printf '%s\n' '# Judge' 'Compare A and B against the rubric.' > "$TMP/evidence/judge-prompt.md"
printf '%s\n' '{"A":"baseline","B":"with_skill"}' > "$TMP/evidence/mapping.json"
printf '%s\n' '# Verdict' 'B meets more criteria.' > "$TMP/evidence/verdict.md"
cat > "$TMP/evidence/runs.json" <<'JSON'
{
  "schema": "yw-skill-foundry.runs/v1",
  "evaluation_level": "exploratory",
  "metrics_status": "unavailable",
  "metrics_unavailable_reason": "self-check fixture does not execute real models",
  "runs": [
    {"id":"b1","configuration":"baseline","run_number":1,"model":"fixture-model","output":"baseline.md"},
    {"id":"s1","configuration":"with_skill","run_number":1,"model":"fixture-model","output":"with_skill.md"}
  ]
}
JSON
cat > "$TMP/evidence/judges.json" <<'JSON'
{
  "schema": "yw-skill-foundry.judges/v1",
  "judges": [
    {
      "id":"j1",
      "model":"fixture-judge",
      "run_number":1,
      "candidate_a":"baseline",
      "candidate_b":"with_skill",
      "candidate_a_file":"candidate-a.md",
      "candidate_b_file":"candidate-b.md",
      "prompt_file":"judge-prompt.md",
      "evidence_file":"verdict.md",
      "verdict":"with_skill"
    }
  ]
}
JSON
expect_exit 0 "evidence.py creates a manifest" -- python3 "$ROOT/scripts/evidence.py" create "$TMP/evidence" --skill "$ROOT"
expect_exit 0 "evidence.py verifies untampered artifacts" -- python3 "$ROOT/scripts/evidence.py" verify "$TMP/evidence"
expect_exit 1 "evidence.py refuses to overwrite an evidence run" -- python3 "$ROOT/scripts/evidence.py" create "$TMP/evidence" --skill "$ROOT"
printf '%s\n' 'outside target' > "$TMP/existing-output-target"
cp -R "$TMP/evidence" "$TMP/evidence-manifest-link"
rm -f "$TMP/evidence-manifest-link/manifest.json" "$TMP/evidence-manifest-link/skill-snapshot.md"
ln -s "$TMP/existing-output-target" "$TMP/evidence-manifest-link/manifest.json"
expect_exit 1 "evidence.py rejects an existing manifest symlink" -- python3 "$ROOT/scripts/evidence.py" create "$TMP/evidence-manifest-link" --skill "$ROOT"
cp -R "$TMP/evidence" "$TMP/evidence-manifest-dangling"
rm -f "$TMP/evidence-manifest-dangling/manifest.json" "$TMP/evidence-manifest-dangling/skill-snapshot.md"
ln -s "$TMP/missing-manifest-target" "$TMP/evidence-manifest-dangling/manifest.json"
expect_exit 1 "evidence.py rejects a dangling manifest symlink" -- python3 "$ROOT/scripts/evidence.py" create "$TMP/evidence-manifest-dangling" --skill "$ROOT"
cp -R "$TMP/evidence" "$TMP/evidence-snapshot-link"
rm -f "$TMP/evidence-snapshot-link/manifest.json" "$TMP/evidence-snapshot-link/skill-snapshot.md"
ln -s "$TMP/existing-output-target" "$TMP/evidence-snapshot-link/skill-snapshot.md"
expect_exit 1 "evidence.py rejects an existing snapshot symlink" -- python3 "$ROOT/scripts/evidence.py" create "$TMP/evidence-snapshot-link" --skill "$ROOT"
cp -R "$TMP/evidence" "$TMP/evidence-snapshot-dangling"
rm -f "$TMP/evidence-snapshot-dangling/manifest.json" "$TMP/evidence-snapshot-dangling/skill-snapshot.md"
ln -s "$TMP/missing-snapshot-target" "$TMP/evidence-snapshot-dangling/skill-snapshot.md"
expect_exit 1 "evidence.py rejects a dangling snapshot symlink" -- python3 "$ROOT/scripts/evidence.py" create "$TMP/evidence-snapshot-dangling" --skill "$ROOT"
mkdir -p "$TMP/evidence-prod"
for name in task.md baseline.md with_skill.md candidate-a.md candidate-b.md judge-prompt.md mapping.json verdict.md runs.json judges.json; do
  cp "$TMP/evidence/$name" "$TMP/evidence-prod/$name"
done
python3 - "$TMP/evidence-prod/runs.json" <<'PYEOF'
import json, sys
from pathlib import Path
path = Path(sys.argv[1])
doc = json.loads(path.read_text())
doc["evaluation_level"] = "production"
path.write_text(json.dumps(doc))
PYEOF
expect_exit 1 "evidence.py rejects production runs without repeats and position swap" -- python3 "$ROOT/scripts/evidence.py" create "$TMP/evidence-prod" --skill "$ROOT"
mkdir -p "$TMP/evidence-mismatch"
for name in task.md baseline.md with_skill.md candidate-a.md candidate-b.md judge-prompt.md mapping.json verdict.md runs.json judges.json; do
  cp "$TMP/evidence/$name" "$TMP/evidence-mismatch/$name"
done
printf '%s\n' 'wrong candidate bytes' > "$TMP/evidence-mismatch/candidate-a.md"
expect_exit 1 "evidence.py rejects blind candidates that do not match source outputs" -- python3 "$ROOT/scripts/evidence.py" create "$TMP/evidence-mismatch" --skill "$ROOT"
printf '%s\n' 'tampered' >> "$TMP/evidence/baseline.md"
expect_exit 1 "evidence.py detects artifact tampering" -- python3 "$ROOT/scripts/evidence.py" verify "$TMP/evidence"

# 18. A valid Production fixture must bind unique runs, contracts, judges, and paths.
PROD="$TMP/evidence-production"
mkdir -p "$PROD"
printf '%s\n' '# Task' 'Create a fixture.' > "$PROD/task.md"
printf '%s\n' 'OK baseline one' > "$PROD/baseline-1.md"
printf '%s\n' 'OK baseline two' > "$PROD/baseline-2.md"
printf '%s\n' 'OK with skill one' > "$PROD/with-skill-1.md"
printf '%s\n' 'OK with skill two' > "$PROD/with-skill-2.md"
cp "$PROD/baseline-1.md" "$PROD/r1-a.md"
cp "$PROD/with-skill-1.md" "$PROD/r1-b.md"
cp "$PROD/with-skill-1.md" "$PROD/r1-swap-a.md"
cp "$PROD/baseline-1.md" "$PROD/r1-swap-b.md"
cp "$PROD/baseline-2.md" "$PROD/r2-a.md"
cp "$PROD/with-skill-2.md" "$PROD/r2-b.md"
cp "$PROD/with-skill-2.md" "$PROD/r2-swap-a.md"
cp "$PROD/baseline-2.md" "$PROD/r2-swap-b.md"
printf '%s\n' '# Judge' 'Use the contract.' > "$PROD/judge-prompt.md"
printf '%s\n' '{"A":"baseline","B":"with_skill"}' > "$PROD/mapping.json"
printf '%s\n' '# Verdict' 'with_skill wins.' > "$PROD/verdict.md"
printf '%s\n' '{"schema":"yw-skill-foundry.contract/v1","checks":[{"id":"ok","type":"contains","value":"OK"}]}' > "$PROD/contract.json"
printf '%s\n' '{}' > "$PROD/manual.json"
for pair in "baseline-1 contract-b1" "baseline-2 contract-b2" "with-skill-1 contract-s1" "with-skill-2 contract-s2"; do
  set -- $pair
  expect_exit 0 "contract_eval creates bound report $2" -- python3 "$ROOT/scripts/contract_eval.py" --contract "$PROD/contract.json" --output "$PROD/$1.md" --manual-results "$PROD/manual.json" --report "$PROD/$2.json"
done
for name in judge-r1 judge-r1-swap judge-r2 judge-r2-swap; do
  printf '%s\n' '# Judge verdict' 'with_skill.' > "$PROD/$name.md"
done
for number in 1 2; do
  printf '%s\n' \
    '{"prompt":"review this diff","expect":"trigger","kind":"positive"}' \
    '{"prompt":"write release notes","expect":"no","kind":"negative"}' \
    '{"prompt":"check branch before merge","expect":"trigger","kind":"positive","holdout":true}' \
    '{"prompt":"polish this prose","expect":"no","kind":"negative","holdout":true}' > "$PROD/routing-$number.jsonl"
  printf '%s\n' \
    '{"id":0,"decision":"trigger"}' \
    '{"id":1,"decision":"no"}' \
    '{"id":2,"decision":"trigger"}' \
    '{"id":3,"decision":"no"}' > "$PROD/routing-judgments-$number.jsonl"
  printf '%s\n' '# Worksheet' 'Four unlabeled prompts.' > "$PROD/routing-worksheet-$number.md"
  expect_exit 0 "trigger_eval creates bound routing report $number" -- python3 "$ROOT/scripts/trigger_eval.py" score --fixture "$PROD/routing-$number.jsonl" --judgments "$PROD/routing-judgments-$number.jsonl" --worksheet "$PROD/routing-worksheet-$number.md" --report "$PROD/routing-report-$number.json"
done
cat > "$PROD/runs.json" <<'JSON'
{
  "schema":"yw-skill-foundry.runs/v1",
  "evaluation_level":"production",
  "metrics_status":"unavailable",
  "metrics_unavailable_reason":"fixture",
  "runs":[
    {"id":"b1","configuration":"baseline","run_number":1,"model":"fixture-model","output":"baseline-1.md","contract_file":"contract.json","manual_results_file":"manual.json","contract_report":"contract-b1.json","contract_passed":true},
    {"id":"b2","configuration":"baseline","run_number":2,"model":"fixture-model","output":"baseline-2.md","contract_file":"contract.json","manual_results_file":"manual.json","contract_report":"contract-b2.json","contract_passed":true},
    {"id":"s1","configuration":"with_skill","run_number":1,"model":"fixture-model","output":"with-skill-1.md","contract_file":"contract.json","manual_results_file":"manual.json","contract_report":"contract-s1.json","contract_passed":true,"routing_fixture":"routing-1.jsonl","routing_judgments":"routing-judgments-1.jsonl","routing_worksheet":"routing-worksheet-1.md","routing_report":"routing-report-1.json","routing_passed":true},
    {"id":"s2","configuration":"with_skill","run_number":2,"model":"fixture-model","output":"with-skill-2.md","contract_file":"contract.json","manual_results_file":"manual.json","contract_report":"contract-s2.json","contract_passed":true,"routing_fixture":"routing-2.jsonl","routing_judgments":"routing-judgments-2.jsonl","routing_worksheet":"routing-worksheet-2.md","routing_report":"routing-report-2.json","routing_passed":true}
  ]
}
JSON
cat > "$PROD/judges.json" <<'JSON'
{
  "schema":"yw-skill-foundry.judges/v1",
  "judges":[
    {"id":"j1","model":"fixture-judge","run_number":1,"candidate_a":"baseline","candidate_b":"with_skill","candidate_a_file":"r1-a.md","candidate_b_file":"r1-b.md","prompt_file":"judge-prompt.md","evidence_file":"judge-r1.md","verdict":"with_skill"},
    {"id":"j2","model":"fixture-judge","run_number":1,"candidate_a":"with_skill","candidate_b":"baseline","candidate_a_file":"r1-swap-a.md","candidate_b_file":"r1-swap-b.md","prompt_file":"judge-prompt.md","evidence_file":"judge-r1-swap.md","verdict":"with_skill"},
    {"id":"j3","model":"fixture-judge","run_number":2,"candidate_a":"baseline","candidate_b":"with_skill","candidate_a_file":"r2-a.md","candidate_b_file":"r2-b.md","prompt_file":"judge-prompt.md","evidence_file":"judge-r2.md","verdict":"with_skill"},
    {"id":"j4","model":"fixture-judge","run_number":2,"candidate_a":"with_skill","candidate_b":"baseline","candidate_a_file":"r2-swap-a.md","candidate_b_file":"r2-swap-b.md","prompt_file":"judge-prompt.md","evidence_file":"judge-r2-swap.md","verdict":"with_skill"}
  ]
}
JSON
expect_exit 0 "evidence.py accepts a fully bound Production run" -- python3 "$ROOT/scripts/evidence.py" create "$PROD" --skill "$ROOT"
expect_exit 0 "evidence.py verifies a fully bound Production run" -- python3 "$ROOT/scripts/evidence.py" verify "$PROD"
expect_exit 0 "new protocol artifacts emit yw-skill-foundry schemas" -- python3 - "$PROD" <<'PYEOF'
import json
import sys
from pathlib import Path

root = Path(sys.argv[1])
expected = {
    "manifest.json": "yw-skill-foundry.run-compare/v2",
    "contract.json": "yw-skill-foundry.contract/v1",
    "runs.json": "yw-skill-foundry.runs/v1",
    "judges.json": "yw-skill-foundry.judges/v1",
}
for path in root.glob("contract-*.json"):
    expected[path.name] = "yw-skill-foundry.contract-result/v2"
for path in root.glob("routing-report-*.json"):
    expected[path.name] = "yw-skill-foundry.routing-result/v1"
for name, schema in expected.items():
    actual = json.loads((root / name).read_text()).get("schema")
    if actual != schema:
        raise SystemExit(f"{name} emitted {actual!r}, expected {schema!r}")
PYEOF

for legacy_prefix in skill-foundry skill-craft; do
  legacy_dir="$TMP/evidence-legacy-$legacy_prefix"
  cp -R "$PROD" "$legacy_dir"
  python3 - "$legacy_dir" "$legacy_prefix" <<'PYEOF'
import hashlib
import json
import sys
from pathlib import Path

root = Path(sys.argv[1])
prefix = sys.argv[2]
updates = {
    "runs.json": f"{prefix}.runs/v1",
    "judges.json": f"{prefix}.judges/v1",
    "contract.json": f"{prefix}.contract/v1",
}
for path in root.glob("contract-*.json"):
    updates[path.name] = f"{prefix}.contract-result/v2"
for path in root.glob("routing-report-*.json"):
    updates[path.name] = f"{prefix}.routing-result/v1"
for name, schema in updates.items():
    path = root / name
    doc = json.loads(path.read_text())
    doc["schema"] = schema
    path.write_text(json.dumps(doc, sort_keys=True) + "\n")

contract_hash = hashlib.sha256((root / "contract.json").read_bytes()).hexdigest()
for path in root.glob("contract-*.json"):
    doc = json.loads(path.read_text())
    doc["inputs"]["contract"]["sha256"] = contract_hash
    path.write_text(json.dumps(doc, sort_keys=True) + "\n")

manifest_path = root / "manifest.json"
manifest = json.loads(manifest_path.read_text())
manifest["schema"] = f"{prefix}.run-compare/v2"
for name in updates:
    data = (root / name).read_bytes()
    manifest["files"][name] = {
        "sha256": hashlib.sha256(data).hexdigest(),
        "bytes": len(data),
    }
manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
PYEOF
  expect_exit 0 "evidence.py accepts legacy $legacy_prefix schemas" -- python3 "$ROOT/scripts/evidence.py" verify "$legacy_dir"
done

cp -R "$PROD" "$TMP/evidence-duplicate-run"
rm -f "$TMP/evidence-duplicate-run/manifest.json" "$TMP/evidence-duplicate-run/skill-snapshot.md"
python3 - "$TMP/evidence-duplicate-run/runs.json" <<'PYEOF'
import hashlib, json, sys
from pathlib import Path
path = Path(sys.argv[1])
doc = json.loads(path.read_text())
doc["runs"][1]["output"] = doc["runs"][0]["output"]
path.write_text(json.dumps(doc))
report_path = path.parent / "contract-b2.json"
report = json.loads(report_path.read_text())
report["inputs"]["output"]["path"] = "baseline-1.md"
report["inputs"]["output"]["sha256"] = hashlib.sha256(
    (path.parent / "baseline-1.md").read_bytes()
).hexdigest()
report_path.write_text(json.dumps(report))
PYEOF
cp "$TMP/evidence-duplicate-run/baseline-1.md" "$TMP/evidence-duplicate-run/r2-a.md"
cp "$TMP/evidence-duplicate-run/baseline-1.md" "$TMP/evidence-duplicate-run/r2-swap-b.md"
expect_exit 1 "evidence.py rejects Production output reuse" -- python3 "$ROOT/scripts/evidence.py" create "$TMP/evidence-duplicate-run" --skill "$ROOT"

cp -R "$PROD" "$TMP/evidence-model-mismatch"
rm -f "$TMP/evidence-model-mismatch/manifest.json" "$TMP/evidence-model-mismatch/skill-snapshot.md"
python3 - "$TMP/evidence-model-mismatch/runs.json" <<'PYEOF'
import json, sys
from pathlib import Path
path = Path(sys.argv[1])
doc = json.loads(path.read_text())
doc["runs"][0]["model"] = "model-a"
doc["runs"][1]["model"] = "model-b"
doc["runs"][2]["model"] = "model-b"
doc["runs"][3]["model"] = "model-a"
path.write_text(json.dumps(doc))
PYEOF
expect_exit 1 "evidence.py rejects per-pair model mismatch" -- python3 "$ROOT/scripts/evidence.py" create "$TMP/evidence-model-mismatch" --skill "$ROOT"

cp -R "$PROD" "$TMP/evidence-duplicate-judge"
rm -f "$TMP/evidence-duplicate-judge/manifest.json" "$TMP/evidence-duplicate-judge/skill-snapshot.md"
python3 - "$TMP/evidence-duplicate-judge/judges.json" <<'PYEOF'
import json, sys
from pathlib import Path
path = Path(sys.argv[1])
doc = json.loads(path.read_text())
doc["judges"][1]["evidence_file"] = doc["judges"][0]["evidence_file"]
path.write_text(json.dumps(doc))
PYEOF
expect_exit 1 "evidence.py rejects judge evidence reuse" -- python3 "$ROOT/scripts/evidence.py" create "$TMP/evidence-duplicate-judge" --skill "$ROOT"

cp -R "$PROD" "$TMP/evidence-forged-contract"
rm -f "$TMP/evidence-forged-contract/manifest.json" "$TMP/evidence-forged-contract/skill-snapshot.md"
python3 - "$TMP/evidence-forged-contract/contract-s1.json" <<'PYEOF'
import json, sys
from pathlib import Path
path = Path(sys.argv[1])
doc = json.loads(path.read_text())
doc["inputs"]["output"]["sha256"] = "0" * 64
path.write_text(json.dumps(doc))
PYEOF
expect_exit 1 "evidence.py rejects a forged contract report" -- python3 "$ROOT/scripts/evidence.py" create "$TMP/evidence-forged-contract" --skill "$ROOT"

cp -R "$PROD" "$TMP/evidence-semantic-forgery"
rm -f "$TMP/evidence-semantic-forgery/manifest.json" "$TMP/evidence-semantic-forgery/skill-snapshot.md"
python3 - "$TMP/evidence-semantic-forgery" <<'PYEOF'
import hashlib, json, sys
from pathlib import Path
root = Path(sys.argv[1])
contract_path = root / "contract.json"
contract = json.loads(contract_path.read_text())
contract["checks"][0]["value"] = "MISSING"
contract_path.write_text(json.dumps(contract))
contract_hash = hashlib.sha256(contract_path.read_bytes()).hexdigest()
for report_path in root.glob("contract-*.json"):
    report = json.loads(report_path.read_text())
    report["inputs"]["contract"]["sha256"] = contract_hash
    report_path.write_text(json.dumps(report))
PYEOF
expect_exit 1 "evidence.py re-evaluates contract semantics" -- python3 "$ROOT/scripts/evidence.py" create "$TMP/evidence-semantic-forgery" --skill "$ROOT"

cp -R "$PROD" "$TMP/evidence-routing-forgery"
rm -f "$TMP/evidence-routing-forgery/manifest.json" "$TMP/evidence-routing-forgery/skill-snapshot.md"
python3 - "$TMP/evidence-routing-forgery/routing-report-1.json" <<'PYEOF'
import json, sys
from pathlib import Path
path = Path(sys.argv[1])
report = json.loads(path.read_text())
report["phases"]["overall"]["correct"] = 0
path.write_text(json.dumps(report))
PYEOF
expect_exit 1 "evidence.py re-evaluates routing semantics" -- python3 "$ROOT/scripts/evidence.py" create "$TMP/evidence-routing-forgery" --skill "$ROOT"

cp -R "$PROD" "$TMP/evidence-routing-threshold"
rm -f "$TMP/evidence-routing-threshold/manifest.json" "$TMP/evidence-routing-threshold/skill-snapshot.md"
python3 - "$TMP/evidence-routing-threshold" <<'PYEOF'
import hashlib, json, sys
from pathlib import Path
root = Path(sys.argv[1])
judgments_path = root / "routing-judgments-1.jsonl"
rows = [json.loads(line) for line in judgments_path.read_text().splitlines()]
rows[0]["decision"] = "no"
judgments_path.write_text("\n".join(json.dumps(row) for row in rows) + "\n")
report_path = root / "routing-report-1.json"
report = json.loads(report_path.read_text())
report["inputs"]["judgments"]["sha256"] = hashlib.sha256(
    judgments_path.read_bytes()
).hexdigest()
report["min_accuracy"] = -1
report["phases"]["overall"]["correct"] = 3
report["phases"]["train"]["correct"] = 1
report["by_kind"]["positive"]["correct"] = 1
report["under_trigger_ids"] = [0]
report_path.write_text(json.dumps(report))
PYEOF
expect_exit 1 "evidence.py rejects forged routing thresholds outside 0-100" -- python3 "$ROOT/scripts/evidence.py" create "$TMP/evidence-routing-threshold" --skill "$ROOT"

cp -R "$PROD" "$TMP/evidence-symlink"
cp "$TMP/evidence-symlink/baseline-2.md" "$TMP/outside-output.md"
rm -f "$TMP/evidence-symlink/manifest.json" "$TMP/evidence-symlink/skill-snapshot.md" "$TMP/evidence-symlink/baseline-2.md"
ln -s "$TMP/outside-output.md" "$TMP/evidence-symlink/baseline-2.md"
python3 - "$TMP/evidence-symlink/contract-b2.json" <<'PYEOF'
import hashlib, json, sys
from pathlib import Path
path = Path(sys.argv[1])
report = json.loads(path.read_text())
report["inputs"]["output"]["path"] = "../outside-output.md"
report["inputs"]["output"]["sha256"] = hashlib.sha256(
    (path.parent.parent / "outside-output.md").read_bytes()
).hexdigest()
path.write_text(json.dumps(report))
PYEOF
expect_exit 1 "evidence.py rejects artifacts that escape through symlinks" -- python3 "$ROOT/scripts/evidence.py" create "$TMP/evidence-symlink" --skill "$ROOT"

# 19. Contract eval must distinguish deterministic fail, manual fail, and incomplete grading.
cat > "$TMP/contract.json" <<'JSON'
{
  "schema": "yw-skill-foundry.contract/v1",
  "checks": [
    {"id": "header", "type": "contains", "value": "## Findings"},
    {"id": "citation", "type": "regex", "pattern": "[A-Za-z0-9_./-]+:[0-9]+"},
    {"id": "no-todo", "type": "not_regex", "pattern": "\\bTODO\\b"}
  ],
  "manual_checks": [
    {"id": "actionable", "description": "The finding names a concrete failure path."}
  ]
}
JSON
printf '%s\n' '## Findings' '- [P1] Crash — src/app.py:42' 'Input X reaches a null dereference.' > "$TMP/contract-output.md"
printf '%s\n' '{"actionable":{"passed":true,"evidence":"The finding names input X and its consequence."}}' > "$TMP/manual-pass.json"
printf '%s\n' '{"actionable":{"passed":false,"evidence":"The consequence is not established."}}' > "$TMP/manual-fail.json"
expect_exit 2 "contract_eval rejects incomplete manual grading" -- python3 "$ROOT/scripts/contract_eval.py" --contract "$TMP/contract.json" --output "$TMP/contract-output.md"
expect_exit 0 "contract_eval passes complete deterministic and manual checks" -- python3 "$ROOT/scripts/contract_eval.py" --contract "$TMP/contract.json" --output "$TMP/contract-output.md" --manual-results "$TMP/manual-pass.json"
expect_exit 1 "contract_eval propagates a manual contract failure" -- python3 "$ROOT/scripts/contract_eval.py" --contract "$TMP/contract.json" --output "$TMP/contract-output.md" --manual-results "$TMP/manual-fail.json"
for legacy_prefix in skill-foundry skill-craft; do
  legacy_contract="$TMP/contract-$legacy_prefix.json"
  python3 - "$TMP/contract.json" "$legacy_contract" "$legacy_prefix" <<'PYEOF'
import json
import sys
from pathlib import Path

source, target = Path(sys.argv[1]), Path(sys.argv[2])
doc = json.loads(source.read_text())
doc["schema"] = f"{sys.argv[3]}.contract/v1"
target.write_text(json.dumps(doc) + "\n")
PYEOF
  expect_exit 0 "contract_eval accepts legacy $legacy_prefix schema" -- python3 "$ROOT/scripts/contract_eval.py" --contract "$legacy_contract" --output "$TMP/contract-output.md" --manual-results "$TMP/manual-pass.json"
done
printf '%s\n' '## Findings' 'TODO: add a real citation' > "$TMP/contract-bad.md"
expect_exit 1 "contract_eval rejects deterministic contract failures" -- python3 "$ROOT/scripts/contract_eval.py" --contract "$TMP/contract.json" --output "$TMP/contract-bad.md" --manual-results "$TMP/manual-pass.json"
printf '%s\n' '{"schema":"yw-skill-foundry.contract/v1","checks":[{"id":"bounded","type":"contains","value":"x","min_matches":1,"max_matches":1}]}' > "$TMP/contract-max.json"
printf '%s\n' 'xxx' > "$TMP/contract-too-many.txt"
expect_exit 1 "contract_eval enforces contains max_matches" -- python3 "$ROOT/scripts/contract_eval.py" --contract "$TMP/contract-max.json" --output "$TMP/contract-too-many.txt"
printf '%s\n' 'existing report target' > "$TMP/contract-existing-target"
ln -s "$TMP/contract-existing-target" "$TMP/contract-report-link.json"
expect_exit 2 "contract_eval rejects an existing report symlink" -- python3 "$ROOT/scripts/contract_eval.py" --contract "$TMP/contract.json" --output "$TMP/contract-output.md" --manual-results "$TMP/manual-pass.json" --report "$TMP/contract-report-link.json"
ln -s "$TMP/missing-contract-target" "$TMP/contract-report-dangling.json"
expect_exit 2 "contract_eval rejects a dangling report symlink" -- python3 "$ROOT/scripts/contract_eval.py" --contract "$TMP/contract.json" --output "$TMP/contract-output.md" --manual-results "$TMP/manual-pass.json" --report "$TMP/contract-report-dangling.json"
cp "$TMP/contract-output.md" "$TMP/contract-output-before.md"
expect_exit 2 "contract_eval refuses to overwrite an input with its report" -- python3 "$ROOT/scripts/contract_eval.py" --contract "$TMP/contract.json" --output "$TMP/contract-output.md" --manual-results "$TMP/manual-pass.json" --report "$TMP/contract-output.md"
if cmp -s "$TMP/contract-output.md" "$TMP/contract-output-before.md"; then
  echo "PASS  contract_eval preserved input bytes"
  PASS=$((PASS + 1))
else
  echo "FAIL  contract_eval overwrote an input"
  FAIL=$((FAIL + 1))
fi

# 20. Monolingual descriptions are valid by default and strict only when requested.
mkdir -p "$TMP/mono"
printf -- '---\nname: mono\ndescription: "Use when reviewing database migrations before deployment."\n---\n# m\n' > "$TMP/mono/SKILL.md"
expect_exit 0 "trigger_eval lint allows observed monolingual audiences" -- python3 "$ROOT/scripts/trigger_eval.py" lint --skill "$TMP/mono"
expect_exit 1 "trigger_eval lint can enforce bilingual coverage explicitly" -- python3 "$ROOT/scripts/trigger_eval.py" lint --skill "$TMP/mono" --require-bilingual

# 21. Release packaging must never overwrite files or follow output symlinks.
mkdir -p "$TMP/package-existing"
printf '%s\n' 'keep me' > "$TMP/package-existing/yw-skill-foundry-$RELEASE_VERSION.tar.gz"
expect_exit 2 "package-release refuses to overwrite an existing archive" -- python3 "$ROOT/scripts/package-release.py" --source-mode working-tree --output-dir "$TMP/package-existing"
mkdir -p "$TMP/package-link"
printf '%s\n' 'outside archive' > "$TMP/outside-archive"
ln -s "$TMP/outside-archive" "$TMP/package-link/yw-skill-foundry-$RELEASE_VERSION.tar.gz"
expect_exit 2 "package-release rejects an existing archive symlink" -- python3 "$ROOT/scripts/package-release.py" --source-mode working-tree --output-dir "$TMP/package-link"
mkdir -p "$TMP/package-dangling"
ln -s "$TMP/missing-archive" "$TMP/package-dangling/yw-skill-foundry-$RELEASE_VERSION.tar.gz"
expect_exit 2 "package-release rejects a dangling archive symlink" -- python3 "$ROOT/scripts/package-release.py" --source-mode working-tree --output-dir "$TMP/package-dangling"
mkdir -p "$TMP/package-first" "$TMP/package-second"
expect_exit 0 "package-release builds allowlisted archives" -- python3 "$ROOT/scripts/package-release.py" --source-mode working-tree --output-dir "$TMP/package-first"
expect_exit 0 "package-release repeats deterministically" -- python3 "$ROOT/scripts/package-release.py" --source-mode working-tree --output-dir "$TMP/package-second"
expect_exit 0 "package-release archives are deterministic and private-safe" -- python3 - "$ROOT" "$TMP/package-first" "$TMP/package-second" "$RELEASE_VERSION" <<'PYEOF'
import sys
import tarfile
import zipfile
from pathlib import Path

root = Path(sys.argv[1])
first = Path(sys.argv[2])
second = Path(sys.argv[3])
version = sys.argv[4]
prefix = f"yw-skill-foundry-{version}"
for suffix in (".tar.gz", ".zip"):
    left = first / f"{prefix}{suffix}"
    right = second / f"{prefix}{suffix}"
    if left.read_bytes() != right.read_bytes():
        raise SystemExit(f"archive is not deterministic: {left.name}")
    if suffix == ".zip":
        with zipfile.ZipFile(left) as archive:
            names = archive.namelist()
    else:
        with tarfile.open(left, "r:gz") as archive:
            names = archive.getnames()
    if any("/.github/" in name or name.endswith("/.gitignore") for name in names):
        raise SystemExit(f"developer configuration leaked into {left.name}")
    if f"{prefix}/PRIVACY.md" not in names:
        raise SystemExit(f"privacy policy missing from {left.name}")
PYEOF
expect_exit 0 "package allowlist excludes unknown files and rejects private ones" -- python3 - "$ROOT" <<'PYEOF'
import importlib.util
import io
import sys
import zipfile
from pathlib import Path

scripts = Path(sys.argv[1]) / "scripts"
sys.path.insert(0, str(scripts))
spec = importlib.util.spec_from_file_location(
    "package_release", scripts / "package-release.py"
)
if spec is None or spec.loader is None:
    raise SystemExit("cannot load package-release.py")
package_release = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = package_release
spec.loader.exec_module(package_release)

ArchiveEntry = package_release.ArchiveEntry
PackageError = package_release.PackageError
RELEASE_FILES = package_release.RELEASE_FILES
archive_payloads = package_release.archive_payloads
load_release = package_release.load_release
release_version = package_release.release_version
select_release_entries = package_release.select_release_entries

def source_entries(version):
    return [
        ArchiveEntry(
            name,
            (version + "\n").encode() if name == "VERSION" else b"public\n",
            0o644,
        )
        for name in RELEASE_FILES
    ]

base = source_entries("2.0.0")
selected = select_release_entries(
    base + [ArchiveEntry("references/unlisted-public.md", b"public\n", 0o644)]
)
if "references/unlisted-public.md" in {entry.relative for entry in selected}:
    raise SystemExit("unknown file entered release allowlist")
try:
    select_release_entries(
        base + [ArchiveEntry("references/private.db", b"", 0o644)]
    )
except PackageError:
    pass
else:
    raise SystemExit("privacy-violating file inside allowed directory was accepted")

original_tracked = package_release.tracked_entries
original_worktree = package_release.working_tree_entries
try:
    package_release.tracked_entries = lambda root: source_entries("2.3.4")
    package_release.working_tree_entries = lambda root: source_entries("5.6.7")
    for mode, expected in (("tracked", "2.3.4"), ("working-tree", "5.6.7")):
        mode_entries, version = load_release(Path("."), mode)
        if version != expected:
            raise SystemExit(f"{mode} used {version!r}, expected selected {expected!r}")
        payloads = archive_payloads(mode_entries, version)
        prefix = f"yw-skill-foundry-{expected}"
        if set(payloads) != {f"{prefix}.tar.gz", f"{prefix}.zip"}:
            raise SystemExit(f"{mode} archive filenames did not use selected VERSION")
        with zipfile.ZipFile(io.BytesIO(payloads[f"{prefix}.zip"])) as archive:
            if not all(name.startswith(prefix + "/") for name in archive.namelist()):
                raise SystemExit(f"{mode} archive root did not use selected VERSION")
finally:
    package_release.tracked_entries = original_tracked
    package_release.working_tree_entries = original_worktree

for invalid in (b"", b"v2.0.0\n", b"2.0\n", b"2.0.0-private\n"):
    try:
        release_version([ArchiveEntry("VERSION", invalid, 0o644)])
    except PackageError:
        pass
    else:
        raise SystemExit(f"invalid selected VERSION was accepted: {invalid!r}")
PYEOF
expect_exit 0 "privacy_lint accepts final tar archive" -- python3 "$ROOT/scripts/privacy_lint.py" --archive "$TMP/package-first/yw-skill-foundry-$RELEASE_VERSION.tar.gz"
expect_exit 0 "privacy_lint accepts final zip archive" -- python3 "$ROOT/scripts/privacy_lint.py" --archive "$TMP/package-first/yw-skill-foundry-$RELEASE_VERSION.zip"
expect_exit 0 "atomic publishers reject raced-in destinations" -- python3 - "$ROOT" "$TMP" <<'PYEOF'
import json
import sys
from pathlib import Path

root = Path(sys.argv[1])
tmp = Path(sys.argv[2])
sys.path.insert(0, str(root / "scripts"))

import contract_eval
import evidence
import trigger_eval

checks = [
    (trigger_eval._atomic_write_text, "trigger-race.txt", "replacement"),
    (contract_eval.atomic_write_text, "contract-race.txt", "replacement"),
    (evidence.atomic_write_json, "evidence-race.json", {"replacement": True}),
]
for function, name, value in checks:
    target = tmp / name
    original = b"concurrent writer\n"
    target.write_bytes(original)
    try:
        function(target, value)
    except FileExistsError:
        pass
    else:
        raise SystemExit(f"{function.__module__} overwrote a raced destination")
    if target.read_bytes() != original:
        raise SystemExit(f"{function.__module__} changed raced destination bytes")
PYEOF

echo
echo "Result: $FAIL FAIL / $PASS PASS"
if [[ "$FAIL" -gt 0 ]]; then
  echo "Action: the harness itself is broken — fix the failing checker before trusting any skill it grades."
  exit 1
fi
echo "Action: harness healthy — all checkers accept good input and reject broken input."
exit 0
