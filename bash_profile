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

# Store the current path
currentPath=$(pwd)

# Get the path of dotfiles
#   If the bashrc is a symblic link to this file, then its parent folder is
#   what we want.
if [[ -L "$HOME/.bashrc" ]]; then
  #   1. Get the real path of the symbolic link of $HOME/.bashrc
  #   expected output: path/to/dotfiles/bashrc
  bashrc=$(python -c "import os; print os.path.realpath('$HOME/.bashrc')")
  #   2. Get father directory of the real bashrc, the path of dotfiles
  dotfiles=${bashrc%"bashrc"} # strip bashrc from path

#  If the bashrc is not a symblic link, then path of dotfiles is set to
#  the default location
else
  dotfiles=$HOME/dotfiles
fi

if [ ! -d "$dotfiles" ]; then
  echo "No $dotfiles exist! Please set the path for dotfiles!"
  return
fi

# Now, go dotfiles to configure settings for OSX under dotfiles
cd $dotfiles

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

# Go back to original location after setting
cd $currentPath
