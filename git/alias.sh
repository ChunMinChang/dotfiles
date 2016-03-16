# General
alias gs='git status'
alias ga='git add'
alias gb='git branch'
alias gc='git commit'
alias gd='git diff'
alias go='git checkout'

# Typo
alias got='git'
alias get='git'
alias gut='git'
alias gkt='git'

# Show git branch in prompt.
function parse_git_branch {
  # The following content is incorrect! please see the raw file
  # git branch --no-color 2> /dev/null | sed -e '/^[^*]/d' -e 's/* \(.*\)/ \[\1\]/'
  # git branch --no-color 2> /dev/null | sed -e '/^[^*]/d' -e 's/* \(.*\)/ (\1)/'
  # git branch 2> /dev/null | sed -e '/^[^*]/d' -e 's/* \(.*\)/ (\1)/'
  git branch 2> /dev/null | sed -e '/^[^*]/d' -e 's/* \(.*\)/(\1)/'
}

function branchInPrompt {
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
  #PS1="\$(parse_git_branch)$PS1"
  #PS1="$GREEN\u@\h$DEFAULT:\w$YELLOW\$(parse_git_branch)$DEFAULT\$ "
  #PS1="\u@\h:\w$GREEN\$(parse_git_branch)$DEFAULT\$ "
  PS1="$GREEN\$(parse_git_branch)$DEFAULT$PS1"
}
