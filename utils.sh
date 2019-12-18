function RecursivelyFind()
{
  find . -name "$1"
}

function RecursivelyRemove()
{
  find . -name "$1" -type f -delete
}

function Trash()
{
  local items=$@
  if [ -d "$TRASH" ]; then
    if [ ! -z "$items" ]; then
      echo "Move $items to $TRASH"
      mv $items $TRASH
    else
      echo "Throw nothing to trash."
    fi
  else
    echo "TRASH path not found! Please set TRASH in dot.bashrc_$PLATFORM"
  fi
}

# The following commands are used internally in this repo
function CommandExists()
{
  local cmd=$1
  if command -v $cmd >/dev/null 2>&1; then
    echo 1
  else
    echo >&2 "$cmd is not installed.";
    echo 0
  fi
}

function PrintError()
{
  local msg=$1
  local bold_red="\033[1;31m"
  local normal="\033[0m"
  echo -e ${bold_red}ERROR:${normal} $msg
}

function PrintHint()
{
  local msg=$1
  local bold_cyan_bkg="\033[1;46m"
  local normal="\033[0m"
  echo -e ${bold_cyan_bkg}HINT:${normal} $msg
}

function PrintWarning()
{
  local msg=$1
  local bold_yellow="\033[1;33m"
  local normal="\033[0m"
  echo -e ${bold_yellow}WARNING:${normal} $msg
}