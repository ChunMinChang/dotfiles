#!/bin/bash

# Load common utilities (Print functions)
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "$SCRIPT_DIR/utils.sh"

PrintTitle "\nUninstall personal environment settings\n"\
"====================================================================\n"

PrintSubTitle "\nUnlink Mozilla stuff\n"\
"--------------------------------------------------------------------\n"
# Unlink machrc
MACHRC_GLOBAL="$HOME/.mozbuild/machrc"
MACHRC_HERE="$SCRIPT_DIR/mozilla/gecko/machrc"
if [ -L "$MACHRC_GLOBAL" ]; then
  MACHRC_LINK="$(readlink -f "$MACHRC_GLOBAL")"
  if [ "$MACHRC_LINK" = "$MACHRC_HERE" ]; then
    echo "Unlink $MACHRC_GLOBAL"
    unlink "$MACHRC_GLOBAL"
  else
    echo "$MACHRC_GLOBAL stay unchanged"
  fi
elif [ -e "$MACHRC_GLOBAL" ]; then
  echo "$MACHRC_GLOBAL is not a symlink, stay unchanged"
else
  echo "$MACHRC_GLOBAL does not exist"
fi

# Remove mozilla hg config
# Note: Manual removal required - user file may contain customizations
PrintWarning "Please remove ./mozilla/hg/config with prefix %include in $HOME/.hgrc manually"

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
if [ -r "$SETTINGS_PLATFORM" ]; then
  echo "Unlink $SETTINGS_PLATFORM"
  unlink "$SETTINGS_PLATFORM"
fi

# Unlink the entry point of environment settings on darwin (MacOSX)
if [ "$PLATFORM" == "darwin" ] && [ -r ~/.zshrc ]; then
  echo "Unlink ~/.zshrc"
  unlink ~/.zshrc
fi

# Unlink the $DOTFILES ($DOTFILES is set in $BASHRC_HERE)
if [ -r "$DOTFILES" ]; then
  echo "Unlink $DOTFILES"
  unlink "$DOTFILES"
fi

# Remove git config
# Note: Manual removal required - user file may contain customizations
PrintWarning "Please remove ./git/config under [include] in $HOME/.gitconfig manually"

# Unlink the $HOME/.bashrc
BASHRC_GLOBAL="$HOME/.bashrc"
if [ -L "$BASHRC_GLOBAL" ]; then
  BASHRC_LINK="$(readlink -f "$BASHRC_GLOBAL")"
  if [ "$BASHRC_LINK" = "$BASHRC_HERE" ]; then
    echo "Unlink $BASHRC_GLOBAL"
    unlink "$BASHRC_GLOBAL"
  else
    echo "$BASHRC_GLOBAL is a symlink to $BASHRC_LINK, stay unchanged"
  fi
elif [ -e "$BASHRC_GLOBAL" ] && [ "$PLATFORM" = "linux" ]; then
  # Note: Manual removal required - user file may contain customizations
  PrintWarning "Please remove $BASHRC_HERE in $BASHRC_GLOBAL manually"
elif [ ! -e "$BASHRC_GLOBAL" ]; then
  echo "$BASHRC_GLOBAL does not exist"
fi
