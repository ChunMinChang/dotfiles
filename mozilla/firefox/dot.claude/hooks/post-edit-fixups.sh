#!/bin/bash
# Claude Code PostToolUse hook wrapper for Edit|Write.
#
# Claude Code launches matching hooks concurrently, so keep the mutating fixups
# (lint --fix, format) in one script and run them in a deterministic order. Two
# mach processes writing the same file at once corrupts it.

set -euo pipefail

hook_json=$(cat)
hook_dir="$CLAUDE_PROJECT_DIR/.claude/hooks"

printf '%s' "$hook_json" | bash "$hook_dir/post-edit-lint.sh" || true
printf '%s' "$hook_json" | bash "$hook_dir/post-edit-format.sh" || true
# printf '%s' "$hook_json" | bash "$hook_dir/post-edit-static-analysis.sh" || true
