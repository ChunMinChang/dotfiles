#!/bin/bash
source utils.sh

GrepStringInFile jekku ~/.gitconfi

# Link environment setting
# -------------------------------------------------------------
LogH1 "Link environment setting"
# If the environment is mac, then link the bash_profile to $HOME/.bash_profile
# if [ $ENV_OSX == $(GetOSEnvironment) ]; then
#   ln -s $(pwd)/bash_profile $HOME/.bash_profile
# elif [ $ENV_LINUX == $(GetOSEnvironment) ]; then
#   ln -s $(pwd)/bashrc $HOME/.bashrc
# fi

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
