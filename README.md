# dotfiles
My personal environment settings.

## Files
- *setup.sh*: A python program to install all my personal settings
  - Link my *dot files* settings to *$HOME*
  - Load my personal commands and alias
  - Load settings that my work needs (personal *Mozilla* settings and commands)
- *dot.bashrc*: Cross-platform common settings
  - Prompt users to install *git*
  - Load *utils.sh*
  - Load *git/utils.sh*
  - Load *dot.bashrc_${PLATFORM}*, where *${PLATFORM}* is *darwin*(OSX) or *linux*
  - Will be symbolically linked from *$HOME/.bashrc*, no matter what the platform users have
    - *$HOME/.bashrc* is a shell script and the entry point to initialize the shell sessions on the *Linux* platforms
    - If *$HOME/.bashrc* exists, a command loading *dot.bashrc* will be append in current *$HOME/.bashrc*
- *utils.sh*: Personal cross-platform commands
- *git*
  - *git/config*: Personal *git* alias
  - *git/utils.sh*: Personal commands using `git *`
- *OSX* files
  - *dot.bash_profile*
    - Will be symbolically linked from *$HOME/.bash_profile* on the *OSX* platforms
      - *$HOME/.bash_profile* is a shell script and the entry point to initialize the shell sessions on the *OSX* platforms
    - Load *$HOME/.bashrc* (and that's why *$HOME/.bashrc* can be cross-platform script)
  - *dot.bashrc_darwin*
    - Will be loaded by *dot.bashrc* if the platform is *OSX*
    - Personal settings on *OSX*
- *Linux* files
  - *dot.bashrc_linux*
    - Will be loaded by *dot.bashrc* if the platform is *Linux*
      - Personal settings on *Linux*
- *vscode*
  - *settings.json*: Personal *vscode* settings

### Links
- Link *~/.dotfiles* to the *path/to/repo*.
- Link *~/.bashrc* to *dot.bashrc*
- Link *~/.bash_profile* to *dot.bash_profile* on *OS X*
- Link *~/.bashrc_darwin* to *dot.bashrc_darwin* and load it in *~/.bashrc* on *OS X*
- Link *~/.bashrc_linux* to *dot.bashrc_linux* and load it in *~/.bashrc* on *Linux*
- Append *git/config* under `[include]` of *~/.gitconfig*
- Load *git/utils.sh* in *~/.bashrc*

## Optional settings
- mozilla
  - All toolkit: `$ python setup.sh --mozilla`
  - hg: `$ python setup.sh --mozilla hg`
    - add `%include mozilla/hg/config` into *~/.hgrc*
  - mach alias and machrc: ```$ python setup.sh --mozilla gecko```
    - Link *~/.mozbuild/.machrc* to the *mozilla/gecko/machrc*.
    - Load *mozilla/gecko/alias.sh* into *~/.bashrc*
  - tools: `$ python setup.sh --mozilla tools`
    - Load *mozilla/gecko/tools.sh* into *~/.bashrc*
      - check if *git-cinnabar* is downloaded
  - *Rust*: `$ python setup.sh --mozilla rust`
    - Load *~/.cargo/env* in *~/.bashrc*

Run `$ python setup.sh -h` to get the messages for optional settings.

## Utils Usage
### Git
- Create a branch for a pull request on a remote tracked repositories
  - ex: Create a branch for pull request 463 on upstream repo
    - `$ CreateGitBranchForPullRequest upstream 463`
- Open the changed/modified files in the code editor
  - ex: `$ GitEdit vim` or `$ GitEdit code`
### Gecko
- Generate a W3C Spec page from a _bs_ file
  - ex: Generate a w3c spec page called _test.html_ from _index.bs_
    - `$ W3CSpec index.bs test.html`
### Common
- RecursivelyFind
  - ex: `$ RecursivelyFind "*.sh"`
- RecursivelyRemove
  - ex: `$ RecursivelyFind ".DS_Store"`

# TODO
- Make it work on Windows!
- Write examples to use the commands, in case I forget.
- Write commands to uninstall all the settings and remove all the links.
- more git alias
- vim
  - add some basic environment settings for vim
- vscode
  - Link `setting.json` to the *vscode* application from `~/dotfiles/vscode/settings.json`
  - Sync the extensions
- mozilla stuff
  - Append `~/dotfiles/mozilla/machrc` into `~/.mozbuild/machrc`
