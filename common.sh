source utils.sh # Common utilities

# Personal shell commands
# ====================================================================

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
export PATH=/Users/chunminchang/Work/git-cinnabar:$PATH
# For version-control-tools
export PATH=/Users/chunminchang/.mozbuild/version-control-tools/git/commands:$PATH

# Git alias
# --------------------------------------------------------------------
source git/alias.sh

# Show git branch in prompt
branchInPrompt
