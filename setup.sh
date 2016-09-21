#!/bin/bash
source utils.sh

# Link environment setting
# -------------------------------------------------------------
LogH1 "Link environment setting"

# If the environment is mac, then link the bash_profile to $HOME/.bash_profile
if [ $ENV_OSX == $(GetOSEnvironment) ]; then
  bashProfile="$HOME/.bash_profile"

  LinkOrImportFile $(pwd)/bash_profile $bashProfile
fi

# If the environment is mac or linux, then link the bashrc to $HOME/.bashrc
if [ $ENV_LINUX == $(GetOSEnvironment) ] || [ $ENV_OSX == $(GetOSEnvironment) ]; then
  bashrc="$HOME/.bashrc"

  LinkOrImportFile $(pwd)/bashrc $bashrc
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
