ARCANIST_BIN=$HOME/Work/arcanist/bin/
if [ -d $ARCANIST_BIN ]; then
  export PATH=$ARCANIST_BIN:$PATH
else
  PrintError 'Please update path for arcanist commands'
fi

GIT_CINNABAR=$HOME/.mozbuild/git-cinnabar
if [ -d $GIT_CINNABAR ]; then
  export PATH=$GIT_CINNABAR:$PATH
else
  PrintError 'No git-cinnabar command!\nRun: "$ ./mach bootstrap" under gecko repo to fix it!'
fi

MOZ_PHAB=$HOME/Work/review/
if [ -d $MOZ_PHAB ]; then
  export PATH=$MOZ_PHAB:$PATH
else
  PrintError 'Please update path for moz-phab commands'
fi