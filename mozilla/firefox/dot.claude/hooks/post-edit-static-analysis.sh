#!/bin/bash
# Post-edit static analysis hook — runs mach static-analysis check on C/C++ files

file_path=$(jq -r '.tool_input.file_path')

# Only run on C/C++ source and header files
ext="${file_path##*.}"
case "$ext" in
    c|cpp|cc|cxx|m|mm|h|hpp|hh|hxx) ;;
    *) exit 0 ;;
esac

# Skip if file doesn't exist
[ -f "$file_path" ] || exit 0

cd "$CLAUDE_PROJECT_DIR" || exit 1
echo "[Hook] Static analysis: $file_path"
./mach static-analysis check "$file_path" 2>&1 | grep -E '(error:|warning:|note:)' | head -30
