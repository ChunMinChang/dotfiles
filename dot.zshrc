# Common Settings
# ====================================================================
[[ -r ~/.bashrc ]] && . ~/.bashrc

# Prompt for version control tool
# ====================================================================
[[ -r $DOTFILES/git/utils.sh ]] && . $DOTFILES/git/utils.sh

# Allow for functions in the prompt.
setopt PROMPT_SUBST

autoload -Uz vcs_info
zstyle ':vcs_info:*' actionformats \
    '< (%f%s) %F{2}%b%F{3}|%F{1}%a%f '
zstyle ':vcs_info:*' formats       \
    '< (%f%s) %F{2}%b%f'
zstyle ':vcs_info:(sv[nk]|bzr):*' branchformat '%b%F{1}:%F{3}%r'

zstyle ':vcs_info:*' enable git hg cvs svn

vcs_info_wrapper() {
  vcs_info
  if [ -n "$vcs_info_msg_0_" ]; then
    echo "%{$fg[grey]%}${vcs_info_msg_0_}%{$reset_color%}$del"
  fi
}

# Set the prompt in the right side
RPROMPT=$'$(vcs_info_wrapper)'

# Auto-completion
# ====================================================================
# Enable the default zsh completions
autoload -Uz compinit && compinit