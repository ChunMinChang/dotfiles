#!/usr/bin/env bash
# config.sh - Centralized configuration for dotfiles repository
#
# This file contains all configurable paths used throughout the dotfiles.
# Users can override these by creating ~/.dotfiles_config with their custom values.
#
# Example ~/.dotfiles_config:
#   DOTFILES_MOZBUILD_DIR="$HOME/my-custom-mozbuild"
#   DOTFILES_LOCAL_BIN_DIR="$HOME/bin"

# ==============================================================================
# Mozilla Development Paths
# ==============================================================================

# Mozilla build directory (contains machrc, etc.)
: "${DOTFILES_MOZBUILD_DIR:=$HOME/.mozbuild}"

# Local bin directory (for moz-phab and other user-installed tools)
: "${DOTFILES_LOCAL_BIN_DIR:=$HOME/.local/bin}"

# Work bin directory (for pernosco-submit and other work tools)
: "${DOTFILES_WORK_BIN_DIR:=$HOME/Work/bin}"

# Cargo/Rust directory
: "${DOTFILES_CARGO_DIR:=$HOME/.cargo}"

# ==============================================================================
# Platform-Specific Paths
# ==============================================================================

# Trash directory on Linux
: "${DOTFILES_TRASH_DIR_LINUX:=$HOME/.local/share/Trash/files}"

# Trash directory on macOS
: "${DOTFILES_TRASH_DIR_DARWIN:=$HOME/.Trash}"

# ==============================================================================
# User Configuration Override
# ==============================================================================

# Source user config if it exists (allows users to override any of the above)
if [ -r "$HOME/.dotfiles_config" ]; then
  # shellcheck source=/dev/null
  . "$HOME/.dotfiles_config"
fi

# ==============================================================================
# Derived Values (computed after user overrides)
# ==============================================================================

# Machrc path (inside mozbuild directory)
export DOTFILES_MACHRC_PATH="$DOTFILES_MOZBUILD_DIR/machrc"

# Cargo env script path
export DOTFILES_CARGO_ENV_PATH="$DOTFILES_CARGO_DIR/env"

# Pernosco-submit path
export DOTFILES_PERNOSCO_SUBMIT_PATH="$DOTFILES_WORK_BIN_DIR/pernosco-submit"

# Platform-specific trash directory
case "$(uname -s | tr '[:upper:]' '[:lower:]')" in
  linux*)
    export DOTFILES_TRASH_DIR="$DOTFILES_TRASH_DIR_LINUX"
    ;;
  darwin*)
    export DOTFILES_TRASH_DIR="$DOTFILES_TRASH_DIR_DARWIN"
    ;;
  *)
    export DOTFILES_TRASH_DIR="$HOME/.Trash"  # Default fallback
    ;;
esac
