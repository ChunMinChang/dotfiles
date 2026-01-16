# Common Settings
# ====================================================================
[[ -r ~/.bashrc ]] && . ~/.bashrc

# Prompt for version control tool
# ====================================================================
# Allow for functions in the prompt.
setopt PROMPT_SUBST

# Auto-completion
# ====================================================================
# Enable the default zsh completions
autoload -Uz compinit && compinit