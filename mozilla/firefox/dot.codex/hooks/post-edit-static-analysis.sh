#!/bin/bash
# Codex PostToolUse hook: run mach static-analysis check on changed C/C++ files.

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
    [ -f "$file_path" ] || continue
    ext="${file_path##*.}"
    case "$ext" in
        c|cpp|cc|cxx|m|mm|h|hpp|hh|hxx) ;;
        *) continue ;;
    esac

    echo "[Codex hook] Static analysis: $file_path"
    ./mach static-analysis check "$file_path" 2>&1 \
        | grep -E '(error:|warning:|note:)' \
        | head -30 || true
done
