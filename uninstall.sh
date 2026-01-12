#!/bin/bash

# Load common utilities (Print functions)
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "$SCRIPT_DIR/utils.sh"

# Parse command-line arguments
DRY_RUN=false
SHOW_MANUAL=false

for arg in "$@"; do
  case $arg in
    --dry-run)
      DRY_RUN=true
      shift
      ;;
    --show-manual)
      SHOW_MANUAL=true
      shift
      ;;
    --help|-h)
      echo "Usage: $0 [OPTIONS]"
      echo ""
      echo "Uninstall personal dotfiles environment settings"
      echo ""
      echo "Options:"
      echo "  --dry-run       Show what would be removed without actually removing anything"
      echo "  --show-manual   Display manual cleanup steps without uninstalling"
      echo "  -h, --help      Show this help message"
      echo ""
      echo "Examples:"
      echo "  $0                    # Uninstall dotfiles"
      echo "  $0 --dry-run          # Preview what would be removed"
      echo "  $0 --show-manual      # Show manual cleanup steps only"
      exit 0
      ;;
    *)
      echo "Unknown option: $arg"
      echo "Run '$0 --help' for usage information"
      exit 1
      ;;
  esac
done

# Track what was removed and what needs manual cleanup
REMOVED_ITEMS=()
MANUAL_ITEMS=()

# Helper function to unlink symlinks
UnlinkIfSymlink() {
  local target="$1"
  local expected_source="$2"

  if [ -L "$target" ]; then
    local actual_source="$(readlink -f "$target")"
    if [ "$actual_source" = "$expected_source" ]; then
      if [ "$DRY_RUN" = true ]; then
        echo "[DRY-RUN] Would unlink $target"
        REMOVED_ITEMS+=("$target")
      else
        echo "Unlink $target"
        unlink "$target"
        REMOVED_ITEMS+=("$target")
      fi
      return 0
    else
      echo "$target is a symlink to $actual_source (not ours), stay unchanged"
      return 1
    fi
  elif [ -e "$target" ]; then
    echo "$target is not a symlink, stay unchanged"
    return 1
  else
    echo "$target does not exist"
    return 1
  fi
}

# Handle --show-manual mode (show manual cleanup steps only)
if [ "$SHOW_MANUAL" = true ]; then
  PrintTitle "\nManual Cleanup Steps\n"\
"====================================================================\n"
  echo "These items need manual removal to avoid losing your customizations:"
  echo ""

  FOUND_MANUAL=false

  # Check Git config
  if [ -f "$HOME/.gitconfig" ] && grep -q "path.*dotfiles/git/config" "$HOME/.gitconfig" 2>/dev/null; then
    FOUND_MANUAL=true
    echo "2. Remove git config include from ~/.gitconfig"
    echo "   Edit ~/.gitconfig and remove lines under [include] section:"
    echo "     path = <path-to-dotfiles>/git/config"
    echo "   Or run:"
    echo "     git config --global --unset include.path"
    echo ""
  fi

  # Check Bashrc loader
  if [ -f "$HOME/.bashrc" ] && grep -q "dot.bashrc" "$HOME/.bashrc" 2>/dev/null; then
    FOUND_MANUAL=true
    echo "3. Remove dot.bashrc loader from ~/.bashrc"
    echo "   Edit ~/.bashrc and remove lines like:"
    grep "dot.bashrc" "$HOME/.bashrc" 2>/dev/null | sed 's/^/     /'
    echo ""
  fi

  if [ "$FOUND_MANUAL" = false ]; then
    echo "✓ No manual cleanup needed!"
    echo ""
  fi

  PrintSubTitle "Note: Symlinks are removed automatically by uninstall.sh"
  echo "Run 'bash uninstall.sh' to remove symlinks."
  echo "Run 'bash uninstall.sh --dry-run' to preview what would be removed."
  echo ""
  exit 0
fi

# Show dry-run banner if enabled
if [ "$DRY_RUN" = true ]; then
  PrintTitle "\n[DRY-RUN MODE] Previewing uninstall - no changes will be made\n"\
"====================================================================\n"
else
  PrintTitle "\nUninstall personal environment settings\n"\
"====================================================================\n"
fi

PrintSubTitle "\nUnlink Mozilla stuff\n"\
"--------------------------------------------------------------------\n"
# Unlink machrc
MACHRC_GLOBAL="$HOME/.mozbuild/machrc"
MACHRC_HERE="$SCRIPT_DIR/mozilla/gecko/machrc"
UnlinkIfSymlink "$MACHRC_GLOBAL" "$MACHRC_HERE"


PrintSubTitle "\nUninstall custom settings\n"\
"--------------------------------------------------------------------\n"
# Load environment variables from dot.bashrc
BASHRC_HERE="$SCRIPT_DIR/dot.bashrc"

# Source the file (don't check exit code - it's unreliable due to conditional sourcing inside)
if [ -f "$BASHRC_HERE" ]; then
  source "$BASHRC_HERE" 2>/dev/null || true
  echo "Loaded environment variables from $BASHRC_HERE"
fi

