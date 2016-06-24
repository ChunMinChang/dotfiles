source utils.sh # Common utilities

# Personal shell commands
# ====================================================================
# Cross Compiler
# --------------------------------------------------------------------
# For IceCC
ExportToPATH /usr/lib/icecc/bin/


# Mozilla Gecko alias
# --------------------------------------------------------------------
source gecko/alias.sh

function linkMachrc() {
  local machrc_target=$HOME/.mozbuild/.machrc
  local machrc_source=$(pwd)/gecko/machrc
  LinkFile $machrc_source $machrc_target
}
linkMachrc

# Mozillla Git Reviewboard:
# --------------------------------------------------------------------
# For git-cinnabar
ExportToPATH /Users/chunminchang/Work/git-cinnabar

# For version-control-tools
ExportToPATH /Users/chunminchang/.mozbuild/version-control-tools/git/commands

# Git alias
# --------------------------------------------------------------------
source git/alias.sh

# Show git branch in prompt
BranchInPrompt
