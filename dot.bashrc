DOTFILES=~/.dotfiles

# Show colors for ls
export CLICOLOR=true
export LSCOLORS="gxfxcxdxcxegedabagacad"

# Load common utils
[[ -r $DOTFILES/utils.sh ]] && . $DOTFILES/utils.sh

# Load git alias and utils functions
[[ -r $DOTFILES/git/utils.sh ]] && . $DOTFILES/git/utils.sh

# Platform-dependent settings
# ====================================================================
PLATFORM=$(uname -s | tr '[:upper:]' '[:lower:]')
SETTINGS_PREFIX=$HOME/.settings_
SETTINGS_PLATFORM=$SETTINGS_PREFIX$PLATFORM
[ -r $SETTINGS_PLATFORM ] && . $SETTINGS_PLATFORM

# Optional settings (settings might be appended by setup.py)
# ====================================================================
[ -r /Users/cm/dotfiles/mozilla/firefox/alias.sh ] && . /Users/cm/dotfiles/mozilla/firefox/alias.sh
[ -r /Users/cm/dotfiles/mozilla/firefox/tools.sh ] && . /Users/cm/dotfiles/mozilla/firefox/tools.sh
[ -r /Users/cm/.cargo/env ] && . /Users/cm/.cargo/env
