#!/bin/bash
source ../utils.sh

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
