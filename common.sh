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
  # Append any string as third parameter of LinkFile to force add symbolic link
  # when machrc_target doesn't exist.
  LinkFile $machrc_source $machrc_target 1
}
linkMachrc

# Mozillla Git Reviewboard
# --------------------------------------------------------------------
source mozilla/mozreview/export_path.sh

# Mozilla Rust
# --------------------------------------------------------------------
source /Users/cchang/.cargo/env

# Git
# ====================================================================
# Git alias
# --------------------------------------------------------------------
source git/alias.sh

# Show git branch in prompt
BranchInPrompt
