ARCANIST_BIN=$HOME/Work/arcanist/bin/
if [ -d $ARCANIST_BIN ]; then
  export PATH=$ARCANIST_BIN:$PATH
else
  echo "Please update path for arcanist commands"
fi

GIT_CINNABAR=$HOME/.mozbuild/git-cinnabar
if [ -d $GIT_CINNABAR ]; then
  export PATH=$GIT_CINNABAR:$PATH
else
  echo "No git-cinnabar command!\n\tRun: \"$ ./mach bootstrap\" under gecko repo to fix it!"
fi

PHLAY=$HOME/Work/phlay/
if [ -d $PHLAY ]; then
  export PATH=$PHLAY:$PATH
else
  echo "Please update path for phlay commands"
fi