# dotfiles
My personal environment settings.

## Files
- *dot.bashrc*
  - Cross-platform common settings
  - Prompt users to install *git*
  - Load *utils.sh*
  - Load *dot.bashrc_${PLATFORM}*, where *${PLATFORM}* is *darwin*(OSX) or *linux*
  - Will be symbolically linked from *$HOME/.bashrc*, no matter what the platform users have
    - *$HOME/.bashrc* is a shell script and the entry point to initialize the shell sessions on the *Linux* platforms
    - If *$HOME/.bashrc* exists, a command loading *dot.bashrc* will be append in current *$HOME/.bashrc*
- *utils.sh*
  - Personal cross-platform commands
- OSX files
  - *dot.bash_profile*
    - Will be symbolically linked from *$HOME/.bash_profile* on the *OSX* platforms
      - *$HOME/.bash_profile* is a shell script and the entry point to initialize the shell sessions on the *OSX* platforms
    - Load *$HOME/.bashrc* (and that's why *$HOME/.bashrc* can be cross-platform script)
  - *dot.bashrc_darwin*
    - Will be loaded by *dot.bashrc* if the platform is *OSX*
    - Personal settings on *OSX*
- Linux files
  - *dot.bashrc_linux*
    - Will be loaded by *dot.bashrc* if the platform is *Linux*
      - Personal settings on *Linux*

## Links
- link ```~/.dotfiles``` to the ```path/to/repo```.
- link ```~/.bashrc``` to ```dot.bashrc```
- link ```~/.bash_profile``` to ```dot.bash_profile``` on OS X
- link ```~/.bashrc_darwin``` to ```dot.bashrc_darwin``` and load it in ```~/.bashrc``` on OS X
- add ```git/config``` into ```[include]``` of ```~/.gitconfig```
- load ```git/utils.sh``` in ```~/.bashrc```

## How to use
Run ```$ python setup.sh``` to do the common settings above.

## Git
- Create a branch for a pull request on a remote tracked repositories
  - ex: Create a branch for pull request 463 on upstream repo
    - `$ CreateGitBranchForPullRequest upstream 463`
- Open the changed/modified files in the code editor
  - ex: `$ GitEdit vim` or `$ GitEdit code`

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
        - [mystor/phlay](https://github.com/mystor/phlay)
      - export ```~/Work/review/``` to ```$PATH``` (TODO: Check if `phlay` can be replaced by this.)
        - [mozilla-conduit/review](https://github.com/mozilla-conduit/review)
  - rust: ```$ python setup.sh --mozilla rust```
    - load ```~/.cargo/env``` in ```~/.bashrc```

Run ```$ python setup.sh -h``` to get the messages for optional settings.

# TODO
- Write examples to use the commands, in case I forget.
- common
  - Move files to trash can
- git alias
  - [ ] Rewrite the ```qbackto``` and ```qpush```
    - The operations should belong to certain branch
    - Warning users when switching branches with un-pushbacked patches
- vim
  - add some basic environment settings for vim
- vscode
  - Link `setting.json` to the *vscode* application from `~/dotfiles/vscode/settings.json`
- mozilla stuff
  - [x] hg
  - [x] gecko alias
  - [x] rust stuff
  - [ ] icecc
  - [ ] lldb on osx
