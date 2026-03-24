#!/bin/bash
# Sync helper for mozilla/media-skills submodule
# Usage:
#   ./mozilla/firefox/sync-media-skills.sh pull   # pull latest from upstream
#   ./mozilla/firefox/sync-media-skills.sh status  # show current pinned commit
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"

SUBMODULE="mozilla/firefox/media-skills"

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
