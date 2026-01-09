# Common Settings
# ====================================================================
[[ -r ~/.bashrc ]] && . ~/.bashrc

# Git
# ====================================================================
if CommandExists git; then
  if [ -r "$HOME/.gitconfig" ]; then
    # Show git branch in prompt
    BranchInPrompt
  else
    echo Please set .gitconfig first
  fi
else
  echo Please install git before loading its settings.
fi