# Verify required variables are set, compute them if not
# (This handles case where sourcing fails or doesn't set variables)
if [ -z "$PLATFORM" ]; then
  PLATFORM=$(uname -s | tr '[:upper:]' '[:lower:]')
  echo "Computed PLATFORM=$PLATFORM"
fi

if [ -z "$SETTINGS_PLATFORM" ]; then
  SETTINGS_PREFIX="$HOME/.settings_"
  SETTINGS_PLATFORM="${SETTINGS_PREFIX}${PLATFORM}"
  echo "Computed SETTINGS_PLATFORM=$SETTINGS_PLATFORM"
fi

if [ -z "$DOTFILES" ]; then
  DOTFILES="$HOME/.dotfiles"
  echo "Computed DOTFILES=$DOTFILES"
fi

# $PLATFORM is set in $BASHRC_HERE
echo Uninstall personal environment settings on $PLATFORM

# Unlink the platform settings ($SETTINGS_PLATFORM is set in $BASHRC_HERE)
SETTINGS_HERE="$SCRIPT_DIR/dot.settings_$PLATFORM"
UnlinkIfSymlink "$SETTINGS_PLATFORM" "$SETTINGS_HERE"

# Unlink the entry point of environment settings on darwin (MacOSX)
if [ "$PLATFORM" == "darwin" ]; then
  ZSHRC_HERE="$SCRIPT_DIR/dot.zshrc"
  UnlinkIfSymlink "$HOME/.zshrc" "$ZSHRC_HERE"
fi

# Unlink the $DOTFILES ($DOTFILES is set in $BASHRC_HERE)
UnlinkIfSymlink "$DOTFILES" "$SCRIPT_DIR"

# Remove git config
# Note: Manual removal required - user file may contain customizations
if [ -f "$HOME/.gitconfig" ] && grep -q "path.*dotfiles/git/config" "$HOME/.gitconfig" 2>/dev/null; then
  MANUAL_ITEMS+=("Remove git config include from ~/.gitconfig")
fi

# Unlink the $HOME/.bashrc
BASHRC_GLOBAL="$HOME/.bashrc"
if UnlinkIfSymlink "$BASHRC_GLOBAL" "$BASHRC_HERE"; then
  : # Successfully unlinked
elif [ -e "$BASHRC_GLOBAL" ] && [ "$PLATFORM" = "linux" ]; then
  # Note: Manual removal required - user file may contain customizations
  if grep -q "dot.bashrc" "$BASHRC_GLOBAL" 2>/dev/null; then
    MANUAL_ITEMS+=("Remove dot.bashrc loader from ~/.bashrc")
  fi
fi

# Summary
PrintTitle "\nUninstall Summary\n"\
"====================================================================\n"

# Show what was removed automatically
if [ ${#REMOVED_ITEMS[@]} -gt 0 ]; then
  PrintSubTitle "Automatically removed (${#REMOVED_ITEMS[@]} items):"
  for item in "${REMOVED_ITEMS[@]}"; do
    echo "  ✓ $item"
  done
  echo ""
else
  echo "No items were automatically removed."
  echo ""
fi

# Show what needs manual cleanup
if [ ${#MANUAL_ITEMS[@]} -gt 0 ]; then
  PrintSubTitle "Manual cleanup required (${#MANUAL_ITEMS[@]} items):"
  PrintWarning "The following items need manual removal to avoid losing customizations:"
  echo ""

  for item in "${MANUAL_ITEMS[@]}"; do
    echo "  • $item"
  done
  echo ""

  PrintSubTitle "Exact cleanup commands:"
  echo ""

  # Git config
  if [ -f "$HOME/.gitconfig" ] && grep -q "path.*dotfiles/git/config" "$HOME/.gitconfig" 2>/dev/null; then
    echo "  # Remove git config include from ~/.gitconfig"
    echo "  # Edit ~/.gitconfig and remove lines under [include] section:"
    echo "  #   path = $SCRIPT_DIR/git/config"
    echo "  # Or run:"
    echo "  git config --global --unset include.path"
    echo ""
  fi

  # Bashrc loader
  if [ -f "$BASHRC_GLOBAL" ] && grep -q "dot.bashrc" "$BASHRC_GLOBAL" 2>/dev/null; then
    echo "  # Remove dot.bashrc loader from ~/.bashrc"
    echo "  # Edit ~/.bashrc and remove lines containing:"
    grep "dot.bashrc" "$BASHRC_GLOBAL" 2>/dev/null | sed 's/^/  #   /'
    echo ""
  fi
else
  echo "✓ No manual cleanup required!"
  echo ""
fi

# Final message
if [ "$DRY_RUN" = true ]; then
  PrintTitle "\n[DRY-RUN COMPLETE] No changes were made\n"\
"====================================================================\n"
  echo "To actually uninstall, run without --dry-run flag:"
  echo "  bash uninstall.sh"
  echo ""
elif [ ${#MANUAL_ITEMS[@]} -gt 0 ]; then
  PrintWarning "Uninstall partially complete. Please complete manual cleanup steps above."
else
  PrintSubTitle "✓ Uninstall complete!"
  echo ""
fi
