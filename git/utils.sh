# General
# ------------------------------------------------
alias ga='git add'
alias gb='git branch -v'
alias gc='git commit'
alias gcp='git cherry-pick'
alias gcl='git clean'
alias gcp='git cherry-pick'
alias gd='git diff'
alias go='git checkout'
alias gpl='git pull'
alias gps='git push'
alias grb='git rebase'
alias grt='git remote -v'
alias gs='git status'
alias gum='git add -u && git commit -m'

# Typo
# ------------------------------------------------
alias get='git'
alias gkt='git'
alias got='git'
alias gut='git'

# Run commands on all files in the last commit
# ------------------------------------------------
function GitLastCommit() {
  local cmd="$1"
  # Load edited files into tabs if cmd is vim
  if [ "$cmd" == "vim" ]; then
    cmd="vim -p" # open files in tabs
  fi
  git diff-tree --no-commit-id --name-only --diff-filter=d -r HEAD | xargs "$cmd"
}

# Run commands on all uncommit files
# ------------------------------------------------
function GitUncommit() {
  local cmd=$1
  # Load edited files into tabs if cmd is vim
  if [ "$cmd" == "vim" ]; then
    cmd="vim -p" # open files in tabs
  fi
  $cmd $(git status --porcelain | awk '{print $2}')
  # git ls-files --modified --deleted --others -z | xargs -0 $cmd
}

# Add some files except some certian files
# ------------------------------------------------
function GitAddExcept {
  local option=""
  local files=()
  while [[ $# -gt 0 ]]
  do
  arg="$1"

  case $arg in
      -A|--all)
      option="$arg"
      shift # past argument
      ;;
      -u|--update)
      option="$arg"
      shift # past argument
      ;;
      *)    # unknown option
      files+=("$1") # save it in an array for later
      shift # past argument
      ;;
  esac
  done
  git add "$option"
  git reset "${files[@]}"
}

# Create a branch for pull #
# ------------------------------------------------
function CreateGitBranchForPullRequest {
  local remote="$1"
  local number="$2"
  git fetch "$remote" pull/"$number"/head:pr-"$number"
  printf "\nCurrent git branches:\n"
  git branch -v
}


# Show git branch in prompt.
# ------------------------------------------------
function ParseGitBranch {
  git branch 2> /dev/null | sed -e '/^[^*]/d' -e 's/* \(.*\)/(\1)/'
}

function BranchInPrompt {
  local            BLACK="\[\033[0;30m\]"
  local       BOLD_BLACK="\[\033[1;30m\]"
  local       LINE_BLACK="\[\033[4;30m\]"
  local         BG_BLACK="\[\033[40m\]"
  local       HIGH_BLACK="\[\033[0;90m\]"
  local  BOLD_HIGH_BLACK="\[\033[1;90m\]"
  # OPTIONAL - if you want to use any of these other colors:
  local              RED="\[\033[0;31m\]"
  local         BOLD_RED="\[\033[1;31m\]"
  local           BG_RED="\[\033[41m\]"

  local            GREEN="\[\033[0;32m\]"
  local       BOLD_GREEN="\[\033[1;32m\]"
  local       LINE_GREEN="\[\033[4;32m\]"
  local         BG_GREEN="\[\033[42m\]"
  local       HIGH_GREEN="\[\033[0;92m\]"
  local  BOLD_HIGH_GREEN="\[\033[1;92m\]"

  local           YELLOW="\[\033[0;33m\]"
  local      BOLD_YELLOW="\[\033[1;33m\]"
  local      LINE_YELLOW="\[\033[4;33m\]"
  local        BG_YELLOW="\[\033[43m\]"
  local      HIGH_YELLOW="\[\033[0;93m\]"
  local BOLD_HIGH_YELLOW="\[\033[1;93m\]"

  local         BLUE="\[\033[0;34m\]"
  local    BOLD_BLUE="\[\033[1;34m\]"
  local      BG_BLUE="\[\033[44m\]"

  local       PURPLE="\[\033[0;35m\]"
  local  BOLD_PURPLE="\[\033[1;35m\]"
  local    BG_PURPLE="\[\033[45m\]"

  local         CYAN="\[\033[0;36m\]"
  local    BOLD_CYAN="\[\033[1;36m\]"
  local      BG_CYAN="\[\033[46m\]"

  local         GRAY="\[\033[0;37m\]"
  local    BOLD_GRAY="\[\033[1;37m\]"
  local      BG_GRAY="\[\033[47m\]"
  # END OPTIONAL
  local     DEFAULT="\[\033[0m\]"
  PS1="$GREEN\$(ParseGitBranch)$DEFAULT$PS1"
}
