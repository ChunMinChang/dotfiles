# dotfiles
My personal environment settings.

We will add the following links to your ```$HOME``` directory
- ```~/.dotfiles``` to the ```path/to/repo```.
- ```~/.bashrc``` to ```dot.bashrc```
- ```~/.bash_profile``` to ```dot.bash_profile``` if it's OS X

and add ```path/to/repo/git/config``` into ```[include]``` of ```~/.gitconfig```

# How to use
Run ```$ python setup.sh```.

We currently provide the following options:
- Mozilla
  - All toolkit: ```$ python setup.sh --mozilla```
  - hg: ```$ python setup.sh --mozilla hg```
    - add ```%include path/to/repo/mozilla/hg/config``` into ```~/.hgrc```

Run ```$ python setup.sh -h``` to get the messages for optional settings.

# TODO
- mozilla stuff
  - [x] hg
  - [x] gecko alias
  - [x] mozreview(check git-cinnabar first)
  - [ ] icecc
  - [ ] lldb on osx

- clean-up
  - [x] useless ```return``` in ```hg_init```
  - [x] add ```\n``` in file write
  - [x] duplicated files read-then-write pattern
  - [x] duplicated export bash commands
  - [x] duplicated bash-loading commands
  - [x] log format
