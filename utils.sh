# Alias
# ====================================================================
alias RSSTimestamp='TZ=GMT date +"%a, %d %b %Y %T %Z %z"'
alias RSSTimestampNoTZ='date +"%a, %d %b %Y %T %Z %z"'
alias RSSTimestampPDX='TZ=GMT+7 date +"%a, %d %b %Y %T %Z %z"'

# The following commands are used internally in this repo
function CommandExists()
{
  local cmd="$1"
  if command -v "$cmd" >/dev/null 2>&1; then
    return 0  # Success: command exists
  else
    echo >&2 "$cmd is not installed."
    return 1  # Failure: command not found
  fi
}

function PrintError()
{
  local msg="$1"
  local bold_red="\033[1;31m"
  local normal="\033[0m"
  echo -e "${bold_red}ERROR:${normal} $msg"
}

function PrintHint()
{
  local msg="$1"
  local bold_cyan_bkg="\033[1;46m"
  local normal="\033[0m"
  echo -e "${bold_cyan_bkg}HINT:${normal} $msg"
}

function PrintWarning()
{
  local msg="$1"
  local bold_yellow="\033[1;33m"
  local normal="\033[0m"
  echo -e "${bold_yellow}WARNING:${normal} $msg"
}

function PrintTitle()
{
  local msg="$1"
  local bold_red="\033[1;31m"
  local normal="\033[0m"
  echo -e "${bold_red}${msg}${normal}"
}

function PrintSubTitle()
{
  local msg="$1"
  local green="\033[92m"
  local normal="\033[0m"
  echo -e "${green}${msg}${normal}"
}

# Utils functions
# ====================================================================
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
  if [ -d "$TRASH" ]; then
    if [ $# -gt 0 ]; then
      echo "Move $* to $TRASH"
      mv "$@" "$TRASH"
    else
      echo "Throw nothing to trash."
    fi
  else
    echo "TRASH path not found! Please set TRASH in dot.bashrc_$PLATFORM"
  fi
}

function HostHTTP()
{
  if CommandExists npx; then
    # npx live-server --port=$port --no-browser --quiet
    npx live-server "$@"
  elif CommandExists python3; then
    python3 -m http.server "$@"
  elif CommandExists python; then
    python -m SimpleHTTPServer "$@"
  else
    PrintError "No HTTP server found! Please install 'npx' or 'python3' or 'python'."
  fi
}
