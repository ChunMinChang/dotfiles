#!/bin/bash
# Sync helper for ChunMinChang/alwu-Fx-Claude-Skills submodule
# Usage:
#   ./mozilla/firefox/sync-alwu-claude-skills.sh pull   # pull latest from upstream
#   ./mozilla/firefox/sync-alwu-claude-skills.sh status  # show current pinned commit
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"

SUBMODULE="mozilla/firefox/alwu-claude-skills"

case "${1:-pull}" in
  pull)
    git submodule update --remote "$SUBMODULE"
    echo "Updated submodule to latest upstream main."
    echo "Run 'git add $SUBMODULE && git commit' to pin this version."
    ;;
  status)
    git submodule status "$SUBMODULE"
    ;;
  *)
    echo "Usage: $0 {pull|status}" >&2; exit 1
    ;;
esac
