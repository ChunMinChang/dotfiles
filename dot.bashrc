DOTFILES=~/.dotfiles

# Git
# ====================================================================
# load git alias and utils functions
[[ -r $DOTFILES/git/utils.sh ]] && . $DOTFILES/git/utils.sh

# Show git branch in prompt
BranchInPrompt
