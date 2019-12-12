DOTFILES=~/.dotfiles

# Show colors for ls
export CLICOLOR=true
export LSCOLORS="gxfxcxdxcxegedabagacad"

# Load common utils
[[ -r $DOTFILES/utils.sh ]] && . $DOTFILES/utils.sh

# Platform-dependent settings
# ====================================================================
PLATFORM=$(uname -s | tr '[:upper:]' '[:lower:]')
BASHRC_PLATFORM=~/.bashrc_${PLATFORM}
[ -r $BASHRC_PLATFORM ] && . $BASHRC_PLATFORM

# Alias
# ====================================================================
alias RSSTimestamp='TZ=GMT date +"%a, %d %b %Y %T %Z"'

# Optional settings
# ====================================================================
export GIT_EDITOR=vim