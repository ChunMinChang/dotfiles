#!/bin/bash
# Codex PostToolUse hook: run mach format on files changed by apply_patch.

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
        echo "[Codex hook] Formatting: $file_path"
        ./mach format "$file_path" 2>&1 | grep -v '^$' | head -30 || true
    fi
done
