#!/usr/bin/env bash
# Create a local log.md from the template on first use.
# Never overwrites an existing log.md — safe to run on every update/pull.
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
skill_root="$(cd "${script_dir}/.." && pwd)"
template="${skill_root}/log.md.example"
target="${skill_root}/log.md"

if [ ! -f "${template}" ]; then
  echo "error: template not found at ${template}" >&2
  exit 2
fi

if [ -e "${target}" ]; then
  echo "log.md already exists — left untouched: ${target}"
  exit 0
fi

cp "${template}" "${target}"
echo "created ${target} from log.md.example"
