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

Run ```$ python setup.sh -h``` to get the messages for optional settings.

# TODO
- mozilla stuff
  - [ ] hg
  - [ ] gecko alias
  - [ ] mozreview(check git-cinnabar first)
  - [ ] icecc
  - [ ] lldb on osx
