# dotfiles
My personal environment settings.

- link ```~/.dotfiles``` to the ```path/to/repo```.
- link ```~/.bashrc``` to ```dot.bashrc```
- link ```~/.bash_profile``` to ```dot.bash_profile``` on OS X
- link ```~/.bashrc_darwin``` to ```dot.bashrc_darwin``` and load it in ```~/.bashrc``` on OS X
- add ```git/config``` into ```[include]``` of ```~/.gitconfig```
- load ```git/utils.sh``` in ```~/.bashrc```

# How to use
Run ```$ python setup.sh``` to do the common settings above.

## Optional settings
We currently provide the following options:
- mozilla
  - All toolkit: ```$ python setup.sh --mozilla```
  - hg: ```$ python setup.sh --mozilla hg```
    - add ```%include mozilla/hg/config``` into ```~/.hgrc```
  - mach alias and machrc: ```$ python setup.sh --mozilla gecko```
    - link ```~/.mozbuild/.machrc``` to the ```mozilla/gecko/machrc```.
    - load ```mozilla/gecko/alias.sh``` into ```~/.bashrc```
  - phabricator: ```$ python setup.sh --mozilla phabricator```
    - load ```mozilla/gecko/phabricator.sh``` into ```~/.bashrc```
      - export ```~/Work/arcanist/bin``` to ```$PATH```
      - export ```~/.mozbuild/git-cinnabar``` to ```$PATH```
      - export ```~/Work/phlay/``` to ```$PATH``` (TODO: It will be imported to moz-phab soon.)
  - rust: ```$ python setup.sh --mozilla rust```
    - load ```~/.cargo/env``` in ```~/.bashrc```

Run ```$ python setup.sh -h``` to get the messages for optional settings.

# TODO
- Don't remove old ```~/.bashrc```.
  If it exists, then append ```source ~/.dotfiles/dot.bashrc``` to it
- common
  - Move files to trash can
  - Recursive delete ```.DS_Store``` on OS X
- git alias
  - [ ] Rewrite the ```qbackto``` and ```qpush```
    - The operations should belong to certain branch
    - Warning users when switching branches with un-pushbacked patches
- mozilla stuff
  - [x] hg
  - [x] gecko alias
  - [x] mozreview(check git-cinnabar first)
  - [x] rust stuff
  - [ ] icecc
  - [ ] lldb on osx
