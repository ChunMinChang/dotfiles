DOTFILES=~/.dotfiles

# Load common utils
[[ -r $DOTFILES/utils.sh ]] && . $DOTFILES/utils.sh

# Git
# ====================================================================
if [ $(CommandExists git) -eq 1 ] && [ -r $HOME/.gitconfig ]; then
  # load git alias and utils functions
  [[ -r $DOTFILES/git/utils.sh ]] && . $DOTFILES/git/utils.sh

  # Show git branch in prompt
  BranchInPrompt
else
  echo Please install git before loading its settings.
fi

# Platform-dependent settings
# ====================================================================
PLATFORM=$(uname -s | tr '[:upper:]' '[:lower:]')
BASHRC_PLATFORM=~/.bashrc_${PLATFORM}
[ -r $BASHRC_PLATFORM ] && . $BASHRC_PLATFORM

# Optional settings
# ====================================================================
