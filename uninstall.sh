#!/bin/bash

PrintTitle()
{
  local msg=$1
  local bold_red="\033[1;31m"
  local normal="\033[0m"
  echo -e ${bold_red}${msg}${normal}
}

PrintSubTitle()
{
  local msg=$1
  local bold_red="\033[92m"
  local normal="\033[0m"
  echo -e ${bold_red}${msg}${normal}
}

PrintWarning() {
  local msg=$1
  local bold_yellow="\033[1;33m"
  local normal="\033[0m"
  echo -e ${bold_yellow}WARNING:${normal} ${msg}
}

PrintTitle "\nUninstall personal environment settings\n"\
"====================================================================\n"

PrintSubTitle "\nUnlink Mozilla stuff\n"\
"--------------------------------------------------------------------\n"
# Unlink machrc
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
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
# TODO: Remove this automatically
PrintWarning "Please remove ./mozilla/hg/config with prefix %include in $HOME/.hgrc manually"

PrintSubTitle "\nUninstall custom settings\n"\
"--------------------------------------------------------------------\n"
# Load environment variables to this script
BASHRC_HERE="$SCRIPT_DIR/dot.bashrc"
source "$BASHRC_HERE"

# TODO: Not sure why `source $BASHRC_HERE` succeeds but `$?` return 1 indicating failure.
if [ $? -eq 0 ] || [ ! -z "$PLATFORM" ]; then
  echo "Load environment variables in $BASHRC_HERE"
else
  PrintWarning "$BASHRC_HERE is not loadable"
  PrintWarning "Apply environment variables by parsing $BASHRC_HERE:"
  # Show the parsed environment variables in $BASHRC_HERE
  grep "^[^#;^export;].*=" "$BASHRC_HERE"
  # Force loading environment variables in $BASHRC_HERE
  eval $(grep "^[^#;^export;].*=" "$BASHRC_HERE")
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
# TODO: Remove this automatically
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
  # TODO: Remove this automatically
  PrintWarning "Please remove $BASHRC_HERE in $BASHRC_GLOBAL manually"
elif [ ! -e "$BASHRC_GLOBAL" ]; then
  echo "$BASHRC_GLOBAL does not exist"
fi
