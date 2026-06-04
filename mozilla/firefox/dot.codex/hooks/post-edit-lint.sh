#!/bin/bash
# Codex PostToolUse hook: run mach lint --fix on files changed by apply_patch.

set -euo pipefail

repo_root=$(git rev-parse --show-toplevel 2>/dev/null || pwd)
cd "$repo_root" || exit 1

changed_files() {
    if [ "$#" -gt 0 ]; then
        printf '%s\n' "$@"
        return
    fi

    jq -r '.tool_input.command // empty' | awk '
        /^\*\*\* Add File: / {
            sub(/^\*\*\* Add File: /, "")
            print
        }
        /^\*\*\* Update File: / {
            sub(/^\*\*\* Update File: /, "")
            print
        }
        /^\*\*\* Move to: / {
            sub(/^\*\*\* Move to: /, "")
            print
        }
    '
}

changed_files "$@" | sort -u | while IFS= read -r file_path; do
    [ -n "$file_path" ] || continue
    if .codex/hooks/should-format-lint.sh "$file_path"; then
        echo "[Codex hook] Lint fixing: $file_path"
        ./mach lint --fix "$file_path" 2>&1 \
            | grep -E '(error|warning|fixed|no problems|✖|✔)' \
            | head -30 || true
    fi
done
