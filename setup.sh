#!/bin/bash
source utils.sh

# Link environment setting
# -------------------------------------------------------------
trash=$(GetTrashPath)

LogH1 "Link environment setting"
# If the environment is mac, then link the bash_profile to $HOME/.bash_profile
if [ $ENV_OSX == $(GetOSEnvironment) ]; then
  bashProfile="$HOME/.bash_profile"

  exist=$(DoseFileExist $bashProfile)

  if [ $exist -eq 1 ]; then # if file exist, then remove it to Trash first
    mv $bashProfile $trash
  fi

  # Link the bash_profile
  echo "link .bash_profile to bash_profile here"
  ln -s $(pwd)/bash_profile $bashProfile

elif [ $ENV_LINUX == $(GetOSEnvironment) ]; then
  bashRc="$HOME/.bashrc"

  exist=$(DoseFileExist $bashRc)

  if [ $exist -eq 1 ]; then # if file exist, then remove it to Trash first
    mv $bashRc $trash
  fi

  echo  "link .bashrc to bashrc here"
  # ln -s $(pwd)/bashrc $bashRc
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
