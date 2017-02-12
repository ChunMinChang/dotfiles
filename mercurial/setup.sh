#!/bin/bash
source ../utils.sh

# Do nothing if "hg" doesn't exist
exist=$(DoesCommandExist hg)
if [ $exist -eq 0 ]; then
  echo "No need to apply mercurial settings since hg doesn't exist"
  return
fi

# Include config to .hgrc
# -------------------------------------------------------------
hgrcPath="$HOME/.hgrc"
configPath="$(pwd)/config"
trashPath=$(GetTrashPath)

isIncluded=$(GrepStringInFile "\%include $configPath" $hgrcPath)
if [ $isIncluded -eq 0 ]; then
  AppendStringToFile "%include $configPath" $hgrcPath
else
  echo "You already include the mercurial config here"
fi
