# This file is used for Linux and OS X environment

# After running our setup.sh script,
# the bashrc here will be symbolically linked to $HOME/.bashrc.
# If you are in OS X environment, you need to keep our bash_profile
# symbolically linking to $HOME/.bash_profile,
# then you can load bashrc here successfully

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

# Now, go dotfiles to configure our common settings
cd $dotfiles

if [ -f common.sh ]; then
    source common.sh
fi

# Go back to original location after setting
cd $currentPath
