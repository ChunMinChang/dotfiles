# Source configuration
if [ -r "$DOTFILES/config.sh" ]; then
  # shellcheck source=../../config.sh
  . "$DOTFILES/config.sh"
fi

# Pernosco-submit setup (Linux only)
if [[ "$OSTYPE" == "linux-gnu"* ]]; then
  if ! command -v pernosco-submit &> /dev/null; then
    if [ -r "$DOTFILES_PERNOSCO_SUBMIT_PATH" ]; then
      export PATH="$DOTFILES_WORK_BIN_DIR:$PATH"
    else
      PrintError "Please put a pernosco-submit script at: $DOTFILES_PERNOSCO_SUBMIT_PATH"
      PrintError "See Mozilla Pernosco Info Page, Docs and pernosco-submit_template"
    fi
  fi
fi
