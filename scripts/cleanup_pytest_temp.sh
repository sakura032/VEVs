#!/usr/bin/env bash
set -euo pipefail

# Cleanup pytest temporary/cache directories in project root.
# Usage:
#   bash scripts/cleanup_pytest_temp.sh            # remove
#   以上命令会删除项目根目录下的 pytest 临时文件夹，如 .pytest_tmp、pytest-cache-files-* 等。
#   该命令只能在powershell终端运行，在wsl运行会报错没有权限删除

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
)

declare -a wildcard_targets=(
  "pytest-cache-files-*"
  "work/pytest_local_tmp*"
  "work/pytest_temp"
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

