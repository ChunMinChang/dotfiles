# Source configuration
if [ -r "$DOTFILES/config.sh" ]; then
  # shellcheck source=../../config.sh
  . "$DOTFILES/config.sh"
fi

# Pernosco-submit setup (Linux only)
# Optional: Install via setup.py --mozilla pernosco
if [[ "$OSTYPE" == "linux-gnu"* ]]; then
  if ! command -v pernosco-submit &> /dev/null; then
    if [ -r "$DOTFILES_PERNOSCO_SUBMIT_PATH" ]; then
      export PATH="$DOTFILES_LOCAL_BIN_DIR:$PATH"
    fi
  fi
fi

# Python fallback (Windows / mozilla-build only).
#
# Many Mozilla tools and Claude Code skills (e.g. /sherlock) assume a
# bare `python` works. On Windows that's often not the case: the only
# `python` on PATH is the WindowsApps `App Execution Alias` stub at
# %LOCALAPPDATA%\Microsoft\WindowsApps\python.exe, which just opens
# the Store unless Python is actually installed from there.
#
# When this file is sourced (i.e. the user opted into Mozilla setup
# via `setup.py --mozilla` / `--mozilla tools` / `--all`), point
# `python` at mozilla-build's bundled python if no real python is on
# PATH. Override or disable via DOTFILES_PYTHON_FALLBACK_DIR_WINDOWS
# in ~/.dotfiles_config (set to empty to disable).
case "$OSTYPE" in
  msys*|cygwin*)
    _python_path="$(command -v python 2>/dev/null || true)"
    case "$_python_path" in
      *WindowsApps*) _python_path="" ;;
    esac
    if [ -z "$_python_path" ] && [ -n "${DOTFILES_PYTHON_FALLBACK_DIR_WINDOWS:-}" ]; then
      if [ -x "$DOTFILES_PYTHON_FALLBACK_DIR_WINDOWS/python.exe" ]; then
        export PATH="$DOTFILES_PYTHON_FALLBACK_DIR_WINDOWS:$PATH"
      else
        echo "WARNING: no 'python' on PATH and fallback not found at $DOTFILES_PYTHON_FALLBACK_DIR_WINDOWS/python.exe — install mozilla-build (https://wiki.mozilla.org/MozillaBuild) or set DOTFILES_PYTHON_FALLBACK_DIR_WINDOWS in ~/.dotfiles_config." >&2
      fi
    fi
    unset _python_path
    ;;
esac
