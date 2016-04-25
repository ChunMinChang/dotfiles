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

# Autocomplete for git alias
if [ -f `brew --prefix`/etc/bash_completion ]; then
  . `brew --prefix`/etc/bash_completion
else
  echo 'Install bash-completion to use Git alias'
  brew install git && brew install bash-completion
fi
