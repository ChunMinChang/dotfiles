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
      export PATH="$DOTFILES_WORK_BIN_DIR:$PATH"
    fi
  fi
fi
