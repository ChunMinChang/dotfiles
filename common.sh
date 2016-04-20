# Personal shell commands
# ====================================================================

# Mozilla Gecko alias
# --------------------------------------------------------------------
source gecko/alias.sh
machrc=$HOME/.mozbuild/.machrc
# if machrc already has a existing file and it's a symblic link
if [[ -L "$machrc" ]]; then
  # then we will remove it
  echo "Remove the existing symlink to $machrc and re-link it!"
  rm $machrc
else # if it's not a symblic link
  # then we will rename it as ./machrc_backup
  echo "Rename the existing .machrc to .machrc_backup!"
  mv $machrc $machrc'_backup'
fi
ln -s $(pwd)/gecko/machrc $machrc


# Mozillla Git Reviewboard:
# --------------------------------------------------------------------
# For git-cinnabar
export PATH=/Users/chunminchang/Work/git-cinnabar:$PATH
# For version-control-tools
export PATH=/Users/chunminchang/.mozbuild/version-control-tools/git/commands:$PATH

# Git alias
# --------------------------------------------------------------------
source git/alias.sh

# Show git branch in prompt
branchInPrompt
