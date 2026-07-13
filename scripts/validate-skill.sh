#!/usr/bin/env bash
set -euo pipefail

# Validate a skill directory against YW SkillFoundry Hard Rules.
# Usage: bash validate-skill.sh <skill-dir>
# Exit 0 = all pass, Exit 1 = at least one FAIL.

export PYTHONDONTWRITEBYTECODE=1

SKILL_DIR="${1:?Usage: validate-skill.sh <skill-dir>}"
SKILL_FILE="$SKILL_DIR/SKILL.md"
REFS_DIR="$SKILL_DIR/references"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

PASS=0; WARN=0; FAIL=0
report() {
  local level=$1
  shift
  case "$level" in
    PASS) PASS=$((PASS + 1)) ;;
    WARN) WARN=$((WARN + 1)) ;;
    FAIL) FAIL=$((FAIL + 1)) ;;
    *) printf "ERROR  invalid report level: %s\n" "$level" >&2; exit 2 ;;
  esac
  printf "%-4s  %s\n" "$level" "$*"
}

if [[ ! -f "$SKILL_FILE" ]]; then
  report FAIL "SKILL.md not found at $SKILL_FILE"
  echo ""; echo "Result: $FAIL FAIL / $WARN WARN / $PASS PASS"; exit 1
fi

body_lines=$(grep -c '' "$SKILL_FILE")
if (( body_lines > 700 )); then
  report FAIL "R1: SKILL.md is $body_lines lines (hard ceiling 700 — split into references)"
elif (( body_lines > 500 )); then
  report WARN "R1: SKILL.md is $body_lines lines (> 500 guideline — justify the excess or split)"
else
  report PASS "R1: SKILL.md is $body_lines lines (≤500)"
fi

# R2/R2b/R3: frontmatter checks delegated to python (block-scalar aware, counts
# Unicode code points — bash ${#var} miscounts nothing here but sed-based extraction
# broke on block scalars and multi-line values).
fm_report=$(python3 - "$SKILL_FILE" "$SCRIPT_DIR" <<'PYEOF'
import re, sys
from pathlib import Path

sys.path.insert(0, sys.argv[2])
from frontmatter import FrontmatterError, parse_frontmatter_file

skill_file = Path(sys.argv[1])
try:
    out = parse_frontmatter_file(skill_file)
except (OSError, FrontmatterError) as exc:
    print(f"FAIL R2: {exc}")
    sys.exit(0)

name = out.get("name")
if name is None:
    print("FAIL R2b: no name field in frontmatter")
else:
    display = name.replace("\r", "\\r").replace("\n", "\\n")
    if not re.match(r"^[a-z0-9]+(-[a-z0-9]+)*$", name) or len(name) > 64:
        print(f"FAIL R2b: name '{display}' violates spec (1-64 chars, lowercase/digits/hyphens)")
    elif name != skill_file.parent.name:
        print(f"FAIL R2b: name '{display}' must match parent directory '{skill_file.parent.name}'")
    else:
        print(f"PASS R2b: name '{display}' is spec-compliant and matches its directory")

desc = out.get("description")
if desc is None:
    print("FAIL R2: no description field in frontmatter")
else:
    n = len(desc)
    if n == 0:
        print("FAIL R2: description field is empty")
    elif n > 1024:
        print(f"FAIL R2: description is {n} chars (limit 1024)")
    else:
        print(f"PASS R2: description is {n} chars (<=1024)")
    hard = re.compile(r"\bstep\s*\d|first\b.*\bthen\b|\bdispatch(es|ed)?\b.*\b(per|each)\b|execute.*\border\b|步骤\s*\d|先.*然后", re.IGNORECASE | re.DOTALL)
    soft = re.compile(r"\bworkflow\b|\bpipeline\b", re.IGNORECASE)
    if hard.search(desc):
        print("FAIL R3: description contains sequenced workflow language (trigger conditions only)")
    elif soft.search(desc):
        print("WARN R3: description mentions workflow/pipeline — confirm it is a domain keyword, not a process summary")
    else:
        print("PASS R3: description has no workflow language")
PYEOF
)
while IFS= read -r line; do
  [[ -z "$line" ]] && continue
  level="${line%% *}"; msg="${line#* }"
  report "$level" "$msg"
done <<< "$fm_report"

