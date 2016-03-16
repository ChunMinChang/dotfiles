# This file is used for OS X environment

# Store the current path
# Notice that the variable name must be different from bashrc,
# or the variable will be overridden
pathNow=$(pwd)

# Get the path of dotfiles
#   - 1. Get the real path of the symbolic link bash_profile
#   expected output: path/to/dotfiles/bash_profile
bashProfile=$(python -c "import os; print os.path.realpath('$HOME/.bash_profile')")
#   - 2. Get father directory of the real bash_profile
dotfiles=${bashProfile%"bash_profile"} # strip bash_profile from path

# Now, go dotfiles directory to configure our specifix settings
cd $dotfiles

if [ -f ./bashrc ]; then
    source ./bashrc
fi

# Go back to original location after setting
cd $pathNow
