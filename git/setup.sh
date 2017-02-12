#!/bin/bash
source ../utils.sh

# Do nothing if "git" doesn't exist
exist=$(DoesCommandExist git)
if [ $exist -eq 0 ]; then
  echo "No need to apply git settings since git doesn't exist"
  return
fi

# Includ config to .gitconfig
# -------------------------------------------------------------
gitconfigPath="$HOME/.gitconfig"
subGitConfigPath="$(pwd)/config"
trashPath=$(GetTrashPath)

# If there is no any [include] is used,
# then the config path will be append with [include]
isIncludeUsed=$(GrepStringInFile "\[include\]" $gitconfigPath)
if [ $isIncludeUsed -eq 0 ]; then
  # echo -e "[include]\n\tpath=$subGitConfigPath" >> $gitconfigPath
  AppendStringToFile "[include]\n\tpath=$subGitConfigPath" $gitconfigPath
else
  # If [include] is used, then our config path will be inserted
  # in the first line below [include]
  isFileIncluded=$(GrepStringInFile $subGitConfigPath $gitconfigPath)
  if [ $isFileIncluded -eq 0 ]; then
    # Insert the config path and save it to a temporary file
    awk '/\[include\]/ { print; print "\tpath='$subGitConfigPath'"; next }1' $gitconfigPath >> $gitconfigPath.temp
    # then replace git config with the temporary file
    mv $gitconfigPath $trashPath
    mv $gitconfigPath.temp $gitconfigPath
  else
    echo "You already include the git config here"
  fi
fi
