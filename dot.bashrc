# shellcheck shell=bash
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
case "$(uname -s)" in
  MINGW*|MSYS*|CYGWIN*) PLATFORM=windows ;;
  Darwin)               PLATFORM=darwin ;;
  Linux)                PLATFORM=linux ;;
  *)                    PLATFORM=$(uname -s | tr '[:upper:]' '[:lower:]') ;;
esac
SETTINGS_PREFIX=$HOME/.settings_
SETTINGS_PLATFORM=$SETTINGS_PREFIX$PLATFORM
# Resolves to one of dot.settings_{darwin,linux,windows} at runtime, so there
# is no single path a shellcheck source= directive could name.
# shellcheck disable=SC1090
[ -r "$SETTINGS_PLATFORM" ] && . "$SETTINGS_PLATFORM"

# Common paths (after platform settings load config.sh)
# ====================================================================
# Add local bin to PATH if it exists
if [ -d "$DOTFILES_LOCAL_BIN_DIR" ]; then
  export PATH="$DOTFILES_LOCAL_BIN_DIR:$PATH"
fi

# Node/npm from `./mach bootstrap`, if present.
#
# Bootstrap unpacks a Node toolchain into its state dir, but never puts it
# on PATH. Borrow it so npm-installed tools (markdownlint, profiler-cli)
# are reachable. We only ever *read* from this directory -- our own npm
# installs go to $HOME/.local via an explicit --prefix, so a bootstrap
# Node update cannot take them with it.
#
# APPENDED, not prepended: a real Node install must always outrank the
# version mach bootstrap happens to pin. Keep in sync with
# _augment_path_with_mozbuild_node() in setup.py.
_mozbuild_node_dir="${MOZBUILD_STATE_PATH:-$HOME/.mozbuild}/node"
if [ -d "$_mozbuild_node_dir" ]; then
  export PATH="$PATH:$_mozbuild_node_dir"
fi
unset _mozbuild_node_dir

# Optional settings
# ====================================================================
# This is a template file. Machine-specific settings (e.g., Mozilla tools)
# are appended to ~/.bashrc by setup.py, not to this template.
# This keeps the template clean and platform-agnostic for version control.
