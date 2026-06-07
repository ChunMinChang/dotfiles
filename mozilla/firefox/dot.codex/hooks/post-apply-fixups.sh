#!/bin/bash
# Codex PostToolUse hook wrapper for apply_patch.
#
# Codex launches matching hooks concurrently, so keep mutating fixups in one
# script and run them in a deterministic order.

set -euo pipefail

hook_json=$(cat)
repo_root=$(git rev-parse --show-toplevel 2>/dev/null || pwd)
hook_dir="$repo_root/.codex/hooks"

printf '%s' "$hook_json" | bash "$hook_dir/post-edit-lint.sh"
printf '%s' "$hook_json" | bash "$hook_dir/post-edit-format.sh"
# printf '%s' "$hook_json" | bash "$hook_dir/post-edit-static-analysis.sh"
