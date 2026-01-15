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

# Common paths (after platform settings load config.sh)
# ====================================================================
# Add local bin to PATH if it exists
if [ -d "$DOTFILES_LOCAL_BIN_DIR" ]; then
  export PATH="$DOTFILES_LOCAL_BIN_DIR:$PATH"
fi

# Optional settings
# ====================================================================
# This is a template file. Machine-specific settings (e.g., Mozilla tools)
# are appended to ~/.bashrc by setup.py, not to this template.
# This keeps the template clean and platform-agnostic for version control.
