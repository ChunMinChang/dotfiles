source utils.sh # Common utilities

# Mozilla
# ====================================================================
# Mozilla Cross Compiler
# --------------------------------------------------------------------
source mozilla/icecream/export_path.sh

# Mozilla Gecko alias
# --------------------------------------------------------------------
source mozilla/gecko/alias.sh

# Mozilla machrc
# --------------------------------------------------------------------
function linkMachrc() {
  local machrc_target=$HOME/.mozbuild/.machrc
  local machrc_source=$(pwd)/mozilla/gecko/machrc
  LinkFile $machrc_source $machrc_target
}
linkMachrc

# Mozillla Git Reviewboard
# --------------------------------------------------------------------
source mozilla/mozreview/export_path.sh

# Git
# ====================================================================
# Git alias
# --------------------------------------------------------------------
source git/alias.sh

# Show git branch in prompt
BranchInPrompt
