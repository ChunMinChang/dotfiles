# dotfiles
My personal environment settings.

Run `$ python setup.py` to set up the common environment settings. For more specific needs, see _Optional settings_ below.

## Files
- *setup.py*: A python program to install all my personal settings
  - Link my *dot files* settings to *$HOME*
  - Load my personal commands and alias
  - Load settings that my work needs (personal *Mozilla* settings and commands)
- *dot.bashrc*: Cross-platform common settings
  - Prompt users to install *git*
  - Load *utils.sh* for common commands and alias
  - Load *git/utils.sh* for common git commands and alias
  - Load *dot.bashrc_${PLATFORM}*, where *${PLATFORM}* is *darwin*(OSX) or *linux*, for platform-denpendent settings
  - Will be symbolically linked from *$HOME/.bashrc*, if users don't have *$HOME/.bashrc*.
    Or be loaded from *$HOME/.bashrc* if users already have their own *$HOME/.bashrc*.
    - *$HOME/.bashrc* is a shell script and the entry point to initialize the shell sessions on the *Linux* platforms
- *utils.sh*: common cross-platform commands
- *git*
  - *git/config*: common *git* alias
  - *git/utils.sh*: common commands using `git *`
- *OSX* files
  - *dot.bash_profile*
    - Will be symbolically linked from *$HOME/.bash_profile* on the *OSX* platforms
      - *$HOME/.bash_profile* is a shell script and the entry point to initialize the shell sessions on the *OSX* platforms
    - Load *$HOME/.bashrc*
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
- Link *~/.bashrc* to *dot.bashrc* if there is no *~/.bashrc*, or load *dot.bashrc* in *~/.bashrc*
- Link *~/.bash_profile* to *dot.bash_profile* on *OS X*
- Link *~/.bashrc_darwin* to *dot.bashrc_darwin* and load it in *~/.bashrc* on *OS X*
- Link *~/.bashrc_linux* to *dot.bashrc_linux* and load it in *~/.bashrc* on *Linux*
- Append *git/config* under `[include]` of *~/.gitconfig*
- Load *git/utils.sh* in *~/.bashrc*

## Optional settings
- mozilla
  - All toolkit: `$ python setup.py --mozilla`
  - hg: `$ python setup.py --mozilla hg`
    - add `%include mozilla/hg/config` into *~/.hgrc*
  - mach alias and machrc: ```$ python setup.py --mozilla gecko```
    - Link *~/.mozbuild/.machrc* to the *mozilla/gecko/machrc*.
    - Load *mozilla/gecko/alias.sh* into *~/.bashrc*
  - tools: `$ python setup.py --mozilla tools`
    - Load *mozilla/gecko/tools.sh* into *~/.bashrc*
      - check if *git-cinnabar* is downloaded
  - *Rust*: `$ python setup.py --mozilla rust`
    - Load *~/.cargo/env* in *~/.bashrc*

Run `$ python setup.py -h` to get the messages for optional settings.

## Utils Usage
### Git
- Open all the files in the last commit
  - ex: `$ GitLastCommit vim` or `$ GitLastCommit code`
- Open all the added/changed/modified files in the code editor
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
