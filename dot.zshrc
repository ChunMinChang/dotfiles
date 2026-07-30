# shellcheck shell=bash
# Sourced into the interactive shell as ~/.zshrc (not executed). This is zsh,
# but shellcheck has no zsh dialect, so it is linted as bash on a best-effort
# basis; zsh-only builtins below (setopt, autoload) are simply not recognised.

# Common Settings
# ====================================================================
# shellcheck source=dot.bashrc
[[ -r ~/.bashrc ]] && . ~/.bashrc

# Prompt for version control tool
# ====================================================================
# Allow for functions in the prompt.
setopt PROMPT_SUBST

# Auto-completion
# ====================================================================
# Enable the default zsh completions
autoload -Uz compinit && compinit