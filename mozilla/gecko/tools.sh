GIT_CINNABAR=$HOME/.mozbuild/git-cinnabar
if [ -d $GIT_CINNABAR ]; then
  export PATH=$GIT_CINNABAR:$PATH
  if [ $(CommandExists git-cinnabar) -eq 0 ]; then
    PrintError 'No git-cinnabar command! Something weird happens ...'
  fi
else
  PrintError 'No git-cinnabar command!\nRun: "$ ./mach bootstrap" under gecko repo to fix it!'
fi

MOZPHAB=$HOME/.mozbuild/moz-phab
if [ $(CommandExists moz-phab) -eq 0 ] || [ ! -d $MOZPHAB ]; then
  PrintError 'No moz-phab command!\nInstall moz-phab: https://moz-conduit.readthedocs.io/en/latest/phabricator-user.html!'
fi