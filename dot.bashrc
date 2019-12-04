DOTFILES=~/.dotfiles

# Show colors for ls
export CLICOLOR=true
export LSCOLORS="gxfxcxdxcxegedabagacad"

# Load common utils
[[ -r $DOTFILES/utils.sh ]] && . $DOTFILES/utils.sh

# Git
# ====================================================================
if [ $(CommandExists git) -eq 1 ]; then
  if [ -r $HOME/.gitconfig ]; then
    # load git alias and utils functions
    [[ -r $DOTFILES/git/utils.sh ]] && . $DOTFILES/git/utils.sh

    # Show git branch in prompt
    BranchInPrompt
  else
    echo Please set .gitconfig first
  fi
else
  echo Please install git before loading its settings.
fi

# Platform-dependent settings
# ====================================================================
PLATFORM=$(uname -s | tr '[:upper:]' '[:lower:]')
BASHRC_PLATFORM=~/.bashrc_${PLATFORM}
[ -r $BASHRC_PLATFORM ] && . $BASHRC_PLATFORM

# Alias
# ====================================================================
alias RSSTimestamp='TZ=GMT date +"%a, %d %b %Y %T %Z"'

# Optional settings
# ====================================================================
export GIT_EDITOR=vim