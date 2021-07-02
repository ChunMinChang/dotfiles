DEFAULT_GIT_CINNABAR=$HOME/.mozbuild/git-cinnabar
if [ -d $DEFAULT_GIT_CINNABAR ]; then
  GIT_CINNABAR=$DEFAULT_GIT_CINNABAR
else # fallback
  GIT_CINNABAR=$HOME/Work/git-cinnabar
fi

if [ -d $GIT_CINNABAR ]; then
  export PATH=$GIT_CINNABAR:$PATH
  if [ $(CommandExists git-cinnabar) -eq 0 ]; then
    git cinnabar download
  fi
else
  PrintError "No git-cinnabar in $GIT_CINNABAR!"
fi

if [ $(CommandExists moz-phab) -eq 0 ]; then
  PrintError 'No moz-phab command!\nInstall moz-phab: https://moz-conduit.readthedocs.io/en/latest/phabricator-user.html!'
fi