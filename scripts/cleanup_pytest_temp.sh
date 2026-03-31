#!/usr/bin/env bash
set -euo pipefail

# Cleanup pytest temporary/cache directories used by this repository.
# Usage:
#   bash scripts/cleanup_pytest_temp.sh            # remove
#   以上命令会删除项目中 pytest 留下的临时目录。

dry_run=0
if [[ "${1:-}" == "--dry-run" ]]; then
  dry_run=1
fi

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
project_root="$(cd "${script_dir}/.." && pwd)"
cd "${project_root}"

declare -a exact_targets=(
  ".pytest_tmp"
  "pytest_tmp_nodot"
  "tests/.tmp"
)

declare -a wildcard_targets=(
  "pytest-cache-files-*"
)

declare -a to_delete=()

for name in "${exact_targets[@]}"; do
  if [[ -d "${name}" ]]; then
    to_delete+=("${name}")
  fi
done

for pattern in "${wildcard_targets[@]}"; do
  while IFS= read -r path; do
    [[ -d "${path}" ]] && to_delete+=("${path}")
  done < <(compgen -G "${pattern}" || true)
done

if [[ ${#to_delete[@]} -eq 0 ]]; then
  echo "No pytest temp/cache directories found."
  exit 0
fi

echo "Project root: ${project_root}"
echo "Found ${#to_delete[@]} target(s):"
for path in "${to_delete[@]}"; do
  echo " - ${path}"
done

for path in "${to_delete[@]}"; do
  if [[ ${dry_run} -eq 1 ]]; then
    echo "[dry-run] Would remove: ${path}"
  else
    rm -rf -- "${path}" && echo "[OK] Removed: ${path}" || echo "[WARN] Failed: ${path}"
  fi
done

if [[ ${dry_run} -eq 1 ]]; then
  echo "Dry-run finished. No files removed."
else
  echo "Cleanup finished."
fi
