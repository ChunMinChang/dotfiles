# Load environment variables to this script
. ~/.bashrc

# $PLATFORM is set in ~/.bashrc
echo Uninstall personal environment settings on $PLATFORM

# Unlink the platform settings ($SETTINGS_PLATFORM is set in ~/.bashrc)
if [ -r $SETTINGS_PLATFORM ]; then
  echo "$SETTINGS_PLATFORM"
  unlink $SETTINGS_PLATFORM
fi

# Unlink the entry point of environment settings on darwin (MacOSX)
if [ "$PLATFORM" == "darwin" ] && [ -r ~/.zshrc ]; then
  echo "Unlink ~/.zshrc"
  unlink ~/.zshrc
fi

# Unlink the $DOTFILES ($DOTFILES is set in ~/.bashrc)
if [ -r $DOTFILES ]; then
  echo "Unlink $DOTFILES"
  unlink $DOTFILES
fi

# Unlink the common settings
if [ -r ~/.bashrc ]; then
  echo "Unlink ~/.bashrc"
  unlink ~/.bashrc
fi

# TODO: Remove the following settings automatically
echo "Please remove ./mozilla/hg/config with prefix %include in $HOME/.hgrc manually"
echo "Please remove ./git/config under [include] in $HOME/.gitconfig manually"
