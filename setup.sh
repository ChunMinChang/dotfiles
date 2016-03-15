#!/bin/bash
source utils.sh

# Link environment setting
# -------------------------------------------------------------
echo "== Link environment setting =="
# If the environment is mac, then link the bash_profile to $HOME/.bash_profile
# if [ $ENV_OSX == $(GetOSEnvironment) ]; then
#   ln -s $(pwd)/bash_profile $HOME/.bash_profile
# elif [ $ENV_LINUX == $(GetOSEnvironment) ]; then
#   ln -s $(pwd)/bashrc $HOME/.bashrc
# fi

# Append gitconfig setting into ~/.gitconfig
# -------------------------------------------------------------
echo "== load sub-gitconfig setting =="
gitconfigPath="$HOME/.gitconfig"
subGitConfigPath="$(pwd)/git/config"
trashPath="$HOME/.Trash"

# If there is no any [include] is used,
# then the config path will be append with [include]
isIncludeUsed=$(GrepStringInFile "\[include\]" ~/.gitconfig)
if [ $isIncludeUsed -eq 0 ]; then
  # echo -e "[include]\n\tpath=$subGitConfigPath" >> $gitconfigPath
  AppendStringInFile "[include]\n\tpath=$subGitConfigPath" $gitconfigPath
else
  # If [include] is used, then our config path will be inserted
  # in the first line below [include]
  isFileIncluded=$(GrepStringInFile $subGitConfigPath $gitconfigPath)
  if [ $isFileIncluded -eq 0 ]; then
    echo "insert to first line: $subGitConfigPath"
    # Insert the config path and save it to a temporary file
    awk '/\[include\]/ { print; print "\tpath='$subGitConfigPath'"; next }1' $gitconfigPath >> $gitconfigPath.temp
    # then replace git config with the temporary file
    mv $gitconfigPath $trashPath
    mv $gitconfigPath.temp $gitconfigPath
  fi
fi
