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
