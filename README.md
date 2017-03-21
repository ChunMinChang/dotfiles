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
  - mach alias and machrc
    - ```~/.mozbuild/.machrc``` to the ```path/to/repo/mozilla/gecko/machrc```.
    - load ```path/to/repo/mozilla/gecko/alias.sh``` in ```~/.bashrc```
  - mozreview
    - export ```~/.mozbuild/version-control-tools/git/commands``` to ```$PATH```
    - export ```path/to/git-cinnabar``` to ```$PATH```

Run ```$ python setup.sh -h``` to get the messages for optional settings.

# TODO
- platform-dependent scripts
  - osx: auto-completion for self-defined alias, vim to macvim, ...
- mozilla stuff
  - [x] hg
  - [x] gecko alias
  - [x] mozreview(check git-cinnabar first)
  - [x] rust stuff
  - [ ] icecc
  - [ ] lldb on osx