if [[ -d "$REFS_DIR" ]]; then
  ref_report=$(python3 - "$SKILL_FILE" "$REFS_DIR" <<'PYEOF'
import re, sys
from pathlib import Path

skill_file, refs_dir = Path(sys.argv[1]), Path(sys.argv[2])
skill_text = skill_file.read_text(encoding="utf-8")
refs = sorted(refs_dir.glob("*.md"))

# References may mention peers as optional further reading, but each file must
# remain executable on its own. Flag imperative nested loads outside code fences.
dependency = re.compile(
    r"(?:\b(?:read|load|open|see)\s+(?:the\s+)?|(?:读|读取|加载|参见|详见)\s*)"
    r"`?(?:references/|\./)?([A-Za-z0-9_-]+\.md)`?",
    re.IGNORECASE,
)
issues = []
for ref in refs:
    text = ref.read_text(encoding="utf-8")
    outside_fences = re.sub(r"```.*?```", "", text, flags=re.DOTALL)
    for lineno, line in enumerate(outside_fences.splitlines(), 1):
        match = dependency.search(line)
        if match and match.group(1) != ref.name:
            issues.append(f"{ref.name}:{lineno} requires nested load of {match.group(1)}")

if issues:
    for issue in issues:
        print(f"FAIL R4: {issue}; inline the needed rule or route both files from SKILL.md")
else:
    print("PASS R4: references are standalone (no required peer loads)")

# Reference Map consistency: every named file must exist, and every reference
# file must be discoverable directly from SKILL.md.
named = set(re.findall(r"references/([A-Za-z0-9_-]+\.md)", skill_text))
existing = {p.name for p in refs}
missing = sorted(named - existing)
unindexed = sorted(existing - named)
if missing:
    print(f"FAIL R4b: SKILL.md names missing reference file(s): {', '.join(missing)}")
elif unindexed:
    print(f"WARN R4b: reference file(s) not indexed from SKILL.md: {', '.join(unindexed)}")
else:
    print(f"PASS R4b: Reference Map and references/ agree ({len(existing)} files)")
PYEOF
)
  while IFS= read -r line; do
    [[ -z "$line" ]] && continue
    level="${line%% *}"; msg="${line#* }"
    report "$level" "$msg"
  done <<< "$ref_report"

  for ref in "$REFS_DIR"/*.md; do
    [[ -f "$ref" ]] || continue
    ref_lines=$(grep -c '' "$ref")
    basename_ref=$(basename "$ref")
    if (( ref_lines > 100 )); then
      if head -20 "$ref" | grep -qiE '^\s*[-*] \[|^## 目录|^## Table of Contents|^## TOC'; then
        report PASS "R5: $basename_ref ($ref_lines lines) has TOC"
      else
        report WARN "R5: $basename_ref is $ref_lines lines but has no TOC in first 20 lines"
      fi
    fi
  done
else
  report WARN "R4: no references/ directory found"
fi

# Word-boundary via Python (BSD grep \b is unreliable). Remove fenced examples,
# inline code, and quoted phrases so R6 reports likely live instructions only.
weak_count=$(python3 - "$SKILL_FILE" <<'PYEOF'
import re, sys
from pathlib import Path
text = Path(sys.argv[1]).read_text(encoding="utf-8")
text = re.sub(r"```.*?```", "", text, flags=re.DOTALL)
rx = re.compile(r"\bconsider\b|\btry to\b|\byou might want", re.IGNORECASE)
count = 0
for line in text.splitlines():
    scrubbed = re.sub(r"\x60[^\x60]*\x60|\"[^\"]*\"|'[^']*'", "", line)
    if rx.search(scrubbed):
        count += 1
print(count)
PYEOF
)
if (( weak_count > 0 )); then
  report WARN "R6: SKILL.md contains $weak_count likely live line(s) with weak-authority phrases (consider/try to/you might want)"
else
  report PASS "R6: no weak-authority phrases in SKILL.md"
fi

if grep -qiE '## Outcome Contract|## outcome|Outcome:|Done when:' "$SKILL_FILE"; then
  report PASS "R7: Outcome Contract found"
else
  report WARN "R7: no Outcome Contract section detected"
fi

if grep -qiE '## Hard Rules|## Non-Negotiables|MUST|NEVER' "$SKILL_FILE"; then
  report PASS "R8: Hard Rules / authority wording found"
else
  report WARN "R8: no Hard Rules section or authority wording detected"
fi

if grep -qiE '## Gotchas|What happened.*Rule' "$SKILL_FILE"; then
  report PASS "R9: Gotchas table found"
else
  report WARN "R9: no Gotchas table detected"
fi

# R10/R11: static security scan of the LOADED BODY (SKILL.md + references only —
# the text that actually ships and gets read; scripts/ is excluded so the scanner's
# own patterns can't match themselves). A skill must never carry credentials, and a
# skill that tells the agent to pipe a remote script into a shell is an injection surface.
scan_files=("$SKILL_FILE")
if [[ -d "$REFS_DIR" ]]; then
  for ref in "$REFS_DIR"/*.md; do [[ -f "$ref" ]] && scan_files+=("$ref"); done
fi
q="'"
secret_re="AKIA[0-9A-Z]{16}|ghp_[A-Za-z0-9]{36}|-----BEGIN[A-Z ]*PRIVATE KEY-----|(api[_-]?key|secret|token|password)[\"${q}]?[[:space:]]*[:=][[:space:]]*[\"${q}][A-Za-z0-9/+_.=-]{20,}"
secret_hits=$(grep -nEi "$secret_re" "${scan_files[@]}" 2>/dev/null || true)
if [[ -n "$secret_hits" ]]; then
  report FAIL "R10: possible hardcoded secret in body — never ship credentials in a skill:"
  echo "$secret_hits" | sed 's/^/        /'
else
  report PASS "R10: no hardcoded secrets detected in body"
fi

inj_re="(curl|wget)[^|]*\|[[:space:]]*(sudo[[:space:]]+)?(bash|sh)\b|eval[[:space:]]+[\"${q}]?\\\$\((curl|wget)|rm[[:space:]]+-rf[[:space:]]+[\$/~]"
inj_hits=$(grep -nEi "$inj_re" "${scan_files[@]}" 2>/dev/null || true)
if [[ -n "$inj_hits" ]]; then
  report WARN "R11: body instructs a risky exec (pipe-to-shell / eval-remote / rm -rf) — confirm intentional & safe:"
  echo "$inj_hits" | sed 's/^/        /'
else
  report PASS "R11: no obvious pipe-to-shell / destructive exec in body"
fi

echo ""
echo "Result: $FAIL FAIL / $WARN WARN / $PASS PASS"
if (( FAIL > 0 )); then
  echo "Action: fix all FAIL items before shipping."
  exit 1
elif (( WARN > 0 )); then
  echo "Action: review WARN items; PASS items are compliant."
  exit 0
else
  echo "Action: structure and static safety checks are clean."
  exit 0
fi
