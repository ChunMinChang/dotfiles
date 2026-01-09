# Source configuration
if [ -r "$DOTFILES/config.sh" ]; then
  # shellcheck source=../../config.sh
  . "$DOTFILES/config.sh"
fi

# Git-cinnabar setup
if [ -d "$DOTFILES_GIT_CINNABAR_DIR" ]; then
  export PATH="$DOTFILES_GIT_CINNABAR_DIR:$PATH"
  if ! CommandExists git-cinnabar; then
    git cinnabar download
  fi
else
  PrintError "No git-cinnabar in $DOTFILES_GIT_CINNABAR_DIR!"
  PrintError "Tried: $DOTFILES_GIT_CINNABAR_PRIMARY (primary) and $DOTFILES_GIT_CINNABAR_FALLBACK (fallback)"
fi

# Moz-phab setup
if ! command -v moz-phab &> /dev/null; then
  export PATH="$DOTFILES_LOCAL_BIN_DIR:$PATH"
  if ! CommandExists moz-phab; then
    PrintError 'No moz-phab command!\nInstall moz-phab: https://moz-conduit.readthedocs.io/en/latest/phabricator-user.html!'
  fi
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
