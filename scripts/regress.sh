#!/usr/bin/env bash
set -uo pipefail

# Run YW SkillFoundry's complete local regression surface.
# Usage: bash scripts/regress.sh [--working-tree-only] [--library-root <skills-dir>]...

export PYTHONDONTWRITEBYTECODE=1

cd "$(dirname "$0")/.." || exit 2
ROOT="$(pwd)"
FAIL=0
PASS=0
LIBRARY_ROOTS=()
PRIVACY_ARGS=()
TMP="$(mktemp -d)" || { echo "ERROR  mktemp failed" >&2; exit 2; }
[[ -n "$TMP" && -d "$TMP" ]] || { echo "ERROR  invalid temp directory" >&2; exit 2; }
trap 'rm -rf "$TMP"' EXIT

while [[ $# -gt 0 ]]; do
  case "$1" in
    --library-root)
      [[ $# -ge 2 ]] || { echo "ERROR  --library-root needs a path" >&2; exit 2; }
      LIBRARY_ROOTS+=("$2")
      shift 2
      ;;
    --working-tree-only)
      PRIVACY_ARGS+=(--working-tree-only)
      shift
      ;;
    *)
      echo "ERROR  unknown argument: $1" >&2
      exit 2
      ;;
  esac
done

run() {
  local label=$1
  shift
  echo
  echo "== $label =="
  if "$@"; then
    PASS=$((PASS + 1))
  else
    FAIL=$((FAIL + 1))
  fi
}

IDENTITY_ROOT="$TMP/yw-skill-foundry"
mkdir -p "$IDENTITY_ROOT"
cp "$ROOT/SKILL.md" "$IDENTITY_ROOT/SKILL.md"
cp -R "$ROOT/references" "$IDENTITY_ROOT/references"

run "checker self-check" bash "$ROOT/scripts/self-check.sh"
run "skill structure" bash "$ROOT/scripts/validate-skill.sh" "$IDENTITY_ROOT"
run "description lint" python3 "$ROOT/scripts/trigger_eval.py" lint --skill "$IDENTITY_ROOT"
run "citation lint" python3 "$ROOT/scripts/citation_lint.py" --skill "$ROOT"
if [[ ${#PRIVACY_ARGS[@]} -gt 0 ]]; then
  run "privacy lint" python3 "$ROOT/scripts/privacy_lint.py" "${PRIVACY_ARGS[@]}"
else
  run "privacy lint" python3 "$ROOT/scripts/privacy_lint.py"
fi

ROUTING_RUNS=0
for fixture in "$ROOT"/evals/routing-*/fixture.jsonl; do
  [[ -f "$fixture" ]] || continue
  evidence_dir=$(dirname "$fixture")
  judgments="$evidence_dir/judgments-after.jsonl"
  if [[ -f "$judgments" ]]; then
    ROUTING_RUNS=$((ROUTING_RUNS + 1))
    run "routing evidence: $(basename "$evidence_dir")" \
      python3 "$ROOT/scripts/trigger_eval.py" score \
      --fixture "$fixture" --judgments "$judgments"
  else
    echo "FAIL  routing fixture lacks judgments-after.jsonl: $evidence_dir"
    FAIL=$((FAIL + 1))
  fi
done
if [[ $ROUTING_RUNS -eq 0 ]]; then
  echo "FAIL  no persisted routing regression was executed"
  FAIL=$((FAIL + 1))
fi

EVIDENCE_RUNS=0
for manifest in "$ROOT"/evals/run-compare-*/manifest.json; do
  [[ -f "$manifest" ]] || continue
  evidence_dir=$(dirname "$manifest")
  EVIDENCE_RUNS=$((EVIDENCE_RUNS + 1))
  run "run-compare evidence: $(basename "$evidence_dir")" \
    python3 "$ROOT/scripts/evidence.py" verify "$evidence_dir"
  for fixture in "$evidence_dir"/routing-with-skill-*.jsonl; do
    [[ -f "$fixture" ]] || continue
    suffix=${fixture##*routing-with-skill-}
    suffix=${suffix%.jsonl}
    judgments="$evidence_dir/routing-judgments-$suffix.jsonl"
    if [[ -f "$judgments" ]]; then
      run "embedded routing: $(basename "$evidence_dir") run $suffix" \
        python3 "$ROOT/scripts/trigger_eval.py" score \
        --fixture "$fixture" --judgments "$judgments"
    else
      echo "FAIL  embedded routing fixture lacks judgments: $fixture"
      FAIL=$((FAIL + 1))
    fi
  done
done
if [[ $EVIDENCE_RUNS -eq 0 ]]; then
  echo "INFO  no public run-compare evidence is bundled"
fi

if [[ ${#LIBRARY_ROOTS[@]} -gt 0 ]]; then
  audit_args=()
  for library_root in "${LIBRARY_ROOTS[@]}"; do
    audit_args+=(--root "$library_root")
  done
  run "library routing audit" \
    python3 "$ROOT/scripts/skill_library_audit.py" "${audit_args[@]}"
fi

echo
echo "Result: $FAIL FAIL / $PASS PASS"
if [[ $FAIL -gt 0 ]]; then
  echo "Action: regression failed — do not publish or claim improvement."
  exit 1
fi
echo "Action: local regression surface is healthy."
exit 0
