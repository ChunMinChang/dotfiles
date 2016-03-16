#!/bin/bash
source utils.sh

# Link environment setting
# -------------------------------------------------------------
LogH1 "Link environment setting"
# If the environment is mac, then link the bash_profile to $HOME/.bash_profile
if [ $ENV_OSX == $(GetOSEnvironment) ]; then
  bashProfile="$HOME/.bash_profile"

  # if bash_profile already has a existing file and it's not a symblic link
  # then we will remove it to Trash.
  if [ -f $bashProfile ] && [ ! -L $bashProfile ]; then
    Move $bashProfile "$(GetTrashPath)/bash_profile"
  fi

  # Link the bash_profile
  echo "link .bash_profile to bash_profile here"
  ln -s $(pwd)/bash_profile $bashProfile

elif [ $ENV_LINUX == $(GetOSEnvironment) ]; then
  bashrc="$HOME/.bashrc"

  # if bashrc already has a existing file and it's not a symblic link
  # then we will remove it to Trash.
  if [ -f $bashrc ] && [ ! -L $bashrc ]; then
    Move $bashrc "$(GetTrashPath)/bashrc"
  fi

  echo  "link .bashrc to bashrc here"
  ln -s $(pwd)/bashrc $bashrc
fi

# Git setting
# -------------------------------------------------------------
LogH1 "Git setting"
cd git
bash setup.sh
cd ..

# Mercurial setting
# -------------------------------------------------------------
LogH1 "Mercurial setting"
cd mercurial
bash setup.sh
cd ..

# Vim setting
# -------------------------------------------------------------
LogH1 "Vim setting"
cd vim
bash setup.sh
cd ..
