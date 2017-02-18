# This file is used for OS X environment

# To successfully load .bashrc, the $HOME/.bashrc must be in same folder
# of the $HOME/.bash_profile. After running our setup.sh script,
# the bashrc and bash_profile here will be symbolically linked to
# $HOME/.bashrc and $HOME/.bash_profile
if [ -f $HOME/.bashrc ]; then
  source $HOME/.bashrc
fi

# Use macvim instead of vim if macvim exist
type -P mvim &>/dev/null && alias vim='mvim -v'

# Show different colors for ls
export CLICOLOR='true'
export LSCOLORS="gxfxcxdxcxegedabagacad"

# Autocomplete for git alias
# Download from https://github.com/git/git/blob/master/contrib/completion/git-completion.bash
# Tutorial: https://gist.github.com/JuggoPop/10706934
if [ -f git-completion.bash ]; then
  . git-completion.bash

  # Add git completion to aliases
  __git_complete g __git_main
  __git_complete gc _git_checkout
  __git_complete gm __git_merge
  __git_complete gp _git_pull
fi
