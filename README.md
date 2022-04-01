# dotfiles

My personal environment settings.

## Install

Run `$ python setup.py` to set up the common environment settings. For more specific needs, see _Optional settings_ below.

## Uninstall

Run `$ bash uninstall.sh` or `$ sh uninstall.sh`

## Common Settings

- *setup.py*: A python program to install all my personal settings
  - Link *~/.dotfiles* to the *path/to/repo*.
  - Link *~/.bashrc* to *dot.bashrc* if there is no *~/.bashrc*,
    or append a command to load *dot.bashrc* in *~/.bashrc*
  - Link *~/.zshrc* to *dot.zshrc* on *MacOSX*
  - Link *~/.settings_darwin* to *dot.settings_darwin*
  - Link *~/.settings_linux* to *dot.settings_linux*
  - Append *git/config* under `[include]` of *~/.gitconfig*
- *dot.bashrc*: Cross-platform common settings
  - Will be symbolically linked from $HOME/.bashrc, if users don't have $HOME/.bashrc.
    Or be loaded from $HOME/.bashrc if users already have their own $HOME/.bashrc.
    - $HOME/.bashrc is a shell script and the entry point to initialize the shell sessions on the Linux platforms
  - Set *~/.dotfiles* to the *path/to/repo*.
  - Load *utils.sh* for common commands and alias
  - Load *git/utils.sh* for common git commands and alias
  - Load *dot.settings_${PLATFORM}*, where *${PLATFORM}* is *darwin* or *linux*, for platform-denpendent settings
- *utils.sh*: common cross-platform alias and utils functions
- *git*
  - *git/config*: Common *git* alias
  - *git/utils.sh*: Common alias for git typo and utilility git functions
- *OSX* files
  - *dot.zshrc*, for mac OS >= 10.15
    - Will be symbolically linked from *$HOME/.zshrc* on the *OSX* platforms
      - *$HOME/.zshrc* is a shell script and the entry point to initialize the shell sessions on the *OSX* platforms for mac OS >= 10.15
    - Load *$HOME/.bashrc*
  - *dot.bash_profile*, for mac OS <= 10.14
    - Will be symbolically linked from *$HOME/.bash_profile* on the *OSX* platforms
      - *$HOME/.bash_profile* is a shell script and the entry point to initialize the shell sessions on the *OSX* platforms for mac OS <= 10.14
    - Load *$HOME/.bashrc*
  - *dot.settings_darwin*
    - Will be loaded by *dot.bashrc* if the platform is *MacOSX*
    - Custom settings on *OSX*
- *Linux* files
  - *dot.settings_linux*
    - Will be loaded by *dot.bashrc* if the platform is *Linux*
    - Custom settings on *Linux*
- *vscode*
  - *settings.json*: Custom *vscode* settings

## Optional settings

- mozilla
  - All toolkit: `$ python setup.py --mozilla`
  - hg: `$ python setup.py --mozilla hg`
    - add `%include mozilla/hg/config` into *~/.hgrc*
  - mach alias and machrc: ```$ python setup.py --mozilla gecko```
    - Link *~/.mozbuild/machrc* to the *mozilla/gecko/machrc*.
    - Load *mozilla/gecko/alias.sh* into *~/.bashrc*
  - tools: `$ python setup.py --mozilla tools`
    - Load *mozilla/gecko/tools.sh* into *~/.bashrc*
      - *mozilla/gecko/tools.sh* will check if *git-cinnabar* is downloaded
  - *Rust*: `$ python setup.py --mozilla rust`
    - Load *~/.cargo/env* in *~/.bashrc*

Run `$ python setup.py -h` to get the messages for optional settings.

## Utils Usage

### Git

-  Run commands on all the files in the last commit
  - ex: `$ GitLastCommit vim` or `$ GitLastCommit code`
-  Run commands on all the added/changed/modified files in the code editor
  - ex: `$ GitUncommit vim` or `$ GitUncommit code`
- Add all/updated files except _f1, f2, f3, ..._
  - ex: Add all updated files, except _A_ and _B_
    - `$ GitAddExcept -u A B`
  - ex: Add all files, except _P_, _Q_ and _R_
    - `$ GitAddExcept -A P Q R`
- Create a branch for a pull request on a remote tracked repositories
  - ex: Create a branch for pull request _123_ on upstream repo
    - `$ CreateGitBranchForPullRequest upstream 123`

### Gecko

- Generate a W3C Spec page from a _bs_ file
  - ex: Generate a w3c spec page called _test.html_ from _index.bs_
    - `$ W3CSpec index.bs test.html`
- Check diff/patch before submitting review
  - ex: Check the uncommited/changed files
    - `$ MozCheckDiff`
  - ex: Check the uncommited/changed files between commit-A and commit-B
    - `$ MozCheckDiff <commit-A>..<commit-B>`

### Common

- Recursively find files under the current folder
  - ex: Recursively list all the _.sh_ files
    - `$ RecursivelyFind "*.sh"`
- Recursively remove files under the current folder
  - ex: Recursively delete all the *.DS_Store* files
    - `$ RecursivelyFind "*.DS_Store"`
- Throw files to trash can
  - ex: Throw _hello.txt_ and _world.log_ to Trash
    - `$ Trash hello.txt world.log`

## TODO

- Use *zsh* configuration tool (e.g. *ohmyzsh*) on zsh
- Make it work on Windows!
- vim
  - add some basic environment settings for vim
- vscode
  - Link `setting.json` to the *vscode* application from `~/dotfiles/vscode/settings.json`
  - Sync the extensions
- mozilla stuff
  - Append `~/dotfiles/mozilla/machrc` into `~/.mozbuild/machrc`
