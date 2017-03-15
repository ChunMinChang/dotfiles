# dotfiles
Common environment settings. Put this in ```$HOME/dotfiles```.

# to-do
Refactor:
- master should contain common setting only
  - including git, bash utils(virtual function for different platforms)
  - decoupling mozilla stuffs(or add ```--mozilla``` to build mozilla stuff)
- mozilla branch
  - including hg, mozreview, icecc
- osx
  - implementation for virtual function on OSX
- ubuntu
  - implementation for virtual function on ubuntu

# Notes
There are different branches for OS dependent settings
like ```linux``` and ```osx```.
The dependent settings should be implemented in different branches.

## utils.sh
The following command needs to implement based on its platforms.
- GetTrashPath
- GetPackageCommand

## mozilla
- mozreview/export_path.sh
