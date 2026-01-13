#!/bin/bash
# Returns exit code 0 if file should be formatted/linted, 1 otherwise

file_path="$1"

# Check if file exists
if [ ! -f "$file_path" ]; then
    exit 1
fi

# Get file extension
ext="${file_path##*.}"

# Check if extension matches source code files
case "$ext" in
    # C/C++
    c|cpp|cc|cxx|h|hpp|hh|hxx|m|mm)
        exit 0 ;;
    # JavaScript/TypeScript
    js|mjs|jsx|ts|tsx)
        exit 0 ;;
    # Python
    py|pyi)
        exit 0 ;;
    # Rust
    rs)
        exit 0 ;;
    # CSS
    css|scss)
        exit 0 ;;
    # HTML
    html|xhtml|sjs)
        exit 0 ;;
    # Build files
    build|configure|mozbuild)
        exit 0 ;;
    # IDL
    idl|webidl)
        exit 0 ;;
    # JSON
    json)
        exit 0 ;;
    # Everything else - don't format/lint
    *)
        exit 1 ;;
esac
