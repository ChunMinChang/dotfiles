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

# Optional settings (ssettings might be appended by setup.py)
# ====================================================================
[ -r /home/cm/dotfiles/mozilla/gecko/tools.sh ] && . /home/cm/dotfiles/mozilla/gecko/tools.sh
[ -r /home/cm/dotfiles/mozilla/gecko/alias.sh ] && . /home/cm/dotfiles/mozilla/gecko/alias.sh
[ -r /home/cm/.cargo/env ] && . /home/cm/.cargo/env
