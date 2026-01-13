#!/bin/bash
# Post-edit lint hook - runs mach lint --fix on edited files

# Read the hook input JSON from stdin
file_path=$(jq -r '.tool_input.file_path')

# Check if file should be linted (using the detection script)
if "$CLAUDE_PROJECT_DIR"/.claude/hooks/should-format-lint.sh "$file_path"; then
    cd "$CLAUDE_PROJECT_DIR" || exit 1
    echo "[Hook] Lint fixing: $file_path"
    ./mach lint --fix "$file_path" 2>&1 | grep -E '(error|warning|fixed|no problems|✖|✔)' | head -30
fi
